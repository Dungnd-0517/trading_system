from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.reflexion_service import reflexion_agent
from core.database import get_db

router = APIRouter()


class PromotedRuleResponse(BaseModel):
    status: str
    memory_id: int
    knowledge_id: int
    title: str
    mistake_category: str
    rule_to_add: str
    promoted_at: str


class CandidateRuleItem(BaseModel):
    mistake_category: str
    frequency: int
    status: str
    latest_memory_id: int
    suggested_rule: str
    already_promoted: bool


class LearningAnalyticsResponse(BaseModel):
    total_memories: int
    overall_winrate: float
    recent_10_trades_winrate: float
    repeated_mistake_frequency: dict[str, int]
    candidates_for_promotion: list[CandidateRuleItem]
    learning_curve: list[dict[str, Any]]
    timestamp: str


class FeedbackReportResponse(BaseModel):
    agent: str
    timestamp: str
    evaluated_order_id: int
    outcome: str
    realized_pnl: float
    mistake_category: str | None
    root_cause_analysis: str
    lesson_learned: str
    rule_to_add: str
    promotion_status: str
    learning_analytics: dict[str, Any]


@router.get("/analytics", response_model=LearningAnalyticsResponse)
async def get_learning_analytics(
    include_test: bool = Query(False, description="Bao gồm dữ liệu test"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy thống kê đường cong học tập (Learning Curve), tỷ lệ thắng gần nhất,
    tần suất các nhóm sai lầm lặp lại và các ứng viên sẵn sàng thăng cấp quy tắc.
    """
    try:
        analytics = await reflexion_agent.get_learning_analytics(
            include_test=include_test, session=db
        )
        return analytics
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi trích xuất phân tích học tập: {exc}"
        )


@router.post("/promote-rule/{memory_id}", response_model=PromotedRuleResponse)
async def promote_rule_to_knowledge(
    memory_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Thăng cấp bài học từ episodic_trade_memory thành quy tắc chính thức trong CSDL tri thức trading_knowledge
    thuộc trường phái POST_MORTEM để toàn bộ hệ thống tham chiếu dài hạn.
    """
    try:
        result = await reflexion_agent.promote_memory_to_rule(
            memory_id=memory_id, session=db
        )
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi thăng cấp quy tắc giao dịch: {exc}"
        )


@router.get("/feedback-report/{order_id}", response_model=FeedbackReportResponse)
async def get_feedback_report(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy báo cáo phân tích sâu ReflexionFeedbackReport cho một lệnh đã đóng
    kèm phân tích nguyên nhân cốt lõi và trạng thái đề xuất thăng cấp.
    """
    try:
        report = await reflexion_agent.generate_feedback_report(
            order_id=order_id, session=db
        )
        return report
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi tạo báo cáo phản hồi: {exc}"
        )


@router.get("/memories")
async def get_recent_memories(
    limit: int = Query(20, ge=1, le=100, description="Số lượng bản ghi tối đa"),
    outcome: str | None = Query(None, description="Lọc theo kết quả: WIN, LOSS, BREAKEVEN"),
    mistake_category: str | None = Query(None, description="Lọc theo phân loại lỗi"),
    include_test: bool = Query(False, description="Bao gồm dữ liệu test"),
):
    """
    Lấy danh sách các ký ức giao dịch gần đây nhất từ Reflexion Memory.
    """
    try:
        return await reflexion_agent.get_recent_memories(
            limit=limit,
            outcome=outcome,
            mistake_category=mistake_category,
            include_test=include_test,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi khi đọc ký ức giao dịch: {exc}")


@router.get("/search")
async def search_memories(
    query: str = Query(..., min_length=2, description="Nội dung tìm kiếm ngữ nghĩa"),
    outcome: str | None = Query(None, description="Lọc theo kết quả"),
    mistake_category: str | None = Query(None, description="Lọc theo phân loại lỗi"),
    top_k: int = Query(3, ge=1, le=10, description="Số lượng kết quả hàng đầu"),
    include_test: bool = Query(False, description="Bao gồm dữ liệu test"),
):
    """
    Tìm kiếm ngữ nghĩa các bài học trong quá khứ bằng pgvector Cosine Distance.
    """
    try:
        return await reflexion_agent.search_similar_lessons(
            query=query,
            outcome=outcome,
            mistake_category=mistake_category,
            top_k=top_k,
            include_test=include_test,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi tìm kiếm ký ức: {exc}")
