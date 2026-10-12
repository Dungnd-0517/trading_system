from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.technical_agent import (
    KnowledgeClassificationResult,
    KnowledgeSubmissionRequest,
    RetrievedKnowledgeChunk,
    TechnicalAnalysisReport,
    technical_rag_agent,
)
from core.database import get_db

router = APIRouter()


class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=5, description="Văn bản cần phân loại trường phái và gắn nhãn")


class ClassifyResponse(BaseModel):
    status: str
    result: KnowledgeClassificationResult


class IngestResponse(BaseModel):
    status: str
    id: int
    title: str
    school_of_thought: str
    category: str


class SchoolsStatsResponse(BaseModel):
    schools: list[dict[str, Any]]
    total_chunks: int
    timestamp: str


@router.get("/analysis", response_model=TechnicalAnalysisReport)
async def get_technical_analysis(
    symbol: str = Query("XAUUSD", description="Cặp tài sản giao dịch"),
    timeframe: str = Query("M15", description="Khung thời gian phân tích"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy báo cáo phân tích kỹ thuật hợp lưu đa trường phái (Wyckoff, ICT, CMT, Inducement/Traps, SMC)
    trên khung thời gian M15 kèm các trích đoạn tri thức RAG tương ứng.
    """
    try:
        report = await technical_rag_agent.generate_technical_analysis(
            session=db, symbol=symbol, timeframe=timeframe
        )
        return report
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi thực hiện phân tích kỹ thuật: {exc}"
        )


@router.post("/knowledge/submit", response_model=IngestResponse)
async def submit_knowledge(
    submission: KnowledgeSubmissionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Trader hoặc hệ thống nạp tài liệu/giáo trình/ghi chú tri thức mới vào Vector DB:
    Tự động trích xuất vector 1536 chiều và lưu trữ siêu dữ liệu trường phái.
    """
    try:
        new_id = await technical_rag_agent.ingest_knowledge(submission=submission, session=db)
        return IngestResponse(
            status="success",
            id=new_id,
            title=submission.title,
            school_of_thought=submission.school_of_thought,
            category=submission.category,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi nạp tri thức vào hệ thống: {exc}"
        )


@router.post("/knowledge/classify", response_model=ClassifyResponse)
async def classify_raw_text(payload: ClassifyRequest):
    """
    Tự động phân loại trường phái (`school_of_thought`), danh mục (`category`),
    và nhãn (`tags`) cho một đoạn văn bản ghi chú hoặc tài liệu chiến lược thô.
    """
    try:
        result = technical_rag_agent.classify_text(payload.text)
        return ClassifyResponse(status="success", result=result)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi phân loại văn bản: {exc}"
        )


@router.get("/knowledge/schools", response_model=SchoolsStatsResponse)
async def get_schools_statistics(db: AsyncSession = Depends(get_db)):
    """
    Lấy danh sách các trường phái tri thức đang lưu trữ cùng số lượng chunks
    và tỷ lệ đã kiểm chứng trong cơ sở dữ liệu vector.
    """
    try:
        stats = await technical_rag_agent.get_school_statistics(db)
        return stats
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi truy vấn thống kê trường phái: {exc}"
        )


@router.get("/knowledge/search", response_model=list[RetrievedKnowledgeChunk])
async def search_multi_school_knowledge(
    query: str = Query(..., min_length=2, description="Nội dung truy vấn ngữ nghĩa"),
    school_of_thought: str | None = Query(None, description="Lọc theo trường phái: WYCKOFF, ICT, CMT, INDUCEMENT_TRAPS, SMC..."),
    category: str | None = Query(None, description="Lọc theo danh mục"),
    top_k: int = Query(3, ge=1, le=10, description="Số lượng kết quả hàng đầu cần lấy"),
    include_test: bool = Query(False, description="Bao gồm dữ liệu test"),
    db: AsyncSession = Depends(get_db),
):
    """
    Tìm kiếm tri thức đa trường phái bằng Cosine Similarity qua pgvector.
    Hỗ trợ lọc theo trường phái cụ thể hoặc tìm kiếm chéo toàn bộ hệ thống tri thức.
    """
    try:
        chunks = await technical_rag_agent.search_multi_school(
            query=query,
            school_of_thought=school_of_thought,
            category=category,
            top_k=top_k,
            include_test=include_test,
            session=db,
        )
        return chunks
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi tìm kiếm tri thức đa trường phái: {exc}"
        )


@router.post("/knowledge/seed")
async def seed_multi_school_baseline(db: AsyncSession = Depends(get_db)):
    """
    Khởi tạo bộ tri thức nền tảng 5 trường phái (Wyckoff, ICT, Inducement/Traps, CMT, SMC)
    nếu chưa tồn tại trong cơ sở dữ liệu.
    """
    try:
        seeded = await technical_rag_agent.seed_multi_school_knowledge(db)
        return {"status": "success", "seeded": seeded}
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi seed tri thức nền tảng: {exc}"
        )
