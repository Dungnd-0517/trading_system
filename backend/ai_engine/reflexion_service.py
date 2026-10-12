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
from core.models import (
    EconomicEvent,
    EpisodicTradeMemory,
    FinancialNews,
    SimulatedOrder,
    TradingKnowledge,
)
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

    async def promote_memory_to_rule(
        self, memory_id: int, session: AsyncSession | None = None
    ) -> dict[str, Any]:
        """
        Thăng cấp bài học từ episodic_trade_memory thành quy tắc chính thức trong trading_knowledge:
        - Gán school_of_thought = 'POST_MORTEM', category = 'MISTAKE_CORRECTION'
        - source_type = 'REFLEXION_PROMOTED' (hoặc 'TEST' nếu memory.is_test)
        - Vectorize nội dung 1536d và lưu trữ kèm GIN metadata
        """
        async def _run_promote(s: AsyncSession) -> dict[str, Any]:
            mem = await s.get(EpisodicTradeMemory, memory_id)
            if not mem:
                raise ValueError(f"Trade memory #{memory_id} not found")

            mistake = mem.mistake_category or "GENERAL_POST_MORTEM"
            rule_text = mem.rule_to_add or mem.lesson_learned or "Adhere strictly to risk parameters."

            # Tiêu đề chuẩn hóa
            title_prefix = "TEST " if mem.is_test else ""
            title = f"{title_prefix}Promoted Rule from Reflexion: [{mistake}] {rule_text[:70]}"

            content = (
                f"# Quy Tắc Thăng Cấp từ Ký Ức Giao Dịch: {mistake}\n\n"
                f"- **Bối Cảnh Thị Trường:** {mem.market_context_summary}\n"
                f"- **Nguyên Nhân Cốt Lõi:** {mem.root_cause or 'N/A'}\n"
                f"- **Bài Học Rút Ra:** {mem.lesson_learned}\n"
                f"- **Quy Tắc Vận Hành Bắt Buộc:** {rule_text}\n\n"
                f"*Nguồn gốc: Thăng cấp tự động từ Reflexion Agent (Memory #{mem.id}, Order #{mem.order_id or 'N/A'}).*"
            )

            # Metadata
            school = "TEST" if mem.is_test else "POST_MORTEM"
            category = "TEST" if mem.is_test else "MISTAKE_CORRECTION"
            source_type = "TEST" if mem.is_test else "REFLEXION_PROMOTED"

            meta = {
                "sub_categories": [mistake, "EMPIRICAL_LESSON"],
                "tags": ["REFLEXION", "PROMOTED_RULE", mistake],
                "academic_reference": f"Reflexion Feedback Loop (Memory #{mem.id})",
                "core_rule": rule_text,
                "promoted_from_memory_id": mem.id,
                "evaluated_order_id": mem.order_id,
                "promoted_at": datetime.now(timezone.utc).isoformat(),
            }

            vec = await embedding_service.embed_text(f"{title}\n{content}")

            knowledge_obj = TradingKnowledge(
                title=title,
                school_of_thought=school,
                category=category,
                content=content,
                source_type=source_type,
                verified_by_trader=True,
                confidence_score=Decimal("0.95"),
                metadata_=meta,
                embedding=vec,
            )
            s.add(knowledge_obj)
            await s.commit()
            await s.refresh(knowledge_obj)

            logger.info("Promoted memory #%d to TradingKnowledge #%d (%s)", mem.id, knowledge_obj.id, title)

            return {
                "status": "PROMOTED",
                "memory_id": mem.id,
                "knowledge_id": knowledge_obj.id,
                "title": title,
                "mistake_category": mistake,
                "rule_to_add": rule_text,
                "promoted_at": datetime.now(timezone.utc).isoformat(),
            }

        if session is not None:
            return await _run_promote(session)
        async with session_factory() as local_s:
            return await _run_promote(local_s)

    async def get_learning_analytics(
        self, include_test: bool = False, session: AsyncSession | None = None
    ) -> dict[str, Any]:
        """
        Thống kê phân tích đường cong học tập (Learning Curve), tỷ lệ thắng gần nhất,
        tần suất lỗi lặp lại và danh sách các ứng viên quy tắc chờ thăng cấp (Rule Promotion Candidates).
        """
        async def _run_analytics(s: AsyncSession) -> dict[str, Any]:
            # Đọc 20 lệnh gần nhất
            stmt = select(EpisodicTradeMemory).order_by(EpisodicTradeMemory.created_at.desc())
            if not include_test:
                stmt = stmt.where(EpisodicTradeMemory.is_test.is_(False))
            recent_20 = (await s.execute(stmt.limit(20))).scalars().all()

            # Tổng số bản ghi
            count_stmt = select(func.count(EpisodicTradeMemory.id))
            if not include_test:
                count_stmt = count_stmt.where(EpisodicTradeMemory.is_test.is_(False))
            total_count = (await s.execute(count_stmt)).scalar_one()

            # Tỷ lệ thắng toàn bộ
            win_count_stmt = select(func.count(EpisodicTradeMemory.id)).where(EpisodicTradeMemory.outcome == "WIN")
            if not include_test:
                win_count_stmt = win_count_stmt.where(EpisodicTradeMemory.is_test.is_(False))
            total_wins = (await s.execute(win_count_stmt)).scalar_one()
            overall_winrate = round(total_wins / total_count, 2) if total_count > 0 else 0.0

            # 10 lệnh gần nhất
            recent_10 = recent_20[:10]
            recent_10_wins = sum(1 for m in recent_10 if m.outcome == "WIN")
            recent_10_winrate = round(recent_10_wins / len(recent_10), 2) if recent_10 else 0.0

            # Tần suất các lỗi trong 10-20 lệnh gần nhất
            mistake_freq: dict[str, int] = {}
            mistake_latest_memory: dict[str, EpisodicTradeMemory] = {}
            for m in recent_20:
                if m.mistake_category:
                    mistake_freq[m.mistake_category] = mistake_freq.get(m.mistake_category, 0) + 1
                    if m.mistake_category not in mistake_latest_memory:
                        mistake_latest_memory[m.mistake_category] = m

            # Kiểm tra xem lỗi nào đã được thăng cấp trong trading_knowledge chưa
            promoted_rules_stmt = select(TradingKnowledge.title).where(
                TradingKnowledge.source_type.in_(["REFLEXION_PROMOTED", "TEST"])
            )
            promoted_titles = (await s.execute(promoted_rules_stmt)).scalars().all()
            promoted_str = " ".join(promoted_titles)

            candidates_for_promotion = []
            for cat, freq in mistake_freq.items():
                if freq >= 2:
                    already_promoted = cat in promoted_str
                    latest_mem = mistake_latest_memory[cat]
                    candidates_for_promotion.append({
                        "mistake_category": cat,
                        "frequency": freq,
                        "status": "ALREADY_PROMOTED" if already_promoted else "READY_FOR_PROMOTION",
                        "latest_memory_id": latest_mem.id,
                        "suggested_rule": latest_mem.rule_to_add or latest_mem.lesson_learned,
                        "already_promoted": already_promoted,
                    })

            # Learning curve checkpoints: Tỷ lệ winrate theo từng block 5 lệnh
            learning_curve = []
            for i in range(0, len(recent_20), 5):
                chunk = recent_20[i:i+5]
                w = sum(1 for c in chunk if c.outcome == "WIN")
                learning_curve.append({
                    "batch": f"Trades {i+1}-{i+len(chunk)}",
                    "winrate": round(w / len(chunk), 2) if chunk else 0.0,
                })

            return {
                "total_memories": total_count,
                "overall_winrate": overall_winrate,
                "recent_10_trades_winrate": recent_10_winrate,
                "repeated_mistake_frequency": mistake_freq,
                "candidates_for_promotion": candidates_for_promotion,
                "learning_curve": learning_curve,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        if session is not None:
            return await _run_analytics(session)
        async with session_factory() as local_s:
            return await _run_analytics(local_s)

    async def generate_feedback_report(
        self, order_id: int, session: AsyncSession | None = None
    ) -> dict[str, Any]:
        """
        Tạo báo cáo phản hồi Reflexion chuyên sâu (ReflexionFeedbackReport) cho một lệnh giao dịch.
        """
        async def _run_report(s: AsyncSession) -> dict[str, Any]:
            mem_stmt = select(EpisodicTradeMemory).where(
                (EpisodicTradeMemory.order_id == order_id) | (EpisodicTradeMemory.id == order_id)
            ).order_by(EpisodicTradeMemory.created_at.desc()).limit(1)
            mem = (await s.execute(mem_stmt)).scalar_one_or_none()

            if not mem:
                order = await s.get(SimulatedOrder, order_id)
                if order:
                    order_data = {
                        "id": order.id,
                        "symbol": order.symbol,
                        "order_type": order.order_type,
                        "entry_price": float(order.entry_price),
                        "exit_price": float(order.exit_price) if order.exit_price is not None else float(order.entry_price),
                        "stop_loss": float(order.stop_loss),
                        "take_profit": float(order.take_profit),
                        "realized_pnl": float(order.realized_pnl) if order.realized_pnl is not None else 0.0,
                        "close_reason": order.close_reason or "MANUAL",
                        "open_time": order.open_time.isoformat() if order.open_time else None,
                        "close_time": order.close_time.isoformat() if order.close_time else None,
                        "is_test": order.is_test,
                        "strategy_trigger": order.strategy_trigger,
                    }
                    mem = await self.analyze_closed_order(order_data, session=s)
                else:
                    raise ValueError(f"Order #{order_id} not found in database")

            analytics = await self.get_learning_analytics(include_test=mem.is_test, session=s)
            mistake_freq = analytics["repeated_mistake_frequency"]
            freq = mistake_freq.get(mem.mistake_category, 1) if mem.mistake_category else 0

            if freq >= 2:
                promotion_status = "READY_FOR_GOVERNOR_APPROVAL"
            elif mem.outcome == "LOSS":
                promotion_status = "EVALUATED_MONITORING"
            else:
                promotion_status = "NOT_ELIGIBLE"

            return {
                "agent": "REFLEXION_AGENT",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "evaluated_order_id": mem.order_id or mem.id,
                "outcome": mem.outcome,
                "realized_pnl": 0.0,
                "mistake_category": mem.mistake_category,
                "root_cause_analysis": mem.root_cause or "Normal market execution.",
                "lesson_learned": mem.lesson_learned,
                "rule_to_add": mem.rule_to_add or "Maintain established parameters.",
                "promotion_status": promotion_status,
                "learning_analytics": {
                    "total_memories": analytics["total_memories"],
                    "recent_10_trades_winrate": analytics["recent_10_trades_winrate"],
                    "repeated_mistake_frequency": analytics["repeated_mistake_frequency"],
                },
            }

        if session is not None:
            return await _run_report(session)
        async with session_factory() as local_s:
            return await _run_report(local_s)


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
reflexion_agent = reflexion_service
reflexion_worker = ReflexionWorker(reflexion_service)
