from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import httpx
import pytest
from sqlalchemy import select, update

from ai_engine.strategy_governor import (
    AgentParamAdjustment,
    REDIS_RUNTIME_PARAMS_KEY,
    strategy_governor,
    validate_and_apply_hard_guardrails,
)
from core.database import session_factory
from core.models import EpisodicTradeMemory, StrategySignal, SystemTradingConfig
from core.redis_client import redis_client
from main import app
from simulation.auto_executor import auto_executor


def test_pydantic_hard_guardrails_clamping():
    """Kiểm tra Hard Guardrails tự động kẹp giá trị (clamp) vào biên độ an toàn tuyệt đối"""
    # 1. Đề xuất rủi ro vượt ngưỡng tối đa (2.5% > 1.5%) -> Kẹp về 1.50%
    proposed_high_risk = {
        "risk_per_trade_percent": 2.50,
        "min_risk_reward_ratio": 1.50,
        "atr_sl_multiplier": 1.50,
    }
    validated, overridden = validate_and_apply_hard_guardrails(proposed_high_risk, current_daily_drawdown=0.5)
    assert validated.risk_per_trade_percent == 1.50
    assert overridden is False

    # 2. Đề xuất R:R dưới mức tối thiểu (1.00 < 1.20) -> Kẹp lên 1.20
    proposed_low_rr = {
        "risk_per_trade_percent": 1.00,
        "min_risk_reward_ratio": 1.00,
        "atr_sl_multiplier": 1.50,
    }
    validated_rr, _ = validate_and_apply_hard_guardrails(proposed_low_rr, current_daily_drawdown=0.5)
    assert validated_rr.min_risk_reward_ratio == 1.20

    # 3. Đề xuất SL multiplier vượt mức tối đa (4.50 > 3.00) -> Kẹp về 3.00
    proposed_high_sl = {
        "risk_per_trade_percent": 1.00,
        "min_risk_reward_ratio": 1.50,
        "atr_sl_multiplier": 4.50,
    }
    validated_sl, _ = validate_and_apply_hard_guardrails(proposed_high_sl, current_daily_drawdown=0.5)
    assert validated_sl.atr_sl_multiplier == 3.00


def test_daily_drawdown_hard_limit_override():
    """Kiểm tra Rào chắn Khóa lỗ ngày 3%: nếu drawdown >= 3.0%, cưỡng chế tắt quyền giao dịch"""
    proposed = {
        "risk_per_trade_percent": 1.00,
        "min_risk_reward_ratio": 1.50,
        "atr_sl_multiplier": 1.50,
        "trading_allowed": True,
    }

    # Trường hợp lỗ ngày 3.2% >= 3.0%
    validated, overridden = validate_and_apply_hard_guardrails(proposed, current_daily_drawdown=3.20)
    assert validated.trading_allowed is False
    assert overridden is True
    assert "HARD_LIMIT_BREACHED" in (validated.halt_reason or "")
    assert "3.20%" in (validated.halt_reason or "")


@pytest.mark.anyio
async def test_governor_consensus_and_reflexion_feedback_loop():
    """Kiểm tra vòng lặp tự thích ứng: lỗi SL_TOO_TIGHT từ Reflexion tự động nới SL multiplier"""
    now = datetime.now(timezone.utc)

    async with session_factory() as session:
        # 1. Thêm 2 ký ức bị dính lỗi SL_TOO_TIGHT gần nhất
        m1 = EpisodicTradeMemory(
            outcome="LOSS",
            market_context_summary="Wicked out by spread",
            root_cause="Stop Loss was placed too tight",
            lesson_learned="Widen SL multiplier",
            mistake_category="SL_TOO_TIGHT",
            rule_to_add="Expand atr_sl_multiplier",
            is_test=True,
        )
        m2 = EpisodicTradeMemory(
            outcome="LOSS",
            market_context_summary="Wicked out by Asian high sweep",
            root_cause="Stop Loss was placed too tight",
            lesson_learned="Widen SL multiplier",
            mistake_category="SL_TOO_TIGHT",
            rule_to_add="Expand atr_sl_multiplier",
            is_test=True,
        )
        session.add_all([m1, m2])
        await session.commit()

        # 2. Kích hoạt Governor tổng hợp đồng thuận
        report = await strategy_governor.synthesize_consensus(session, include_test=True)

        # 3. Kiểm tra phản ứng tự thích ứng
        assert report.active_params.atr_sl_multiplier >= 1.80
        assert "Reflexion alert" in report.rationale
        assert "SL_TOO_TIGHT" in report.rationale

        # 4. Kiểm tra đồng bộ vào DB
        cfg = await session.scalar(select(SystemTradingConfig).where(SystemTradingConfig.id == 1))
        assert cfg is not None
        assert float(cfg.atr_sl_multiplier) >= 1.80
        assert cfg.updated_by_agent == "STRATEGY_GOVERNOR"

        # 5. Kiểm tra đồng bộ vào Redis Cache
        cached_raw = await redis_client.get(REDIS_RUNTIME_PARAMS_KEY)
        assert cached_raw is not None
        cached_data = json.loads(cached_raw)
        assert cached_data["atr_sl_multiplier"] >= 1.80


@pytest.mark.anyio
async def test_auto_executor_respects_governor_halt():
    """Kiểm tra AutoExecutor chặn đứng khớp lệnh tự động khi Governor khóa quyền giao dịch"""
    async with session_factory() as session:
        # 1. Khóa quyền giao dịch trong config
        await session.execute(
            update(SystemTradingConfig)
            .where(SystemTradingConfig.id == 1)
            .values(
                trading_allowed=False,
                halt_reason="AI_GOVERNOR_HALT: High geopolitical volatility warning",
                execution_mode="FULL_AUTO",
            )
        )
        await session.commit()

        # 2. Tạo tín hiệu hợp lệ PENDING
        sig = StrategySignal(
            symbol="XAUUSD",
            side="BUY",
            generated_at=datetime.now(timezone.utc),
            session_name="London Kill Zone",
            entry_price=Decimal("2650.00"),
            stop_loss=Decimal("2635.00"),
            take_profit_1=Decimal("2680.00"),
            risk_reward=Decimal("2.00"),
            status="PENDING",
            reason="SMC Bullish Order Block tap",
            is_test=True,
        )
        session.add(sig)
        await session.commit()
        await session.refresh(sig)
        sig_id = sig.id

        # 3. Thực thi qua auto_executor -> Bắt buộc ném lỗi do trading_allowed=False
        with pytest.raises(ValueError, match="Trading halted by Governor"):
            await auto_executor.execute_signal(sig_id, session=session, force_manual=False)

        # 4. Khôi phục quyền giao dịch
        await session.execute(
            update(SystemTradingConfig)
            .where(SystemTradingConfig.id == 1)
            .values(trading_allowed=True, halt_reason=None, execution_mode="MANUAL")
        )
        await session.commit()


@pytest.mark.anyio
async def test_governor_api_endpoints():
    """Kiểm tra các REST API endpoints của Governor"""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. GET /api/v1/governor/consensus
        res_con = await client.get("/api/v1/governor/consensus?include_test=true")
        assert res_con.status_code == 200
        con_data = res_con.json()
        assert "market_regime" in con_data
        assert "active_params" in con_data
        assert "confidence_score" in con_data

        # 2. GET /api/v1/governor/runtime-params
        res_params = await client.get("/api/v1/governor/runtime-params")
        assert res_params.status_code == 200
        param_data = res_params.json()
        assert "risk_per_trade_percent" in param_data
        assert "atr_sl_multiplier" in param_data

        # 3. POST /api/v1/governor/evaluate
        res_eval = await client.post("/api/v1/governor/evaluate?include_test=true")
        assert res_eval.status_code == 200
        eval_data = res_eval.json()
        assert eval_data["active_params"]["updated_by_agent"] == "STRATEGY_GOVERNOR"

        # 4. POST /api/v1/governor/override (Trader can thiệp thủ công an toàn)
        res_override = await client.post(
            "/api/v1/governor/override",
            json={
                "risk_per_trade_percent": 0.75,
                "atr_sl_multiplier": 1.75,
                "trading_allowed": True,
            },
        )
        assert res_override.status_code == 200
        override_data = res_override.json()
        assert override_data["status"] == "success"
        assert override_data["active_params"]["risk_per_trade_percent"] == 0.75
        assert override_data["active_params"]["atr_sl_multiplier"] == 1.75
