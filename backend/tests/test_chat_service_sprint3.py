from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from ai_engine.chat_service import chat_service
from ai_engine.strategy_governor import strategy_governor
from core.database import session_factory
from core.models import AgentTraderDialogue, ChatConversation
from main import app


@pytest.mark.anyio
async def test_conversation_lifecycle_crud():
    """
    Kiểm tra toàn diện vòng đời (CRUD) của phiên hội thoại (ChatConversation):
    Tạo mới -> Lấy danh sách (ưu tiên pinned) -> Cập nhật thông tin -> Xem chi tiết -> Xóa.
    """
    async with session_factory() as session:
        # 1. Tạo 2 phiên hội thoại test D18
        c1 = await chat_service.create_conversation(
            session=session,
            title="Cuộc trò chuyện 1",
            agent_target="GOVERNOR",
            metadata={"source": "test_unit"},
            is_test=True,
        )
        assert c1["id"] is not None
        assert c1["title"] == "Cuộc trò chuyện 1"
        assert c1["agent_target"] == "GOVERNOR"
        assert c1["is_pinned"] is False
        assert c1["is_test"] is True

        c2 = await chat_service.create_conversation(
            session=session,
            title="Cuộc trò chuyện 2 (Pinned)",
            agent_target="TECHNICAL",
            is_test=True,
        )

        # 2. Ghim phiên c2
        updated_c2 = await chat_service.update_conversation(
            session=session,
            conversation_id=c2["id"],
            is_pinned=True,
            title="Cuộc trò chuyện 2 (Đã Ghim)",
        )
        assert updated_c2 is not None
        assert updated_c2["is_pinned"] is True
        assert updated_c2["title"] == "Cuộc trò chuyện 2 (Đã Ghim)"

        # 3. Lấy danh sách kiểm tra thứ tự sắp xếp (Pinned phải lên trước)
        convs = await chat_service.get_conversations(session=session, include_test=True)
        conv_ids = [c["id"] for c in convs]
        assert c2["id"] in conv_ids
        assert c1["id"] in conv_ids

        # c2 được ghim nên phải nằm trước c1 trong danh sách
        c2_idx = conv_ids.index(c2["id"])
        c1_idx = conv_ids.index(c1["id"])
        assert c2_idx < c1_idx

        # 4. Kiểm tra xem chi tiết
        detail_c1 = await chat_service.get_conversation(
            session=session, conversation_id=c1["id"], include_test=True
        )
        assert detail_c1 is not None
        assert detail_c1["id"] == c1["id"]
        assert detail_c1["title"] == "Cuộc trò chuyện 1"

        # 5. Lưu trữ phiên c1 và kiểm tra lọc
        await chat_service.update_conversation(
            session=session, conversation_id=c1["id"], is_archived=True
        )
        unarchived = await chat_service.get_conversations(
            session=session, include_archived=False, include_test=True
        )
        unarchived_ids = [c["id"] for c in unarchived]
        assert c1["id"] not in unarchived_ids
        assert c2["id"] in unarchived_ids

        # 6. Xóa phiên hội thoại
        deleted = await chat_service.delete_conversation(session=session, conversation_id=c1["id"])
        assert deleted is True

        check_deleted = await chat_service.get_conversation(
            session=session, conversation_id=c1["id"], include_test=True
        )
        assert check_deleted is None


@pytest.mark.anyio
async def test_auto_title_conversation():
    """
    Kiểm tra cơ chế tự động đặt tiêu đề thông minh khi Trader gửi tin nhắn đầu tiên.
    """
    async with session_factory() as session:
        # Tạo session với tiêu đề mặc định
        conv = await chat_service.create_conversation(
            session=session,
            title="Cuộc trò chuyện mới",
            agent_target="GOVERNOR",
            is_test=True,
        )
        assert conv["title"] == "Cuộc trò chuyện mới"

        # Tự động rút gọn câu hỏi đầu tiên thành tiêu đề
        first_q = "Đánh giá khả năng bứt phá cản kỹ thuật $2675 và khuyến nghị rủi ro"
        new_title = await chat_service.auto_title_conversation(
            session=session,
            conversation_id=conv["id"],
            first_message=first_q,
        )
        assert "Đánh giá khả năng bứt phá" in new_title
        assert len(new_title) <= 40

        # Lần gọi tiếp theo với tin nhắn khác không được ghi đè tiêu đề đã có
        second_q = "Một câu hỏi hoàn toàn khác về phiên Mỹ"
        kept_title = await chat_service.auto_title_conversation(
            session=session,
            conversation_id=conv["id"],
            first_message=second_q,
        )
        assert kept_title == new_title


@pytest.mark.anyio
async def test_multi_persona_routing_and_messaging():
    """
    Kiểm tra khả năng định tuyến đa Persona:
    GOVERNOR, TECHNICAL, NEWS, REFLEXION, COUNCIL.
    """
    async with session_factory() as session:
        conv = await chat_service.create_conversation(
            session=session,
            title="Phiên Kiểm Thử Đa Persona",
            agent_target="GOVERNOR",
            is_test=True,
        )

        # 1. Gửi tới GOVERNOR (thực thi chỉ thị rủi ro hợp lệ D21/D24)
        gov_res = await chat_service.send_message(
            session=session,
            conversation_id=conv["id"],
            message="Hạ mức rủi ro xuống 0.65% và nới SL lên 2.1x ATR",
            target_agent="GOVERNOR",
            is_test=True,
        )
        assert gov_res["target_agent"] == "GOVERNOR"
        assert gov_res["trader_message"]["sender"] == "TRADER"
        assert gov_res["agent_message"]["sender"] == "GOVERNOR"
        assert "THÀNH CÔNG" in gov_res["agent_message"]["content"]
        assert gov_res["agent_message"]["is_test"] is True

        # 2. Gửi tới TECHNICAL (tham vấn cấu trúc kỹ thuật hợp lưu)
        tech_res = await chat_service.send_message(
            session=session,
            conversation_id=conv["id"],
            message="Phân tích cấu trúc Wyckoff Spring và SMC Order Block hiện tại",
            target_agent="TECHNICAL",
            is_test=True,
        )
        assert tech_res["target_agent"] == "TECHNICAL"
        assert tech_res["agent_message"]["sender"] == "TECHNICAL"
        assert "TECHNICAL RAG SPECIALIST" in tech_res["agent_message"]["content"]
        assert "market_regime" in tech_res["agent_message"]["metadata"]

        # 3. Gửi tới NEWS (tham vấn vĩ mô & Circuit Breaker)
        news_res = await chat_service.send_message(
            session=session,
            conversation_id=conv["id"],
            message="Tình hình tin tức CPI và tương quan DXY hôm nay ra sao?",
            target_agent="NEWS",
            is_test=True,
        )
        assert news_res["target_agent"] == "NEWS"
        assert news_res["agent_message"]["sender"] == "NEWS"
        assert "NEWS & MACRO AGENT" in news_res["agent_message"]["content"]
        assert "macro_sentiment_score" in news_res["agent_message"]["metadata"]

        # 4. Gửi tới REFLEXION (tham vấn kinh nghiệm thực nghiệm & sai lầm)
        ref_res = await chat_service.send_message(
            session=session,
            conversation_id=conv["id"],
            message="Xem lại các bài học kiểm điểm và phân loại sai lầm gần nhất",
            target_agent="REFLEXION",
            is_test=True,
        )
        assert ref_res["target_agent"] == "REFLEXION"
        assert ref_res["agent_message"]["sender"] == "REFLEXION"
        assert "REFLEXION COACH" in ref_res["agent_message"]["content"]
        assert "winrate" in ref_res["agent_message"]["metadata"]

        # 5. Gửi tới COUNCIL (đồng thuận toàn diện 3 Agent + CRO)
        council_res = await chat_service.send_message(
            session=session,
            conversation_id=conv["id"],
            message="Hội đồng hãy tổng hợp ý kiến đa agent và ban hành nghị quyết đồng thuận",
            target_agent="COUNCIL",
            is_test=True,
        )
        assert council_res["target_agent"] == "COUNCIL"
        assert "MULTI-AGENT CONSENSUS COUNCIL" in council_res["agent_message"]["content"]
        assert "consensus_score" in council_res["agent_message"]["metadata"]

        # Kiểm tra danh sách tin nhắn trong thread
        messages = await chat_service.get_messages(
            session=session, conversation_id=conv["id"], include_test=True
        )
        # Tổng cộng 5 cặp = 10 tin nhắn
        assert len(messages) == 10


@pytest.mark.anyio
async def test_market_context_snapshot_and_injection():
    """
    Kiểm tra tính năng chụp snapshot ngữ cảnh thị trường động và tiêm vào câu trả lời của Agent.
    """
    async with session_factory() as session:
        # 1. Lấy snapshot trực tiếp
        snapshot = await chat_service.get_market_context_snapshot(session=session)
        assert "last_price" in snapshot
        assert "params" in snapshot
        assert "macro_sentiment" in snapshot
        assert "markdown_summary" in snapshot
        assert "Snapshot Ngữ Cảnh Thị Trường" in snapshot["markdown_summary"]

        # 2. Gửi tin nhắn kèm cờ attach_market_context=True
        conv = await chat_service.create_conversation(
            session=session,
            title="Kiểm tra Ngữ Cảnh Thị Trường",
            agent_target="GOVERNOR",
            is_test=True,
        )

        res = await chat_service.send_message(
            session=session,
            conversation_id=conv["id"],
            message="Kiểm tra tình trạng vận hành và bối cảnh thị trường",
            target_agent="GOVERNOR",
            attach_market_context=True,
            is_test=True,
        )
        assert res["market_context"] is not None
        assert "Snapshot Ngữ Cảnh Thị Trường" in res["agent_message"]["content"]


@pytest.mark.anyio
async def test_markdown_export():
    """
    Kiểm tra tính năng xuất bản cuộc trò chuyện sang định dạng Markdown chuẩn mực.
    """
    async with session_factory() as session:
        conv = await chat_service.create_conversation(
            session=session,
            title="Phiên Xuất Bản Markdown",
            agent_target="GOVERNOR",
            is_test=True,
        )
        await chat_service.send_message(
            session=session,
            conversation_id=conv["id"],
            message="Chỉ thị tăng rủi ro lên 0.70%",
            target_agent="GOVERNOR",
            is_test=True,
        )

        md_doc = await chat_service.export_conversation_markdown(
            session=session, conversation_id=conv["id"], include_test=True
        )
        assert "# Nhật Ký Đối Thoại: Phiên Xuất Bản Markdown" in md_doc
        assert "👤 TRADER" in md_doc
        assert "🤖 AGENT [GOVERNOR]" in md_doc
        assert "Chỉ thị tăng rủi ro lên 0.70%" in md_doc


@pytest.mark.anyio
async def test_chat_rest_api_endpoints():
    """
    Kiểm tra tích hợp đầy đủ các REST API endpoints tại /api/v1/chat/*.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/v1/chat/personas
        personas_res = await client.get("/api/v1/chat/personas")
        assert personas_res.status_code == 200
        personas = personas_res.json()
        assert len(personas) >= 5
        persona_ids = [p["id"] for p in personas]
        assert "GOVERNOR" in persona_ids
        assert "TECHNICAL" in persona_ids
        assert "NEWS" in persona_ids
        assert "REFLEXION" in persona_ids
        assert "COUNCIL" in persona_ids

        # 2. GET /api/v1/chat/market-context
        ctx_res = await client.get("/api/v1/chat/market-context")
        assert ctx_res.status_code == 200
        assert "last_price" in ctx_res.json()

        # 3. POST /api/v1/chat/conversations (Tạo mới)
        create_res = await client.post(
            "/api/v1/chat/conversations",
            json={
                "title": "API Test Conversation",
                "agent_target": "GOVERNOR",
                "is_test": True,
            },
        )
        assert create_res.status_code == 201
        conv_data = create_res.json()
        conv_id = conv_data["id"]
        assert conv_id is not None
        assert conv_data["title"] == "API Test Conversation"

        # 4. GET /api/v1/chat/conversations (Danh sách)
        list_res = await client.get("/api/v1/chat/conversations?include_test=true")
        assert list_res.status_code == 200
        items = list_res.json()
        assert any(item["id"] == conv_id for item in items)

        # 5. GET /api/v1/chat/conversations/{id} (Chi tiết)
        detail_res = await client.get(f"/api/v1/chat/conversations/{conv_id}?include_test=true")
        assert detail_res.status_code == 200
        assert detail_res.json()["id"] == conv_id

        # 6. PATCH /api/v1/chat/conversations/{id} (Cập nhật tiêu đề & ghim)
        patch_res = await client.patch(
            f"/api/v1/chat/conversations/{conv_id}",
            json={
                "title": "API Test Conversation (Renamed)",
                "is_pinned": True,
            },
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == "API Test Conversation (Renamed)"
        assert patch_res.json()["is_pinned"] is True

        # 7. POST /api/v1/chat/conversations/{id}/messages (Gửi tin nhắn)
        msg_res = await client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages",
            json={
                "message": "Nới SL lên 2.0x ATR và kiểm tra tình hình",
                "target_agent": "GOVERNOR",
                "attach_market_context": True,
                "is_test": True,
            },
        )
        assert msg_res.status_code == 200
        msg_data = msg_res.json()
        assert msg_data["conversation_id"] == conv_id
        assert msg_data["trader_message"]["sender"] == "TRADER"
        assert msg_data["agent_message"]["sender"] == "GOVERNOR"

        # 8. GET /api/v1/chat/conversations/{id}/messages (Lấy thread)
        thread_res = await client.get(
            f"/api/v1/chat/conversations/{conv_id}/messages?include_test=true"
        )
        assert thread_res.status_code == 200
        thread = thread_res.json()
        assert len(thread) >= 2

        # 9. GET /api/v1/chat/conversations/{id}/export (Xuất Markdown và JSON)
        export_md = await client.get(
            f"/api/v1/chat/conversations/{conv_id}/export?format=markdown&include_test=true"
        )
        assert export_md.status_code == 200
        assert "text/markdown" in export_md.headers["content-type"]
        assert "Nhật Ký Đối Thoại" in export_md.text

        export_json = await client.get(
            f"/api/v1/chat/conversations/{conv_id}/export?format=json&include_test=true"
        )
        assert export_json.status_code == 200
        assert "markdown" in export_json.json()

        # 10. POST /api/v1/chat/respond-approval (Phê duyệt lệnh)
        async with session_factory() as session:
            approval_req = AgentTraderDialogue(
                conversation_id=conv_id,
                target_agent="GOVERNOR",
                sender="GOVERNOR",
                message_type="APPROVAL_REQUEST",
                content="[TEST] Yêu cầu phê duyệt BUY XAUUSD tại 2650.00",
                approval_status="PENDING",
                metadata_={"symbol": "XAUUSD", "action": "BUY", "volume": 0.1},
                is_test=True,
            )
            session.add(approval_req)
            await session.commit()
            await session.refresh(approval_req)
            req_id = approval_req.id

        approval_res = await client.post(
            "/api/v1/chat/respond-approval",
            json={
                "dialogue_id": req_id,
                "action": "APPROVE",
                "is_test": True,
            },
        )
        assert approval_res.status_code == 200
        assert approval_res.json()["action"] == "APPROVE"
        assert approval_res.json()["new_status"] == "APPROVED"

        # 11. DELETE /api/v1/chat/conversations/{id}
        del_res = await client.delete(f"/api/v1/chat/conversations/{conv_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # 12. Kiểm tra truy cập sau khi xóa trả về 404
        get_404 = await client.get(f"/api/v1/chat/conversations/{conv_id}?include_test=true")
        assert get_404.status_code == 404
