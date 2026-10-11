from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from ai_engine.reflexion_service import reflexion_service
from core.database import session_factory
from core.models import SimulatedOrder

router = APIRouter()


class MemoryItemResponse(BaseModel):
    id: int
    order_id: int | None
    outcome: str
    market_context_summary: str
    root_cause: str | None
    lesson_learned: str
    mistake_category: str | None
    rule_to_add: str | None
    is_test: bool
    created_at: str | None


class SearchMemoryResponse(MemoryItemResponse):
    similarity: float
    distance: float


class ReflexionStatsResponse(BaseModel):
    total_memories: int
    outcomes: dict[str, int]
    mistake_categories: dict[str, int]


@router.get("/memories", response_model=list[MemoryItemResponse])
async def get_recent_memories(
    limit: int = Query(20, ge=1, le=100, description="Số lượng bản ghi tối đa"),
    outcome: str | None = Query(None, description="Lọc theo kết quả: WIN, LOSS, BREAKEVEN"),
    mistake_category: str | None = Query(None, description="Lọc theo phân loại lỗi"),
    include_test: bool = Query(False, description="Bao gồm dữ liệu test"),
):
    """
    Lấy danh sách các ký ức giao dịch (Reflexion Post-Mortem Memories) gần đây nhất.
    """
    try:
        memories = await reflexion_service.get_recent_memories(
            limit=limit,
            outcome=outcome,
            mistake_category=mistake_category,
            include_test=include_test,
        )
        return memories
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch memories: {exc}")


@router.get("/search", response_model=list[SearchMemoryResponse])
async def search_memories(
    query: str = Query(..., min_length=2, description="Nội dung tìm kiếm ngữ nghĩa"),
    outcome: str | None = Query(None, description="Lọc theo kết quả"),
    mistake_category: str | None = Query(None, description="Lọc theo phân loại lỗi"),
    top_k: int = Query(3, ge=1, le=10, description="Số lượng kết quả hàng đầu"),
    include_test: bool = Query(False, description="Bao gồm dữ liệu test"),
):
    """
    Tìm kiếm các bài học trong quá khứ có bối cảnh hoặc lỗi tương tự bằng Semantic Search (pgvector).
    """
    try:
        results = await reflexion_service.search_similar_lessons(
            query=query,
            outcome=outcome,
            mistake_category=mistake_category,
            top_k=top_k,
            include_test=include_test,
        )
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search memories failed: {exc}")


@router.post("/analyze/{order_id}", response_model=MemoryItemResponse)
async def analyze_order(order_id: int):
    """
    Kích hoạt phân tích thủ công bài học rút ra (Post-Mortem Reflexion) cho một lệnh đã đóng trong DB.
    """
    async with session_factory() as session:
        order = await session.get(SimulatedOrder, order_id)
        if not order:
            raise HTTPException(status_code=404, detail=f"Order #{order_id} not found")

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

        memory = await reflexion_service.analyze_closed_order(order_data, session=session)
        return {
            "id": memory.id,
            "order_id": memory.order_id,
            "outcome": memory.outcome,
            "market_context_summary": memory.market_context_summary,
            "root_cause": memory.root_cause,
            "lesson_learned": memory.lesson_learned,
            "mistake_category": memory.mistake_category,
            "rule_to_add": memory.rule_to_add,
            "is_test": memory.is_test,
            "created_at": memory.created_at.isoformat() if memory.created_at else None,
        }


@router.get("/stats", response_model=ReflexionStatsResponse)
async def get_reflexion_stats(
    include_test: bool = Query(False, description="Bao gồm dữ liệu test"),
):
    """
    Lấy thống kê tổng hợp của Reflexion Engine (Win/Loss, tỷ lệ các nhóm lỗi phổ biến).
    """
    try:
        stats = await reflexion_service.get_reflexion_stats(include_test=include_test)
        return stats
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch reflexion stats: {exc}")
