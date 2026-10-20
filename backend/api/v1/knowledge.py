from typing import Any
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ai_engine.knowledge_ingestor import (
    KnowledgeIngestionResult,
    StandardizedStrategyDTO,
    knowledge_ingestion_engine,
)
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


class IngestUrlRequest(BaseModel):
    url: str = Field(..., description="Đường dẫn URL bài viết/tài liệu kỹ thuật giao dịch")
    custom_title: str | None = Field(default=None, description="Tiêu đề tùy chỉnh cho tài liệu")
    school_of_thought: str | None = Field(
        default=None,
        description="Trường phái: WYCKOFF, SMC, ICT, CMT, PRICE_ACTION, RISK_MANAGEMENT (hoặc để trống để Agent tự động nhận diện)",
    )
    is_test: bool = Field(default=False, description="Đánh dấu dữ liệu kiểm thử D18")


class IngestMarkdownRequest(BaseModel):
    title: str = Field(..., min_length=3, description="Tiêu đề tài liệu/phương pháp")
    content: str = Field(..., min_length=20, description="Nội dung Markdown chi tiết của phương pháp")
    school_of_thought: str | None = Field(
        default=None,
        description="Trường phái kỹ thuật (WYCKOFF, SMC, ICT, CMT, PRICE_ACTION, RISK...)",
    )
    source_name: str | None = Field(default=None, description="Tên định danh nguồn tài liệu")
    is_test: bool = Field(default=False, description="Đánh dấu dữ liệu kiểm thử D18")


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


# ============================================================================
# PHASE 03 - SPRINT 03: KNOWLEDGE INGESTION & STANDARDIZED STRATEGIES API
# ============================================================================


@router.post("/upload-file", response_model=KnowledgeIngestionResult)
async def upload_knowledge_file(
    file: UploadFile = File(..., description="File PDF (.pdf), Markdown (.md), hoặc Text (.txt)"),
    school_of_thought: str | None = Form(None, description="Trường phái kỹ thuật chỉ định (tùy chọn)"),
    custom_title: str | None = Form(None, description="Tiêu đề tài liệu tùy chỉnh (tùy chọn)"),
    is_test: bool = Form(False, description="Dữ liệu kiểm thử D18"),
):
    """
    Tải lên file tài liệu (PDF, Markdown, Text):
    - Agent [VECTOR] tự động trích xuất nội dung văn bản.
    - Phân tích và phân loại trường phái học thuật (SMC, Wyckoff, ICT, CMT, Price Action).
    - Tạo cấu trúc giao dịch tiêu chuẩn (Standardized Trading Strategy) cho phương pháp.
    - Xuất file hệ thống (.json và .md) trong thư mục knowledge_base/standardized_strategies/.
    - Vector hóa 1536 chiều và lưu trữ vào PostgreSQL pgvector.
    """
    filename = file.filename or "unknown_document"
    ext = filename.split(".")[-1].lower() if "." in filename else ""

    if ext not in ("pdf", "md", "markdown", "txt"):
        raise HTTPException(
            status_code=400,
            detail="Định dạng file không được hỗ trợ. Vui lòng tải lên file .pdf, .md, hoặc .txt.",
        )

    try:
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(status_code=400, detail="File tải lên rỗng.")

        if ext == "pdf":
            raw_text = knowledge_ingestion_engine.extract_text_from_pdf(content_bytes)
            source_type = "PDF"
        else:
            raw_text = content_bytes.decode("utf-8", errors="replace")
            source_type = "MARKDOWN"

        doc_title = custom_title or filename.rsplit(".", 1)[0].replace("_", " ").title()

        res = await knowledge_ingestion_engine.ingest_document(
            raw_text=raw_text,
            source_name=filename,
            source_type=source_type,
            custom_title=doc_title,
            forced_school=school_of_thought,
            is_test=is_test,
        )
        return res
    except HTTPException:
        raise
    except Exception as exc:
        logger_msg = f"Lỗi khi xử lý tải lên file: {exc}"
        raise HTTPException(status_code=500, detail=logger_msg)


@router.post("/ingest-url", response_model=KnowledgeIngestionResult)
async def ingest_knowledge_url(payload: IngestUrlRequest):
    """
    Nạp tri thức từ liên kết tài liệu hoặc bài báo phân tích (Link tài liệu):
    - Tải và cào văn bản HTML sạch sẽ bằng HTTPX.
    - Agent [VECTOR] đọc và phân loại trường phái.
    - Tự động sinh cấu trúc giao dịch chuẩn hóa và lưu file hệ thống (.json, .md) + CSDL.
    """
    if not payload.url.startswith("http://") and not payload.url.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail="Đường dẫn URL không hợp lệ (bắt buộc bắt đầu bằng http:// hoặc https://).",
        )

    try:
        doc_title, raw_text = await knowledge_ingestion_engine.fetch_url_content(payload.url)
        final_title = payload.custom_title or doc_title

        res = await knowledge_ingestion_engine.ingest_document(
            raw_text=raw_text,
            source_name=payload.url,
            source_type="URL",
            source_url=payload.url,
            custom_title=final_title,
            forced_school=payload.school_of_thought,
            is_test=payload.is_test,
        )
        return res
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi khi nạp tài liệu từ URL: {exc}")


@router.post("/ingest-markdown", response_model=KnowledgeIngestionResult)
async def ingest_knowledge_markdown(payload: IngestMarkdownRequest):
    """
    Soạn thảo hoặc dán trực tiếp tài liệu Markdown vào hệ thống:
    - Agent [VECTOR] phân tích nội dung, chia chunks và vector hóa pgvector.
    - Tự động cấu trúc hóa chiến lược giao dịch chuẩn mực và lưu file hệ thống.
    """
    try:
        source_name = payload.source_name or f"{payload.title}.md"
        res = await knowledge_ingestion_engine.ingest_document(
            raw_text=payload.content,
            source_name=source_name,
            source_type="MARKDOWN",
            custom_title=payload.title,
            forced_school=payload.school_of_thought,
            is_test=payload.is_test,
        )
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi khi nạp Markdown: {exc}")


@router.get("/standardized-strategies", response_model=list[StandardizedStrategyDTO])
async def list_standardized_strategies(
    school: str | None = Query(None, description="Lọc theo trường phái: WYCKOFF, SMC, ICT, CMT, PRICE_ACTION..."),
    include_test: bool = Query(False, description="Bao gồm dữ liệu test"),
):
    """
    Lấy danh sách toàn bộ các cấu trúc giao dịch tiêu chuẩn hóa (Standardized Trading Strategies)
    đã được Agent [VECTOR] tổng hợp và lưu trữ trong hệ thống.
    """
    try:
        strategies = await knowledge_ingestion_engine.list_standardized_strategies(
            school=school, include_test=include_test
        )
        return strategies
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi truy vấn danh sách chiến lược tiêu chuẩn: {exc}"
        )


@router.get("/standardized-strategies/{slug}", response_model=StandardizedStrategyDTO)
async def get_standardized_strategy_detail(slug: str):
    """
    Lấy thông tin chi tiết một cấu trúc giao dịch tiêu chuẩn kèm toàn bộ nội dung file JSON và Markdown hệ thống.
    """
    try:
        strategy = await knowledge_ingestion_engine.get_strategy_detail(slug)
        if not strategy:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy cấu trúc giao dịch tiêu chuẩn với mã định danh '{slug}'.",
            )
        return strategy
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tải chi tiết chiến lược: {exc}")


@router.get("/standardized-strategies/{slug}/markdown")
async def get_strategy_markdown_raw(slug: str):
    """
    Tải hoặc xem trực tiếp file Markdown của cấu trúc giao dịch tiêu chuẩn.
    """
    strategy = await knowledge_ingestion_engine.get_strategy_detail(slug)
    if not strategy or not strategy.markdown_content:
        raise HTTPException(status_code=404, detail="File Markdown không tồn tại.")
    return PlainTextResponse(content=strategy.markdown_content, media_type="text/markdown")


@router.get("/documents", response_model=list[dict[str, Any]])
async def list_ingested_documents():
    """
    Lấy danh sách toàn bộ các nguồn tài liệu (PDF, URL, Markdown) đã được nạp vào hệ thống RAG Vector DB.
    """
    try:
        docs = await knowledge_ingestion_engine.list_ingested_documents()
        return docs
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách tài liệu: {exc}")


@router.post("/seed-strategies")
async def seed_baseline_strategies():
    """
    Khởi tạo sẵn 5 cấu trúc giao dịch tiêu chuẩn nền tảng (SMC, Wyckoff, ICT, CMT, Price Action)
    nếu chưa tồn tại trong hệ thống.
    """
    try:
        count = await knowledge_ingestion_engine.seed_baseline_standardized_strategies()
        return {"status": "success", "seeded_count": count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi khi seed chiến lược tiêu chuẩn: {exc}")
