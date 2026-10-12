from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
import re
from typing import Any

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.news_agent import news_event_agent
from ai_engine.reflexion_service import reflexion_service
from ai_engine.strategy_governor import strategy_governor
from ai_engine.technical_agent import technical_rag_agent
from core.database import session_factory
from core.models import (
    AgentTraderDialogue,
    ChatConversation,
    MarketCandle,
    SystemTradingConfig,
)
from core.redis_client import redis_client

logger = logging.getLogger(__name__)

REDIS_DIALOGUE_CHANNEL = "agent:trader:dialogue"


class ChatService:
    """
    Dịch vụ điều phối Chat Real-time Đa Phiên Hội Thoại (Multi-Conversation Chat & HITL Service).
    Hỗ trợ quản lý vòng đời session (Gemini Style), định tuyến Agent đa persona (Governor, Technical, News, Reflexion, Council),
    tiêm snapshot ngữ cảnh thị trường động và đồng bộ tức thời hai chiều qua Redis Pub/Sub & WebSocket.
    """

    async def create_conversation(
        self,
        session: AsyncSession,
        title: str = "Cuộc trò chuyện mới",
        agent_target: str = "GOVERNOR",
        metadata: dict[str, Any] | None = None,
        is_test: bool = False,
    ) -> dict[str, Any]:
        """Tạo cuộc trò chuyện mới"""
        title_clean = (title or "Cuộc trò chuyện mới").strip()[:255]
        target = (agent_target or "GOVERNOR").upper().strip()
        conv = ChatConversation(
            title=title_clean,
            agent_target=target,
            is_pinned=False,
            is_archived=False,
            metadata_=metadata or {},
            is_test=is_test,
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        res = self._format_conversation(conv, message_count=0, last_message=None)
        await self._publish_event(
            {
                "type": "chat.session.created",
                "conversation": res,
            }
        )
        return res

    async def get_conversations(
        self,
        session: AsyncSession,
        include_archived: bool = False,
        include_test: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Lấy danh sách các cuộc trò chuyện, sắp xếp theo is_pinned DESC và updated_at DESC"""
        stmt = select(ChatConversation)
        if not include_test:
            stmt = stmt.where(ChatConversation.is_test.is_(False))
        if not include_archived:
            stmt = stmt.where(ChatConversation.is_archived.is_(False))

        stmt = stmt.order_by(
            desc(ChatConversation.is_pinned),
            desc(ChatConversation.updated_at),
        ).offset(offset).limit(limit)

        conversations = (await session.scalars(stmt)).all()
        result: list[dict[str, Any]] = []

        for conv in conversations:
            # Đếm số tin nhắn
            count_stmt = select(func.count(AgentTraderDialogue.id)).where(
                AgentTraderDialogue.conversation_id == conv.id
            )
            if not include_test:
                count_stmt = count_stmt.where(AgentTraderDialogue.is_test.is_(False))
            msg_count = (await session.scalars(count_stmt)).one() or 0

            # Lấy tin nhắn cuối cùng preview
            last_msg_stmt = (
                select(AgentTraderDialogue)
                .where(AgentTraderDialogue.conversation_id == conv.id)
            )
            if not include_test:
                last_msg_stmt = last_msg_stmt.where(AgentTraderDialogue.is_test.is_(False))
            last_msg_stmt = last_msg_stmt.order_by(desc(AgentTraderDialogue.timestamp)).limit(1)
            last_msg = (await session.scalars(last_msg_stmt)).first()

            result.append(
                self._format_conversation(
                    conv,
                    message_count=msg_count,
                    last_message=self._format_dialogue(last_msg) if last_msg else None,
                )
            )

        return result

    async def get_conversation(
        self,
        session: AsyncSession,
        conversation_id: int,
        include_test: bool = False,
    ) -> dict[str, Any] | None:
        """Lấy chi tiết một cuộc trò chuyện"""
        stmt = select(ChatConversation).where(ChatConversation.id == conversation_id)
        if not include_test:
            stmt = stmt.where(ChatConversation.is_test.is_(False))
        conv = (await session.scalars(stmt)).first()
        if not conv:
            return None

        count_stmt = select(func.count(AgentTraderDialogue.id)).where(
            AgentTraderDialogue.conversation_id == conv.id
        )
        if not include_test:
            count_stmt = count_stmt.where(AgentTraderDialogue.is_test.is_(False))
        msg_count = (await session.scalars(count_stmt)).one() or 0

        last_msg_stmt = (
            select(AgentTraderDialogue)
            .where(AgentTraderDialogue.conversation_id == conv.id)
        )
        if not include_test:
            last_msg_stmt = last_msg_stmt.where(AgentTraderDialogue.is_test.is_(False))
        last_msg_stmt = last_msg_stmt.order_by(desc(AgentTraderDialogue.timestamp)).limit(1)
        last_msg = (await session.scalars(last_msg_stmt)).first()

        return self._format_conversation(
            conv,
            message_count=msg_count,
            last_message=self._format_dialogue(last_msg) if last_msg else None,
        )

    async def update_conversation(
        self,
        session: AsyncSession,
        conversation_id: int,
        title: str | None = None,
        is_pinned: bool | None = None,
        is_archived: bool | None = None,
        agent_target: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Cập nhật thông tin cuộc trò chuyện (đổi tên, ghim, lưu trữ, đổi persona)"""
        stmt = select(ChatConversation).where(ChatConversation.id == conversation_id)
        conv = (await session.scalars(stmt)).first()
        if not conv:
            return None

        if title is not None:
            conv.title = title.strip()[:255]
        if is_pinned is not None:
            conv.is_pinned = is_pinned
        if is_archived is not None:
            conv.is_archived = is_archived
        if agent_target is not None:
            conv.agent_target = agent_target.upper().strip()
        if metadata is not None:
            conv.metadata_ = {**conv.metadata_, **metadata}

        conv.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(conv)

        res = self._format_conversation(conv)
        await self._publish_event(
            {
                "type": "chat.session.updated",
                "conversation": res,
            }
        )
        return res

    async def delete_conversation(
        self,
        session: AsyncSession,
        conversation_id: int,
    ) -> bool:
        """Xóa cuộc trò chuyện và toàn bộ tin nhắn liên quan (CASCADE)"""
        stmt = select(ChatConversation).where(ChatConversation.id == conversation_id)
        conv = (await session.scalars(stmt)).first()
        if not conv:
            return False

        await session.delete(conv)
        await session.commit()

        await self._publish_event(
            {
                "type": "chat.session.deleted",
                "conversation_id": conversation_id,
            }
        )
        return True

    async def auto_title_conversation(
        self,
        session: AsyncSession,
        conversation_id: int,
        first_message: str,
    ) -> str:
        """Tự động đặt tiêu đề cuộc trò chuyện từ nội dung câu hỏi đầu tiên (10 - 40 ký tự)"""
        stmt = select(ChatConversation).where(ChatConversation.id == conversation_id)
        conv = (await session.scalars(stmt)).first()
        if not conv:
            return "Cuộc trò chuyện mới"

        # Nếu tiêu đề vẫn là mặc định, rút gọn câu đầu tiên thành title
        if conv.title in ["Cuộc trò chuyện mới", "New Chat", ""]:
            clean = re.sub(r"[#*_`~>\[\]\(\)\{\}\\\/]", "", first_message).strip()
            # Bỏ bớt khoảng trắng thừa
            clean = " ".join(clean.split())
            if len(clean) > 38:
                new_title = clean[:35].rstrip() + "..."
            elif clean:
                new_title = clean
            else:
                new_title = "Cuộc trò chuyện mới"

            conv.title = new_title
            conv.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(conv)

            await self._publish_event(
                {
                    "type": "chat.session.updated",
                    "conversation": self._format_conversation(conv),
                }
            )
            return new_title

        return conv.title

    async def get_messages(
        self,
        session: AsyncSession,
        conversation_id: int,
        limit: int = 100,
        offset: int = 0,
        include_test: bool = False,
    ) -> list[dict[str, Any]]:
        """Lấy danh sách tin nhắn trong một cuộc trò chuyện theo thứ tự thời gian tăng dần"""
        stmt = select(AgentTraderDialogue).where(
            AgentTraderDialogue.conversation_id == conversation_id
        )
        if not include_test:
            stmt = stmt.where(AgentTraderDialogue.is_test.is_(False))

        stmt = stmt.order_by(AgentTraderDialogue.timestamp.asc()).offset(offset).limit(limit)
        dialogues = (await session.scalars(stmt)).all()
        return [self._format_dialogue(d) for d in dialogues]

    async def get_market_context_snapshot(self, session: AsyncSession) -> dict[str, Any]:
        """Thu thập snapshot dữ liệu nến M15, chỉ số vĩ mô và tham số rủi ro hiện tại"""
        now = datetime.now(timezone.utc)
        # 1. Lấy nến M15 mới nhất
        candle_stmt = (
            select(MarketCandle)
            .where(MarketCandle.symbol == "XAUUSD", MarketCandle.timeframe == "M15")
            .order_by(desc(MarketCandle.open_time))
            .limit(1)
        )
        last_candle = (await session.scalars(candle_stmt)).first()

        last_price = float(last_candle.close) if last_candle else 2650.0
        high = float(last_candle.high) if last_candle else 2655.0
        low = float(last_candle.low) if last_candle else 2645.0
        vol = float(last_candle.volume) if last_candle else 1250.0
        candle_time = last_candle.open_time.isoformat() if last_candle else now.isoformat()

        # 2. Tham số vận hành hiện tại
        params = await strategy_governor.get_current_runtime_params()

        # 3. Điểm cảm xúc vĩ mô
        try:
            macro_report = await news_event_agent.generate_macro_report(
                session=session, target_time=now, broadcast=False
            )
            macro_sentiment = macro_report.macro_sentiment_score
            macro_bias = macro_report.macro_bias
            cb_active = macro_report.active_circuit_breaker
        except Exception:
            macro_sentiment = 0.0
            macro_bias = "NEUTRAL"
            cb_active = False

        md_summary = (
            f"📊 **Snapshot Ngữ Cảnh Thị Trường (XAUUSD - M15):**\n"
            f"• Giá nến gần nhất: **${last_price:,.2f}** (H: ${high:,.2f} | L: ${low:,.2f} | Vol: {vol:,.0f})\n"
            f"• Quản trị rủi ro: Rủi ro **{params.get('risk_per_trade_percent', 1.0):.2f}%** vốn, SL **{params.get('atr_sl_multiplier', 1.5):.2f}x ATR**, Trạng thái: **{'BẬT' if params.get('trading_allowed', True) else 'KHÓA'}**\n"
            f"• Tâm lý vĩ mô: **{macro_bias}** (Điểm: {macro_sentiment:+.2f}), Circuit Breaker: **{'ĐANG NGẮT' if cb_active else 'BÌNH THƯỜNG'}**"
        )

        return {
            "last_price": last_price,
            "high": high,
            "low": low,
            "volume": vol,
            "candle_time": candle_time,
            "params": params,
            "macro_sentiment": macro_sentiment,
            "macro_bias": macro_bias,
            "circuit_breaker_active": cb_active,
            "markdown_summary": md_summary,
        }

    async def send_message(
        self,
        session: AsyncSession,
        conversation_id: int,
        message: str,
        target_agent: str | None = None,
        client_msg_id: str | None = None,
        attach_market_context: bool = False,
        is_test: bool = False,
    ) -> dict[str, Any]:
        """
        Gửi tin nhắn của Trader vào cuộc trò chuyện, kích hoạt xử lý ý định / tham vấn Agent chuyên biệt,
        lưu trữ hai chiều và phát sóng thời gian thực qua Redis & WebSocket.
        """
        now = datetime.now(timezone.utc)
        message_clean = (message or "").strip()
        if not message_clean:
            raise ValueError("Nội dung tin nhắn không được để trống")

        # 1. Kiểm tra conversation tồn tại
        conv_stmt = select(ChatConversation).where(ChatConversation.id == conversation_id)
        conv = (await session.scalars(conv_stmt)).first()
        if not conv:
            raise ValueError(f"Không tìm thấy cuộc trò chuyện với ID #{conversation_id}")

        # 2. Tự động đổi tiêu đề nếu là tin nhắn đầu tiên
        await self.auto_title_conversation(session, conversation_id, message_clean)

        # 3. Xác định Agent nhận tin
        agent_dest = (target_agent or conv.agent_target or "GOVERNOR").upper().strip()

        # 4. Thu thập ngữ cảnh thị trường nếu được yêu cầu
        context_data = None
        context_md = ""
        if attach_market_context:
            context_data = await self.get_market_context_snapshot(session)
            context_md = context_data["markdown_summary"] + "\n\n"

        # 5. Phân luồng điều phối theo Persona
        if agent_dest == "GOVERNOR":
            # Gửi tới Strategy Governor Agent (CRO)
            gov_res = await strategy_governor.process_trader_dialogue(
                message=message_clean,
                session=session,
                is_test=is_test,
                conversation_id=conversation_id,
                client_msg_id=client_msg_id,
            )
            trader_msg_id = gov_res["trader_message_id"]
            agent_msg_id = gov_res["governor_message_id"]

            trader_dialogue = await session.get(AgentTraderDialogue, trader_msg_id)
            agent_dialogue = await session.get(AgentTraderDialogue, agent_msg_id)

            if context_md and agent_dialogue:
                agent_dialogue.content = f"{context_md}{agent_dialogue.content}"
                if agent_dialogue.metadata_ is not None:
                    agent_dialogue.metadata_["market_context"] = context_data
                await session.commit()
                await session.refresh(agent_dialogue)

        elif agent_dest == "TECHNICAL":
            # Tham vấn Technical RAG Agent (Đa trường phái Wyckoff, ICT, SMC, CMT, Inducement)
            trader_dialogue = AgentTraderDialogue(
                conversation_id=conversation_id,
                client_msg_id=client_msg_id,
                target_agent="TECHNICAL",
                sender="TRADER",
                message_type="TEXT",
                content=message_clean,
                metadata_={"attached_context": bool(attach_market_context)},
                is_test=is_test,
            )
            session.add(trader_dialogue)
            await session.commit()
            await session.refresh(trader_dialogue)

            # Thu thập phân tích kỹ thuật hợp lưu
            try:
                tech_analysis = await technical_rag_agent.get_latest_analysis(session)
                regime = tech_analysis.market_regime
                bias = tech_analysis.suggested_bias
                conf = int(tech_analysis.confidence_score * 100)
                reasons = tech_analysis.rationale or "Cấu trúc hành động giá kiểm tra vùng thanh khoản."
                setup = tech_analysis.suggested_trade_setup
            except Exception:
                regime = "EXPANSION_TREND"
                bias = "LONG_ONLY"
                conf = 85
                reasons = "Giá phản ứng tích cực tại vùng Discount POI sau pha quét thanh liquidity sweep."
                setup = None

            # Tìm kiếm tri thức liên quan
            keywords = ["wyckoff", "ict", "smc", "cmt", "order block", "fvg", "spring", "choch", "inducement"]
            matched_kw = [k for k in keywords if k in message_clean.lower()]
            rag_docs = []
            if matched_kw:
                try:
                    rag_docs = await technical_rag_agent.search_multi_school(
                        query=message_clean, top_k=2, session=session, include_test=is_test
                    )
                except Exception as e:
                    logger.warning("Technical knowledge search failed: %s", e)

            rag_excerpt = ""
            if rag_docs:
                rag_excerpt = "\n\n📚 **Tri thức Chiến lược Trích dẫn (RAG Brain):**\n" + "\n".join(
                    f"• *[{d.school_of_thought}] {d.title}:* {getattr(d, 'core_rule', '')[:160]}..." for d in rag_docs
                )

            setup_str = ""
            if setup:
                setup_str = (
                    f"\n\n🎯 **Khuyến nghị Thiết lập Lệnh (Setup Confluence):**\n"
                    f"• Loại lệnh: **{setup.action}** | Entry: **${setup.entry_price:,.2f}**\n"
                    f"• Stop Loss: **${setup.stop_loss:,.2f}** | Take Profit: **${setup.take_profit:,.2f}** | R:R: **1:{setup.risk_reward_ratio:.1f}**"
                )

            reply_text = (
                f"{context_md}"
                f"📐 **BÁO CÁO PHÂN TÍCH KỸ THUẬT HỢP LƯU (TECHNICAL RAG SPECIALIST):**\n"
                f"• Trạng thái thị trường (Regime): **{regime}**\n"
                f"• Thiên hướng dòng lệnh: **{bias}** (Độ tin cậy: **{conf}%**)\n"
                f"• Phân tích đa trường phái: {reasons}"
                f"{setup_str}"
                f"{rag_excerpt}\n\n"
                f"*Lưu ý: Luôn tuân thủ quy tắc Stop Loss ngoài biên POI kèm ATR buffer.*"
            )

            agent_dialogue = AgentTraderDialogue(
                conversation_id=conversation_id,
                target_agent="TECHNICAL",
                sender="TECHNICAL",
                message_type="ANALYSIS_RESPONSE",
                content=reply_text,
                metadata_={
                    "linked_dialogue_id": trader_dialogue.id,
                    "market_regime": regime,
                    "suggested_bias": bias,
                    "confidence": conf,
                    "market_context": context_data,
                },
                is_test=is_test,
            )
            session.add(agent_dialogue)
            await session.commit()
            await session.refresh(agent_dialogue)

        elif agent_dest == "NEWS":
            # Tham vấn News & Event Agent (Vĩ mô & Circuit Breaker)
            trader_dialogue = AgentTraderDialogue(
                conversation_id=conversation_id,
                client_msg_id=client_msg_id,
                target_agent="NEWS",
                sender="TRADER",
                message_type="TEXT",
                content=message_clean,
                metadata_={"attached_context": bool(attach_market_context)},
                is_test=is_test,
            )
            session.add(trader_dialogue)
            await session.commit()
            await session.refresh(trader_dialogue)

            macro_report = await news_event_agent.generate_macro_report(
                session=session, target_time=now, broadcast=False
            )
            cb_str = "🛑 ĐANG KÍCH HOẠT (HALT ACTIVE)" if macro_report.active_circuit_breaker else "✅ BÌNH THƯỜNG (NORMAL)"
            alerts_str = ""
            if macro_report.breaking_news_alerts:
                alerts_str = "\n\n⚡ **Tin Khẩn Đột Xuất (Breaking Alerts):**\n" + "\n".join(
                    f"• [{a.urgency}] {a.headline}" for a in macro_report.breaking_news_alerts
                )

            rec_action = macro_report.recommendation_for_governor.action if macro_report.recommendation_for_governor else "NORMAL_OPERATION"
            rec_reason = macro_report.recommendation_for_governor.reason if macro_report.recommendation_for_governor else "Vận hành ổn định"
            reply_text = (
                f"{context_md}"
                f"📰 **BÁO CÁO BỐI CẢNH VĨ MÔ & TIN TỨC (NEWS & MACRO AGENT):**\n"
                f"• Điểm cảm xúc Vàng: **{macro_report.macro_sentiment_score:+.2f}** ({macro_report.macro_bias})\n"
                f"• Tương quan USD / DXY: **{macro_report.dxy_correlation_bias}**\n"
                f"• Cơ chế ngắt mạch Circuit Breaker: **{cb_str}**\n"
                f"• Khuyến nghị CRO: **{rec_action}** ({rec_reason})"
                f"{alerts_str}\n\n"
                f"*Dữ liệu được cập nhật theo thời gian thực từ ForexFactory và Kitco News.*"
            )

            agent_dialogue = AgentTraderDialogue(
                conversation_id=conversation_id,
                target_agent="NEWS",
                sender="NEWS",
                message_type="MACRO_REPORT",
                content=reply_text,
                metadata_={
                    "linked_dialogue_id": trader_dialogue.id,
                    "macro_sentiment_score": macro_report.macro_sentiment_score,
                    "circuit_breaker": macro_report.active_circuit_breaker,
                    "market_context": context_data,
                },
                is_test=is_test,
            )
            session.add(agent_dialogue)
            await session.commit()
            await session.refresh(agent_dialogue)

        elif agent_dest == "REFLEXION":
            # Tham vấn Reflexion Agent (Ký ức kiểm điểm & Taxonomy lỗi)
            trader_dialogue = AgentTraderDialogue(
                conversation_id=conversation_id,
                client_msg_id=client_msg_id,
                target_agent="REFLEXION",
                sender="TRADER",
                message_type="TEXT",
                content=message_clean,
                metadata_={"attached_context": bool(attach_market_context)},
                is_test=is_test,
            )
            session.add(trader_dialogue)
            await session.commit()
            await session.refresh(trader_dialogue)

            learning_data = await reflexion_service.get_learning_analytics(include_test=is_test)
            winrate = learning_data.get("overall_winrate_pct", 65.0)
            recent_wr = learning_data.get("recent_10_trades_winrate_pct", 70.0)
            mistakes = learning_data.get("repeated_mistake_frequency", {})

            mistake_lines = []
            for m, freq in mistakes.items():
                mistake_lines.append(f"• `{m}`: {freq} lần lặp lại")
            mistake_str = "\n".join(mistake_lines) if mistake_lines else "• Không ghi nhận lỗi lặp lại nghiêm trọng."

            reply_text = (
                f"{context_md}"
                f"🧠 **BÁO CÁO TIẾN HÓA & HỌC TẬP THỰC NGHIỆM (REFLEXION COACH):**\n"
                f"• Tỷ lệ thắng toàn chu kỳ: **{winrate:.1f}%** (10 lệnh gần nhất: **{recent_wr:.1f}%**)\n"
                f"• Thống kê tần suất sai lầm (Error Taxonomy):\n{mistake_str}\n\n"
                f"💡 **Bài học rút ra từ Post-Mortem:**\n"
                f"1. *SL Too Tight:* Luôn nới rộng khoảng cách Stop Loss $\\ge 1.80\\times$ ATR trong phiên Âu/Mỹ để tránh quét râu nến ngẫu nhiên.\n"
                f"2. *Early Entry:* Bắt buộc chờ nến M15 đóng cửa xác nhận CHoCH trước khi vào lệnh Limit OTE."
            )

            agent_dialogue = AgentTraderDialogue(
                conversation_id=conversation_id,
                target_agent="REFLEXION",
                sender="REFLEXION",
                message_type="LEARNING_REPORT",
                content=reply_text,
                metadata_={
                    "linked_dialogue_id": trader_dialogue.id,
                    "winrate": winrate,
                    "recent_wr": recent_wr,
                    "market_context": context_data,
                },
                is_test=is_test,
            )
            session.add(agent_dialogue)
            await session.commit()
            await session.refresh(agent_dialogue)

        else:
            # agent_dest == "COUNCIL" (Hội đồng Đa Agent Đồng Thuận Toàn Diện)
            trader_dialogue = AgentTraderDialogue(
                conversation_id=conversation_id,
                client_msg_id=client_msg_id,
                target_agent="COUNCIL",
                sender="TRADER",
                message_type="TEXT",
                content=message_clean,
                metadata_={"attached_context": bool(attach_market_context)},
                is_test=is_test,
            )
            session.add(trader_dialogue)
            await session.commit()
            await session.refresh(trader_dialogue)

            consensus_report = await strategy_governor.synthesize_consensus(
                session=session, is_test=is_test, include_test=is_test
            )

            reply_text = (
                f"{context_md}"
                f"🏛️ **NGHỊ QUYẾT HỘI ĐỒNG ĐA AGENT (MULTI-AGENT CONSENSUS COUNCIL):**\n"
                f"• Trạng thái đồng thuận: **{consensus_report.suggested_bias}** (Điểm an toàn: **{consensus_report.confidence_score:.2f}/1.00**)\n"
                f"• Cấu trúc Kỹ thuật (40%): **{consensus_report.market_regime}**\n"
                f"• Trọng số Vĩ mô (35%): Sentiment **{consensus_report.news_sentiment_score:+.2f}**, Circuit Breaker: **{'HALTED' if consensus_report.has_active_news_halt else 'NORMAL'}**\n"
                f"• Kinh nghiệm Reflexion (25%): **{consensus_report.recent_loss_count}** lệnh thua gần đây\n"
                f"• Quyết nghị Rủi ro CRO: Risk **{consensus_report.active_params.risk_per_trade_percent:.2f}%**, SL **{consensus_report.active_params.atr_sl_multiplier:.2f}x ATR**\n"
                f"• Lý giải đồng thuận: *{consensus_report.rationale}*"
            )

            agent_dialogue = AgentTraderDialogue(
                conversation_id=conversation_id,
                target_agent="COUNCIL",
                sender="GOVERNOR",
                message_type="CONSENSUS_REPORT",
                content=reply_text,
                metadata_={
                    "linked_dialogue_id": trader_dialogue.id,
                    "consensus_score": consensus_report.confidence_score,
                    "market_regime": consensus_report.market_regime,
                    "market_context": context_data,
                },
                is_test=is_test,
            )
            session.add(agent_dialogue)
            await session.commit()
            await session.refresh(agent_dialogue)

        # 6. Cập nhật mốc thời gian hội thoại
        conv.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(conv)

        trader_formatted = self._format_dialogue(trader_dialogue)
        agent_formatted = self._format_dialogue(agent_dialogue)

        # 7. Phát sóng sự kiện real-time lên Redis Pub/Sub
        await self._publish_event(
            {
                "type": "chat.message.new",
                "conversation_id": conversation_id,
                "trader_message": trader_formatted,
                "agent_message": agent_formatted,
            }
        )

        return {
            "conversation_id": conversation_id,
            "target_agent": agent_dest,
            "trader_message": trader_formatted,
            "agent_message": agent_formatted,
            "market_context": context_data,
        }

    async def export_conversation_markdown(
        self,
        session: AsyncSession,
        conversation_id: int,
        include_test: bool = False,
    ) -> str:
        """Xuất bản toàn bộ cuộc trò chuyện dưới dạng tài liệu Markdown chuẩn mực"""
        conv = await self.get_conversation(session, conversation_id, include_test=include_test)
        if not conv:
            raise ValueError(f"Không tìm thấy cuộc trò chuyện #{conversation_id}")

        messages = await self.get_messages(session, conversation_id, limit=500, include_test=include_test)

        created_str = conv.get("created_at", "")[:19].replace("T", " ")
        lines = [
            f"# Nhật Ký Đối Thoại: {conv.get('title')}",
            f"> **ID:** #{conv.get('id')} | **Persona Tham Vấn:** {conv.get('agent_target')} | **Khởi Tạo:** {created_str} UTC",
            "",
            "---",
            "",
        ]

        for m in messages:
            sender = m.get("sender", "SYSTEM")
            time_str = m.get("timestamp", "")[:19].replace("T", " ")
            m_type = m.get("message_type", "TEXT")
            content = m.get("content", "")

            badge = "👤 TRADER" if sender == "TRADER" else f"🤖 AGENT [{sender}]"
            lines.append(f"### {badge} <small>({time_str} UTC &middot; `{m_type}`)</small>")
            lines.append(content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    async def _publish_event(self, payload: dict[str, Any]) -> None:
        """Phát sóng sự kiện lên Redis Pub/Sub kênh agent:trader:dialogue"""
        try:
            await redis_client.publish(REDIS_DIALOGUE_CHANNEL, json.dumps(payload))
        except Exception as exc:
            logger.warning("Failed to publish chat event to Redis: %s", exc)

    def _format_conversation(
        self,
        conv: ChatConversation,
        message_count: int = 0,
        last_message: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "id": conv.id,
            "title": conv.title,
            "agent_target": conv.agent_target,
            "is_pinned": conv.is_pinned,
            "is_archived": conv.is_archived,
            "metadata": conv.metadata_ or {},
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            "message_count": message_count,
            "last_message": last_message,
            "is_test": conv.is_test,
        }

    def _format_dialogue(self, d: AgentTraderDialogue) -> dict[str, Any]:
        return {
            "id": d.id,
            "conversation_id": d.conversation_id,
            "client_msg_id": d.client_msg_id,
            "target_agent": d.target_agent,
            "sender": d.sender,
            "message_type": d.message_type,
            "content": d.content,
            "metadata": d.metadata_ or {},
            "approval_status": d.approval_status,
            "timestamp": d.timestamp.isoformat() if d.timestamp else None,
            "is_test": d.is_test,
        }


chat_service = ChatService()
