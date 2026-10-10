from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ai_engine.rag_service import rag_service

router = APIRouter()


class SearchResultItem(BaseModel):
    id: int
    title: str
    category: str
    content: str
    metadata: dict[str, Any]
    similarity: float
    distance: float


class KnowledgeStatsResponse(BaseModel):
    total_chunks: int
    categories: dict[str, int]
    knowledge_dir: str


class ReindexResponse(BaseModel):
    status: str
    files_indexed: dict[str, int]
    total_chunks: int


@router.get("/search", response_model=list[SearchResultItem])
async def search_knowledge(
    query: str = Query(..., min_length=2, description="Nội dung cần tìm kiếm ngữ nghĩa"),
    category: str | None = Query(None, description="Lọc theo danh mục: SMC, PRICE_ACTION, MACRO, POST_MORTEM"),
    top_k: int = Query(3, ge=1, le=10, description="Số lượng kết quả hàng đầu cần lấy"),
):
    """
    Truy vấn tri thức giao dịch RAG bằng Semantic Search qua pgvector (Cosine Distance).
    """
    try:
        results = await rag_service.search_knowledge(
            query=query,
            category=category,
            top_k=top_k,
        )
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}")


@router.get("/stats", response_model=KnowledgeStatsResponse)
async def get_knowledge_stats():
    """
    Lấy thống kê số lượng tài liệu và phân bổ danh mục trong RAG Knowledge Base.
    """
    try:
        stats = await rag_service.get_stats()
        return stats
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {exc}")


@router.post("/reindex", response_model=ReindexResponse)
async def reindex_knowledge():
    """
    Nạp lại toàn bộ tài liệu Markdown từ knowledge_base/ vào PostgreSQL pgvector.
    """
    try:
        indexed = await rag_service.ingest_all_knowledge()
        total = sum(indexed.values())
        return {
            "status": "success",
            "files_indexed": indexed,
            "total_chunks": total,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {exc}")
