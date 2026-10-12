from typing import Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.chat_service import chat_service
from ai_engine.strategy_governor import strategy_governor
from core.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateConversationRequest(BaseModel):
    title: str = Field(default="Cuộc trò chuyện mới", max_length=255, description="Tiêu đề cuộc trò chuyện")
    agent_target: str = Field(default="GOVERNOR", max_length=64, description="Persona Agent mặc định")
    metadata: dict[str, Any] | None = Field(default=None, description="Metadata mở rộng")
    is_test: bool = Field(default=False, description="Cờ môi trường kiểm thử D18")


class UpdateConversationRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255, description="Tiêu đề cập nhật")
    is_pinned: bool | None = Field(default=None, description="Trạng thái ghim")
    is_archived: bool | None = Field(default=None, description="Trạng thái lưu trữ")
    agent_target: str | None = Field(default=None, max_length=64, description="Persona Agent")
    metadata: dict[str, Any] | None = Field(default=None, description="Metadata cập nhật")


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="Nội dung tin nhắn từ Trader")
    target_agent: str | None = Field(default=None, description="Chỉ định persona nhận tin (nếu khác mặc định)")
    client_msg_id: str | None = Field(default=None, max_length=64, description="UUID tin nhắn từ client chống trùng lặp")
    attach_market_context: bool = Field(default=False, description="Tự động tiêm snapshot ngữ cảnh thị trường vào câu trả lời")
    is_test: bool = Field(default=False, description="Cờ môi trường kiểm thử D18")


class ChatApprovalRequest(BaseModel):
    dialogue_id: int = Field(..., description="ID của bản ghi yêu cầu phê duyệt trong agent_trader_dialogue")
    action: str = Field(..., description="'APPROVE' hoặc 'REJECT'")
    is_test: bool = Field(default=False, description="Cờ môi trường kiểm thử D18")


@router.get("/conversations", response_model=list[dict[str, Any]])
async def list_conversations(
    include_archived: bool = Query(default=False, description="Bao gồm các phiên đã lưu trữ"),
    include_test: bool = Query(default=False, description="Bao gồm dữ liệu test D18"),
    limit: int = Query(default=50, ge=1, le=200, description="Giới hạn số phiên trả về"),
    offset: int = Query(default=0, ge=0, description="Phân trang offset"),
    session: AsyncSession = Depends(get_session),
):
    """
    Lấy danh sách các cuộc trò chuyện (Multi-Conversation Sidebar),
    sắp xếp ưu tiên các cuộc trò chuyện được Ghim (is_pinned) lên đầu và thời gian cập nhật mới nhất.
    """
    return await chat_service.get_conversations(
        session=session,
        include_archived=include_archived,
        include_test=include_test,
        limit=limit,
        offset=offset,
    )


@router.post("/conversations", status_code=status.HTTP_201_CREATED, response_model=dict[str, Any])
async def create_conversation(
    payload: CreateConversationRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Tạo một cuộc trò chuyện mới (New Chat session).
    Phát sóng sự kiện chat.session.created qua Redis & WebSocket.
    """
    try:
        return await chat_service.create_conversation(
            session=session,
            title=payload.title,
            agent_target=payload.agent_target,
            metadata=payload.metadata,
            is_test=payload.is_test,
        )
    except Exception as exc:
        logger.error("Failed to create conversation: %s", exc)
        raise HTTPException(status_code=500, detail=f"Không thể tạo cuộc trò chuyện: {exc}")


@router.get("/conversations/{conversation_id}", response_model=dict[str, Any])
async def get_conversation_detail(
    conversation_id: int,
    include_test: bool = Query(default=False, description="Bao gồm dữ liệu test D18"),
    session: AsyncSession = Depends(get_session),
):
    """
    Lấy thông tin chi tiết của một cuộc trò chuyện.
    """
    conv = await chat_service.get_conversation(
        session=session,
        conversation_id=conversation_id,
        include_test=include_test,
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cuộc trò chuyện #{conversation_id}",
        )
    return conv


@router.patch("/conversations/{conversation_id}", response_model=dict[str, Any])
async def update_conversation(
    conversation_id: int,
    payload: UpdateConversationRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Cập nhật cuộc trò chuyện: đổi tên tiêu đề, ghim (pin), lưu trữ (archive) hoặc đổi persona mặc định.
    """
    updated = await chat_service.update_conversation(
        session=session,
        conversation_id=conversation_id,
        title=payload.title,
        is_pinned=payload.is_pinned,
        is_archived=payload.is_archived,
        agent_target=payload.agent_target,
        metadata=payload.metadata,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cuộc trò chuyện #{conversation_id}",
        )
    return updated


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Xóa vĩnh viễn một cuộc trò chuyện và toàn bộ lịch sử tin nhắn liên quan (CASCADE).
    """
    success = await chat_service.delete_conversation(
        session=session,
        conversation_id=conversation_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cuộc trò chuyện #{conversation_id}",
        )
    return {"status": "deleted", "conversation_id": conversation_id}


@router.get("/conversations/{conversation_id}/messages", response_model=list[dict[str, Any]])
async def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(default=100, ge=1, le=500, description="Số lượng tin nhắn"),
    offset: int = Query(default=0, ge=0, description="Offset phân trang"),
    include_test: bool = Query(default=False, description="Bao gồm dữ liệu test D18"),
    session: AsyncSession = Depends(get_session),
):
    """
    Lấy toàn bộ lịch sử luồng tin nhắn (Message Thread) trong cuộc trò chuyện theo thứ tự thời gian tăng dần.
    """
    conv = await chat_service.get_conversation(
        session=session,
        conversation_id=conversation_id,
        include_test=include_test,
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cuộc trò chuyện #{conversation_id}",
        )

    return await chat_service.get_messages(
        session=session,
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
        include_test=include_test,
    )


@router.post("/conversations/{conversation_id}/messages", response_model=dict[str, Any])
async def send_conversation_message(
    conversation_id: int,
    payload: SendMessageRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Gửi tin nhắn Trader vào cuộc trò chuyện, kích hoạt xử lý nghiệp vụ Agent và trả về cặp tin nhắn (Trader + Agent Response).
    Phát sóng thời gian thực qua Redis Pub/Sub kênh agent:trader:dialogue.
    """
    try:
        return await chat_service.send_message(
            session=session,
            conversation_id=conversation_id,
            message=payload.message,
            target_agent=payload.target_agent,
            client_msg_id=payload.client_msg_id,
            attach_market_context=payload.attach_market_context,
            is_test=payload.is_test,
        )
    except ValueError as val_err:
        err_msg = str(val_err)
        if "Không tìm thấy" in err_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as exc:
        logger.error("Failed to process conversation message: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý tin nhắn: {exc}")


@router.get("/conversations/{conversation_id}/export")
async def export_conversation(
    conversation_id: int,
    format: str = Query(default="markdown", description="'markdown' hoặc 'json'"),
    include_test: bool = Query(default=False, description="Bao gồm dữ liệu test D18"),
    session: AsyncSession = Depends(get_session),
):
    """
    Xuất bản toàn bộ cuộc trò chuyện dưới dạng tài liệu Markdown chuẩn mực để tải về hoặc lưu trữ.
    """
    try:
        md_text = await chat_service.export_conversation_markdown(
            session=session,
            conversation_id=conversation_id,
            include_test=include_test,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        logger.error("Failed to export conversation markdown: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi xuất bản hội thoại: {exc}")

    if format.lower() == "json":
        return {"conversation_id": conversation_id, "markdown": md_text}

    filename = f"chat_conversation_{conversation_id}.md"
    return PlainTextResponse(
        content=md_text,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/respond-approval", response_model=dict[str, Any])
async def respond_chat_approval(
    payload: ChatApprovalRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Xử lý phản hồi phê duyệt (APPROVE) hoặc từ chối (REJECT) từ Trader trực tiếp trong Interactive Card của Chat UI.
    """
    try:
        res = await strategy_governor.respond_trade_approval(
            dialogue_id=payload.dialogue_id,
            action=payload.action,
            session=session,
            is_test=payload.is_test,
        )
        return {
            **res,
            "action": payload.action.upper(),
            "new_status": res["status"],
        }
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        logger.error("Failed to respond to trade approval: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi phản hồi phê duyệt lệnh: {exc}")


@router.get("/market-context", response_model=dict[str, Any])
async def get_market_context_snapshot(
    session: AsyncSession = Depends(get_session),
):
    """
    Lấy snapshot ngữ cảnh thị trường động hiện tại (nến XAUUSD M15, tham số rủi ro, điểm cảm xúc vĩ mô và circuit breaker).
    """
    try:
        return await chat_service.get_market_context_snapshot(session)
    except Exception as exc:
        logger.error("Failed to retrieve market context snapshot: %s", exc)
        raise HTTPException(status_code=500, detail=f"Không thể thu thập ngữ cảnh thị trường: {exc}")


@router.get("/personas", response_model=list[dict[str, Any]])
async def list_agent_personas():
    """
    Danh sách các AI Agent Persona sẵn sàng tham vấn và mô tả trách nhiệm nghiệp vụ.
    """
    return [
        {
            "id": "GOVERNOR",
            "name": "Strategy Governor (CRO)",
            "title": "Giám Đốc Quản Trị Rủi Ro & Điều Hành Chiến Lược",
            "avatar": "🛡️",
            "description": "Thẩm định rủi ro đa tầng, phê duyệt lệnh giao dịch, giám sát Drawdown và điều chỉnh tham số vận hành.",
            "is_default": True,
        },
        {
            "id": "TECHNICAL",
            "name": "Technical RAG Specialist",
            "title": "Chuyên Gia Phân Tích Kỹ Thuật Đa Trường Phái",
            "avatar": "📐",
            "description": "Phân tích cấu trúc thị trường Wyckoff, SMC/ICT Liquidity Sweep, CMT Chart Patterns và tìm kiếm điểm hội lưu POI.",
            "is_default": False,
        },
        {
            "id": "NEWS",
            "name": "News & Macro Event Agent",
            "title": "Chuyên Gia Vĩ Mô & Giám Sát Tin Tức Khẩn",
            "avatar": "📰",
            "description": "Theo dõi ForexFactory, Kitco News, phân tích tương quan DXY, đo lường điểm cảm xúc và kích hoạt Circuit Breaker.",
            "is_default": False,
        },
        {
            "id": "REFLEXION",
            "name": "Reflexion Learning Coach",
            "title": "Trợ Lý Đúc Rút Kinh Nghiệm & Hồi Tưởng",
            "avatar": "🧠",
            "description": "Phân tích nhật ký Post-Mortem, thống kê phân loại sai lầm lặp lại (Taxonomy) và nâng cấp bộ quy tắc phản xạ.",
            "is_default": False,
        },
        {
            "id": "COUNCIL",
            "name": "Multi-Agent Consensus Council",
            "title": "Hội Đồng Đa Agent Đồng Thuận Toàn Diện",
            "avatar": "🏛️",
            "description": "Tổng hợp ý kiến từ 3 Agent chuyên biệt (Technical 40%, News 35%, Reflexion 25%) và ban hành nghị quyết đồng thuận.",
            "is_default": False,
        },
    ]
