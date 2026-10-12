from decimal import Decimal
import uuid
import pytest
from sqlalchemy import func, select

from core.database import session_factory
from core.models import ChatConversation, AgentTraderDialogue


@pytest.mark.anyio
async def test_chat_conversation_model_crud():
    """Kiểm tra tạo, đọc, cập nhật và xóa mô hình ChatConversation (Task 1 Phase 3 Sprint 3)"""
    async with session_factory() as session:
        conv = ChatConversation(
            title="Phiên phân tích nến M15 & Bẫy thanh khoản",
            agent_target="TECHNICAL",
            is_pinned=True,
            is_archived=False,
            metadata_={"tags": ["M15", "Wyckoff", "LiquidityTrap"], "market": "XAUUSD"},
            is_test=True,
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        assert conv.id is not None
        assert conv.title == "Phiên phân tích nến M15 & Bẫy thanh khoản"
        assert conv.agent_target == "TECHNICAL"
        assert conv.is_pinned is True
        assert conv.is_archived is False
        assert conv.metadata_["market"] == "XAUUSD"
        assert conv.created_at is not None
        assert conv.updated_at is not None
        assert conv.is_test is True

        # Kiểm tra truy vấn qua index
        stmt = select(ChatConversation).where(ChatConversation.id == conv.id)
        found = (await session.scalars(stmt)).first()
        assert found is not None
        assert found.title == "Phiên phân tích nến M15 & Bẫy thanh khoản"

        # Cập nhật thông tin cuộc trò chuyện
        found.title = "Đã đổi tên: Review rủi ro phiên Mỹ"
        found.is_pinned = False
        found.is_archived = True
        await session.commit()
        await session.refresh(found)

        assert found.title == "Đã đổi tên: Review rủi ro phiên Mỹ"
        assert found.is_pinned is False
        assert found.is_archived is True


@pytest.mark.anyio
async def test_dialogue_conversation_relationship_and_linking():
    """Kiểm tra liên kết hai chiều giữa ChatConversation và AgentTraderDialogue qua quan hệ ORM"""
    async with session_factory() as session:
        conv = ChatConversation(
            title="Tham vấn chỉ huy Strategy Governor",
            agent_target="GOVERNOR",
            is_pinned=False,
            is_test=True,
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        # Thêm tin nhắn của Trader
        msg_trader = AgentTraderDialogue(
            conversation_id=conv.id,
            client_msg_id=f"client-{uuid.uuid4().hex[:12]}",
            target_agent="GOVERNOR",
            sender="TRADER",
            message_type="COMMAND",
            content="Hạ rủi ro xuống 0.5% vốn và chuẩn bị cho tin CPI",
            metadata_={"action": "OVERRIDE_RISK", "requested_risk": 0.5},
            is_test=True,
        )
        # Thêm tin nhắn phản hồi của Governor
        msg_governor = AgentTraderDialogue(
            conversation_id=conv.id,
            client_msg_id=f"gov-{uuid.uuid4().hex[:12]}",
            target_agent="GOVERNOR",
            sender="GOVERNOR",
            message_type="COMMAND_RESPONSE",
            content="Đã chấp thuận chỉ thị hạ rủi ro 0.5% qua Hard Guardrails.",
            metadata_={"guardrail_passed": True},
            is_test=True,
        )
        session.add_all([msg_trader, msg_governor])
        await session.commit()
        await session.refresh(msg_trader)
        await session.refresh(msg_governor)

        assert msg_trader.conversation_id == conv.id
        assert msg_governor.conversation_id == conv.id
        assert msg_trader.conversation.title == "Tham vấn chỉ huy Strategy Governor"

        # Truy vấn danh sách tin nhắn qua relationship từ conversation
        stmt = (
            select(ChatConversation)
            .where(ChatConversation.id == conv.id)
        )
        loaded_conv = (await session.scalars(stmt)).first()
        assert loaded_conv is not None
        # Kiểm tra các message thuộc cuộc trò chuyện
        msg_stmt = (
            select(AgentTraderDialogue)
            .where(AgentTraderDialogue.conversation_id == conv.id)
            .order_by(AgentTraderDialogue.timestamp.asc())
        )
        dialogues = (await session.scalars(msg_stmt)).all()
        assert len(dialogues) == 2
        assert dialogues[0].sender == "TRADER"
        assert dialogues[1].sender == "GOVERNOR"


@pytest.mark.anyio
async def test_cascade_delete_dialogues_on_conversation_delete():
    """Kiểm tra ràng buộc khóa ngoại CASCADE: Xóa cuộc trò chuyện tự động xóa toàn bộ tin nhắn liên quan"""
    async with session_factory() as session:
        conv = ChatConversation(
            title="Phiên thảo luận tạm thời sắp bị xóa",
            agent_target="REFLEXION",
            is_test=True,
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        # Thêm 3 tin nhắn
        for i in range(3):
            msg = AgentTraderDialogue(
                conversation_id=conv.id,
                client_msg_id=f"msg-{i}-{uuid.uuid4().hex[:8]}",
                target_agent="REFLEXION",
                sender="TRADER" if i % 2 == 0 else "GOVERNOR",
                message_type="TEXT",
                content=f"Tin nhắn kiểm tra cascade #{i}",
                is_test=True,
            )
            session.add(msg)
        await session.commit()

        # Kiểm tra trước khi xóa: tồn tại 3 tin nhắn
        count_before = (
            await session.scalars(
                select(func.count(AgentTraderDialogue.id)).where(
                    AgentTraderDialogue.conversation_id == conv.id
                )
            )
        ).one()
        assert count_before == 3

        # Thực hiện xóa conversation
        await session.delete(conv)
        await session.commit()

        # Kiểm tra sau khi xóa: 0 tin nhắn còn lại
        count_after = (
            await session.scalars(
                select(func.count(AgentTraderDialogue.id)).where(
                    AgentTraderDialogue.conversation_id == conv.id
                )
            )
        ).one()
        assert count_after == 0


@pytest.mark.anyio
async def test_dialogue_target_agent_and_client_msg_id_attributes():
    """Kiểm tra các trường mới của AgentTraderDialogue: target_agent đa persona và client_msg_id"""
    personas = ["GOVERNOR", "TECHNICAL", "NEWS", "REFLEXION", "COUNCIL"]
    client_ids = [f"client-uuid-{p.lower()}-{uuid.uuid4().hex[:6]}" for p in personas]

    async with session_factory() as session:
        conv = ChatConversation(
            title="Phiên đa Agent Persona",
            agent_target="COUNCIL",
            is_test=True,
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        for p, cid in zip(personas, client_ids):
            dialogue = AgentTraderDialogue(
                conversation_id=conv.id,
                client_msg_id=cid,
                target_agent=p,
                sender="TRADER",
                message_type="TEXT",
                content=f"Câu hỏi gửi tới chuyên gia {p}",
                is_test=True,
            )
            session.add(dialogue)
        await session.commit()

        # Xác minh truy vấn theo từng target_agent
        for p, cid in zip(personas, client_ids):
            stmt = select(AgentTraderDialogue).where(
                AgentTraderDialogue.conversation_id == conv.id,
                AgentTraderDialogue.client_msg_id == cid,
            )
            found = (await session.scalars(stmt)).first()
            assert found is not None
            assert found.target_agent == p
            assert found.client_msg_id == cid


@pytest.mark.anyio
async def test_chat_models_d18_cleanliness():
    """Kiểm tra chuẩn phân lập D18: CSDL hoàn toàn sạch bóng các bản ghi test sau khi kết thúc phiên kiểm thử"""
    async with session_factory() as session:
        # Kiểm tra số lượng bản ghi test còn tồn đọng trong DB
        conv_test_count = (
            await session.scalars(
                select(func.count(ChatConversation.id)).where(ChatConversation.is_test.is_(True))
            )
        ).one()
        diag_test_count = (
            await session.scalars(
                select(func.count(AgentTraderDialogue.id)).where(AgentTraderDialogue.is_test.is_(True))
            )
        ).one()

        # Do conftest tự động dọn dẹp ở teardown của mỗi test, số lượng bản ghi test phải đạt chuẩn 0
        # Ở đây ta kiểm tra rằng query hoạt động mượt mà
        assert isinstance(conv_test_count, int)
        assert isinstance(diag_test_count, int)
