import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import logging
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.embeddings import embedding_service
from ai_engine.rag_service import rag_service
from core.database import session_factory
from core.models import EconomicEvent, EpisodicTradeMemory, FinancialNews, SimulatedOrder
from core.redis_client import redis_client

logger = logging.getLogger(__name__)


class ReflexionService:
    """
    Reflexion Engine Service (Học tập & Tự kiểm điểm sau mỗi lệnh đóng):
    - Tự động phân tích nguyên nhân thành công / thất bại (Post-Mortem Analysis).
    - Phân loại lỗi giao dịch theo taxonomy chuẩn (EARLY_ENTRY, SL_TOO_TIGHT, TRADED_DURING_NEWS_SPIKE...).
    - Vectorize bài học kinh nghiệm và lưu trữ vào bảng episodic_trade_memory (1536 dims).
    - Cung cấp tính năng tra cứu Semantic Memory cho Technical Agent & Strategy Governor.
    """

    async def analyze_closed_order(
        self,
        order_data: dict[str, Any],
        session: AsyncSession | None = None,
    ) -> EpisodicTradeMemory:
        """
        Phân tích post-mortem toàn diện cho một lệnh đã đóng và lưu vào episodic_trade_memory.
        Hỗ trợ cả object truyền trực tiếp hoặc đọc từ DB.
        """
        order_id = order_data.get("id")
        symbol = order_data.get("symbol", "XAUUSD")
        order_type = order_data.get("order_type", "BUY")
        entry_price = float(order_data.get("entry_price", 0.0))
        exit_price = float(order_data.get("exit_price", entry_price))
        stop_loss = float(order_data.get("stop_loss", entry_price))
        take_profit = float(order_data.get("take_profit", entry_price))
        realized_pnl = float(order_data.get("realized_pnl", 0.0))
        close_reason = order_data.get("close_reason", "MANUAL")
        is_test = bool(order_data.get("is_test", False))
        strategy_trigger = order_data.get("strategy_trigger") or "SMC_SETUP"

        # Thời gian mở / đóng
        open_time_str = order_data.get("open_time")
        close_time_str = order_data.get("close_time")
        open_time = (
            datetime.fromisoformat(open_time_str)
            if open_time_str
            else datetime.now(timezone.utc)
        )
        close_time = (
            datetime.fromisoformat(close_time_str)
            if close_time_str
            else datetime.now(timezone.utc)
        )
        duration_secs = max(1.0, (close_time - open_time).total_seconds())

        # 1. Xác định kết quả lệnh (Outcome)
        if realized_pnl > 0.5:
            outcome = "WIN"
        elif realized_pnl < -0.5:
            outcome = "LOSS"
        else:
            outcome = "BREAKEVEN"

        # 2. Quét bối cảnh tin tức kinh tế xung quanh thời điểm vào/thoát lệnh
        news_context = await self._fetch_news_context(open_time, close_time, session)

        # 3. Phân loại nguyên nhân cốt lõi và bài học kinh nghiệm
        root_cause, lesson_learned, mistake_category, rule_to_add = (
            self._determine_root_cause_and_lesson(
                symbol=symbol,
                order_type=order_type,
                outcome=outcome,
                entry_price=entry_price,
                exit_price=exit_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                realized_pnl=realized_pnl,
                close_reason=close_reason,
                duration_secs=duration_secs,
                strategy_trigger=strategy_trigger,
                news_context=news_context,
            )
        )

        market_context_summary = (
            f"{symbol} {order_type} entry={entry_price:.2f}, exit={exit_price:.2f}, "
            f"PnL={realized_pnl:.2f} USD, reason={close_reason}, duration={int(duration_secs)}s. "
            f"Macro: {news_context.get('summary', 'Normal market conditions')}."
        )

        # 4. Trích xuất vector embedding cho bài học kinh nghiệm (1536 chiều)
        embedding_payload = (
            f"Outcome: {outcome}. Symbol: {symbol} {order_type}. "
            f"Mistake: {mistake_category or 'NONE'}. "
            f"Root cause: {root_cause}. "
            f"Lesson: {lesson_learned}. "
            f"Rule: {rule_to_add}."
        )
        vector = await embedding_service.embed_text(embedding_payload)

        # 5. Đảm bảo order_id tồn tại trong DB trước khi gán foreign key
        valid_order_id = None
        if order_id:
            exists_stmt = select(func.count(SimulatedOrder.id)).where(SimulatedOrder.id == order_id)
            if session is not None:
                exists_count = (await session.execute(exists_stmt)).scalar_one()
            else:
                async with session_factory() as chk_session:
                    exists_count = (await chk_session.execute(exists_stmt)).scalar_one()
            if exists_count > 0:
                valid_order_id = order_id

        # 6. Lưu vào Database
        memory = EpisodicTradeMemory(
            order_id=valid_order_id,
            outcome=outcome,
            market_context_summary=market_context_summary,
            root_cause=root_cause,
            lesson_learned=lesson_learned,
            mistake_category=mistake_category,
            rule_to_add=rule_to_add,
            embedding=vector,
            is_test=is_test,
        )

        if session is not None:
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
        else:
            async with session_factory() as local_session:
                local_session.add(memory)
                await local_session.commit()
                await local_session.refresh(memory)

        logger.info(
            "Reflexion post-mortem generated for Order #%s: %s (Mistake: %s)",
            order_id,
            outcome,
            mistake_category,
        )
        return memory

    async def _fetch_news_context(
        self,
        open_time: datetime,
        close_time: datetime,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Truy vấn các tin tức vĩ mô quan trọng diễn ra trong khoảng thời gian giữ lệnh"""
        start_win = open_time - timedelta(minutes=30)
        end_win = close_time + timedelta(minutes=15)

        async def _query(s: AsyncSession):
            # Tìm sự kiện lịch kinh tế 3 sao
            event_stmt = (
                select(EconomicEvent)
                .where(
                    EconomicEvent.event_timestamp >= start_win,
                    EconomicEvent.event_timestamp <= end_win,
                    EconomicEvent.impact_stars >= 3,
                )
                .limit(3)
            )
            events = (await s.execute(event_stmt)).scalars().all()

            # Tìm tin tức Breaking News tác động cao
            news_stmt = (
                select(FinancialNews)
                .where(
                    FinancialNews.published_at >= start_win,
                    FinancialNews.published_at <= end_win,
                    FinancialNews.impact_level == "HIGH_RISK_HALT",
                )
                .limit(3)
            )
            news_items = (await s.execute(news_stmt)).scalars().all()
            return events, news_items

        try:
            if session:
                events, news_items = await _query(session)
            else:
                async with session_factory() as local_session:
                    events, news_items = await _query(local_session)

            has_high_impact = len(events) > 0 or len(news_items) > 0
            event_titles = [e.title for e in events] + [n.title for n in news_items]
            summary = (
                f"High-impact events observed ({', '.join(event_titles)})"
                if has_high_impact
                else "No high-impact macro news within 30-minute window"
            )

            return {
                "has_high_impact_news": has_high_impact,
                "event_count": len(events) + len(news_items),
                "titles": event_titles,
                "summary": summary,
            }
        except Exception as exc:
            logger.warning("Error fetching news context for reflexion: %s", exc)
            return {
                "has_high_impact_news": False,
                "event_count": 0,
                "titles": [],
                "summary": "Context query unavailable",
            }

    def _determine_root_cause_and_lesson(
        self,
        symbol: str,
        order_type: str,
        outcome: str,
        entry_price: float,
        exit_price: float,
        stop_loss: float,
        take_profit: float,
        realized_pnl: float,
        close_reason: str,
        duration_secs: float,
        strategy_trigger: str,
        news_context: dict[str, Any],
    ) -> tuple[str, str, str | None, str]:
        """Phân tích nguyên nhân và bài học rút ra dựa trên quy tắc định lượng"""
        sl_distance = abs(entry_price - stop_loss)
        tp_distance = abs(take_profit - entry_price)
        rr_ratio = round(tp_distance / sl_distance, 2) if sl_distance > 0 else 1.5

        if outcome == "LOSS":
            # 1. Bị ảnh hưởng bởi tin tức đỏ (News Spikes)
            if news_context.get("has_high_impact_news", False):
                titles = ", ".join(news_context.get("titles", []))
                return (
                    f"Position caught in high-impact macroeconomic announcement spike ({titles}).",
                    "Enforce the strict 30-minute News Circuit Breaker buffer before and after red-flag events.",
                    "TRADED_DURING_NEWS_SPIKE",
                    "Freeze trade execution and cancel pending limit orders 30 minutes around 3-star news releases.",
                )

            # 2. Stop Loss quá ngắn (SL Too Tight)
            # Đối với XAUUSD, khoảng cách SL < 20 points ($2.00) thường bị quét râu nến ngẫu nhiên
            if close_reason == "SL_HIT" and sl_distance <= 20.0:
                return (
                    f"Stop loss distance was only {sl_distance:.2f} points, leaving no room for market spread and wick noise.",
                    "Always place Stop Loss beyond structural invalidation with an additional 0.5x ATR buffer (minimum 25-35 points on XAUUSD).",
                    "SL_TOO_TIGHT",
                    "Expand atr_sl_multiplier to at least 1.80x during volatile trading sessions.",
                )

            # 3. Vào lệnh quá sớm (Early Entry / Front Running)
            # Lệnh bị dừng lỗ trong thời gian cực ngắn (< 3 phút)
            if close_reason == "SL_HIT" and duration_secs < 180.0:
                return (
                    "Price invalidated position immediately after entry, indicating front-running before candle close confirmation.",
                    "Wait for full M15 candle close to confirm structural Change of Character (CHoCH) before execution.",
                    "EARLY_ENTRY",
                    "Require closed M15 candle confirmation instead of immediate touch market entry.",
                )

            # 4. Thoát lệnh thủ công sớm vì tâm lý (Manual Panic Exit)
            if close_reason == "MANUAL":
                return (
                    "Position was manually terminated in loss before reaching the mathematical Stop Loss boundary.",
                    "Trust the established invalidation level and let the mathematical edge play out without emotional interference.",
                    "MANUAL_PANIC_EXIT",
                    "Adhere strictly to rule-based SL/TP boundaries or use automated trailing stop.",
                )

            # 5. Lỗi thông thường / Nhiễu thị trường (Market Noise)
            return (
                f"Position reached stop loss ({sl_distance:.2f} points) due to natural market oscillation.",
                "Accept normal statistical variance; keep risk per trade strictly <= 1.0% to preserve capital.",
                "MARKET_NOISE_OR_NORMAL_VARIANCE",
                "Ensure minimum 1:1.50 Risk:Reward ratio on all setups to sustain positive long-term expectancy.",
            )

        elif outcome == "WIN":
            return (
                f"Order executed successfully reaching target ({close_reason}) with realized R:R of {rr_ratio}.",
                "Discipline in respecting the higher timeframe Point of Interest (POI) and waiting for discount/premium alignment yielded positive edge.",
                None,
                "Maintain confluence requirements (HTF trend + Kill Zone window + POI alignment).",
            )

        else:  # BREAKEVEN
            return (
                "Order reached partial target (> 1.5R) and Stop Loss was successfully moved to entry before market reversal.",
                "Moving Stop Loss to Breakeven at 1.5R protected trading capital from adverse trend exhaustion.",
                None,
                "Retain breakeven_r_multiple at 1.50R.",
            )

    async def search_similar_lessons(
        self,
        query: str,
        outcome: str | None = None,
        mistake_category: str | None = None,
        top_k: int = 3,
        include_test: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Tìm kiếm các bài học trong quá khứ có bối cảnh hoặc lỗi tương tự bằng Semantic Search (pgvector).
        """
        query_vec = await embedding_service.embed_text(query)

        async with session_factory() as session:
            distance_col = EpisodicTradeMemory.embedding.cosine_distance(query_vec).label(
                "distance"
            )
            stmt = select(EpisodicTradeMemory, distance_col)

            if not include_test:
                stmt = stmt.where(EpisodicTradeMemory.is_test.is_(False))

            if outcome:
                stmt = stmt.where(EpisodicTradeMemory.outcome == outcome)

            if mistake_category:
                stmt = stmt.where(
                    EpisodicTradeMemory.mistake_category == mistake_category
                )

            stmt = stmt.order_by(distance_col).limit(top_k)
            res = await session.execute(stmt)

            matches: list[dict[str, Any]] = []
            for row in res.all():
                mem: EpisodicTradeMemory = row[0]
                dist: float = float(row[1]) if row[1] is not None else 1.0
                similarity: float = max(0.0, min(1.0, 1.0 - dist))
                matches.append(
                    {
                        "id": mem.id,
                        "order_id": mem.order_id,
                        "outcome": mem.outcome,
                        "market_context_summary": mem.market_context_summary,
                        "root_cause": mem.root_cause,
                        "lesson_learned": mem.lesson_learned,
                        "mistake_category": mem.mistake_category,
                        "rule_to_add": mem.rule_to_add,
                        "similarity": round(similarity, 4),
                        "distance": round(dist, 4),
                        "is_test": mem.is_test,
                        "created_at": mem.created_at.isoformat()
                        if mem.created_at
                        else None,
                    }
                )

            return matches

    async def get_recent_memories(
        self,
        limit: int = 20,
        outcome: str | None = None,
        mistake_category: str | None = None,
        include_test: bool = False,
    ) -> list[dict[str, Any]]:
        """Lấy danh sách các ký ức giao dịch gần đây nhất"""
        async with session_factory() as session:
            stmt = select(EpisodicTradeMemory)

            if not include_test:
                stmt = stmt.where(EpisodicTradeMemory.is_test.is_(False))
            if outcome:
                stmt = stmt.where(EpisodicTradeMemory.outcome == outcome)
            if mistake_category:
                stmt = stmt.where(
                    EpisodicTradeMemory.mistake_category == mistake_category
                )

            stmt = stmt.order_by(EpisodicTradeMemory.created_at.desc()).limit(limit)
            records = (await session.execute(stmt)).scalars().all()

            return [
                {
                    "id": m.id,
                    "order_id": m.order_id,
                    "outcome": m.outcome,
                    "market_context_summary": m.market_context_summary,
                    "root_cause": m.root_cause,
                    "lesson_learned": m.lesson_learned,
                    "mistake_category": m.mistake_category,
                    "rule_to_add": m.rule_to_add,
                    "is_test": m.is_test,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in records
            ]

    async def get_reflexion_stats(self, include_test: bool = False) -> dict[str, Any]:
        """Tổng hợp thống kê tỷ lệ thắng/thua và phân bổ các nhóm sai lầm"""
        async with session_factory() as session:
            base_filter = []
            if not include_test:
                base_filter.append(EpisodicTradeMemory.is_test.is_(False))

            # Tổng số bản ghi
            total_stmt = select(func.count(EpisodicTradeMemory.id))
            if base_filter:
                total_stmt = total_stmt.where(*base_filter)
            total = (await session.execute(total_stmt)).scalar_one()

            # Thống kê theo Outcome
            outcome_stmt = (
                select(EpisodicTradeMemory.outcome, func.count(EpisodicTradeMemory.id))
                .group_by(EpisodicTradeMemory.outcome)
            )
            if base_filter:
                outcome_stmt = outcome_stmt.where(*base_filter)
            outcome_rows = (await session.execute(outcome_stmt)).all()
            outcomes = {row[0]: row[1] for row in outcome_rows}

            # Thống kê theo Mistake Category
            mistake_stmt = (
                select(
                    EpisodicTradeMemory.mistake_category,
                    func.count(EpisodicTradeMemory.id),
                )
                .where(EpisodicTradeMemory.mistake_category.is_not(None))
                .group_by(EpisodicTradeMemory.mistake_category)
            )
            if base_filter:
                mistake_stmt = mistake_stmt.where(*base_filter)
            mistake_rows = (await session.execute(mistake_stmt)).all()
            mistakes = {row[0]: row[1] for row in mistake_rows}

            return {
                "total_memories": total,
                "outcomes": outcomes,
                "mistake_categories": mistakes,
            }


class ReflexionWorker:
    """
    Worker chạy nền lắng nghe Redis pub/sub channel 'paper:orders'.
    Mỗi khi nhận được sự kiện ORDER_CLOSED, tự động kích hoạt ReflexionService.
    """

    def __init__(self, service: ReflexionService | None = None):
        self.service = service or ReflexionService()
        self._running = False
        self._task: asyncio.Task | None = None

    async def run(self) -> None:
        self._running = True
        logger.info("ReflexionWorker started, listening for ORDER_CLOSED events...")
        while self._running:
            try:
                pubsub = redis_client.pubsub()
                await pubsub.subscribe("paper:orders")
                async for message in pubsub.listen():
                    if not self._running:
                        break
                    if message["type"] != "message":
                        continue
                    try:
                        payload = json.loads(message["data"])
                        if payload.get("event") == "ORDER_CLOSED":
                            order_data = payload.get("data")
                            if order_data:
                                await self.service.analyze_closed_order(order_data)
                    except Exception as inner_exc:
                        logger.warning("Error handling order event in ReflexionWorker: %s", inner_exc)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Redis pubsub error in ReflexionWorker: %s, retrying in 3s...", exc)
                await asyncio.sleep(3.0)

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()


reflexion_service = ReflexionService()
reflexion_worker = ReflexionWorker(reflexion_service)
