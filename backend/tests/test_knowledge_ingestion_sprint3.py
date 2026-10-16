from decimal import Decimal
import io
import json
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfWriter

from ai_engine.knowledge_ingestor import knowledge_ingestion_engine
from core.database import session_factory
from core.models import StandardizedTradingStrategy, TradingKnowledge
from main import app


def _create_minimal_pdf_bytes(title: str, body_text: str) -> bytes:
    """Tạo một file PDF hợp lệ trong bộ nhớ bằng pypdf để kiểm thử"""
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    # pypdf có thể thêm metadata
    writer.add_metadata({"/Title": title, "/Subject": body_text})
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


@pytest.mark.anyio
async def test_pdf_extraction_fallback_or_parse():
    """Kiểm tra trích xuất nội dung từ byte stream PDF"""
    pdf_bytes = _create_minimal_pdf_bytes(
        "Wyckoff Spring Strategy",
        "Accumulation Phase C Spring sweeps liquidity and tests with low volume.",
    )
    # Ngay cả khi trang trống chưa có font glyphs, hàm không được crash
    text = knowledge_ingestion_engine.extract_text_from_pdf(pdf_bytes)
    assert isinstance(text, str)


@pytest.mark.anyio
async def test_markdown_ingestion_and_standardized_strategy_generation():
    """
    Kiểm tra Agent [VECTOR] nạp tài liệu Markdown, phân loại Wyckoff,
    sinh Cấu trúc Giao dịch Tiêu chuẩn hóa (.json & .md) và lưu CSDL.
    """
    sample_md = """# Chiến lược Wyckoff Phase C Spring Accumulation

## 1. Nguyên lý Tích lũy
Mô hình tích lũy Wyckoff Phase C xuất hiện khi giá tạo cú nhúng Spring xuyên thủng Preliminary Support.
Smart Money hấp thụ toàn bộ khối lượng bán tháo (Effort vs Result) và tạo cú bật mạnh mẽ.

## 2. Quy tắc Vào Lệnh & Chốt Lời
Chờ nến Test of Spring với volume cạn kiệt, sau đó xuất hiện nến SOS vượt qua Creek.
Vào lệnh tại LPS, Stop Loss đặt cách đáy Spring 1.5x ATR, Take Profit tại đỉnh Range.
"""

    result = await knowledge_ingestion_engine.ingest_document(
        raw_text=sample_md,
        source_name="test_wyckoff_spring.md",
        source_type="MARKDOWN",
        custom_title="TEST Wyckoff Phase C Spring",
        forced_school="WYCKOFF",
        is_test=True,
    )

    assert result.status == "success"
    assert result.source_type == "MARKDOWN"
    assert "WYCKOFF" in result.detected_school
    assert result.chunks_created >= 1
    assert result.standardized_strategy is not None

    strat = result.standardized_strategy
    assert "test_" in strat.slug
    assert strat.school_of_thought == "WYCKOFF"
    assert len(strat.setup_checklist) >= 4
    assert "1.5x ATR" in strat.stop_loss_rules or "Stop Loss" in strat.stop_loss_rules

    # Kiểm tra file hệ thống đã được tạo
    json_file = Path(result.file_saved_paths[0])
    md_file = Path(result.file_saved_paths[1])
    assert json_file.exists()
    assert md_file.exists()

    # Đọc và xác thực nội dung file JSON
    json_data = json.loads(json_file.read_text(encoding="utf-8"))
    assert json_data["slug"] == strat.slug
    assert json_data["school_of_thought"] == "WYCKOFF"

    # Kiểm tra trong PostgreSQL
    async with session_factory() as session:
        from sqlalchemy import select

        stmt = select(StandardizedTradingStrategy).where(
            StandardizedTradingStrategy.slug == strat.slug
        )
        db_strat = (await session.execute(stmt)).scalar_one_or_none()
        assert db_strat is not None
        assert db_strat.is_test is True
        assert db_strat.school_of_thought == "WYCKOFF"

        # Kiểm tra chunks trong trading_knowledge
        tk_stmt = select(TradingKnowledge).where(
            TradingKnowledge.source_file == "test_wyckoff_spring.md"
        )
        chunks = (await session.execute(tk_stmt)).scalars().all()
        assert len(chunks) >= 1
        for ch in chunks:
            assert ch.is_test is True
            assert ch.school_of_thought == "WYCKOFF"
            assert ch.embedding is not None

    # Dọn dẹp files test
    if json_file.exists():
        json_file.unlink()
    if md_file.exists():
        md_file.unlink()


@pytest.mark.anyio
async def test_api_upload_markdown_file():
    """Kiểm tra API upload file Markdown (/api/v1/knowledge/upload-file)"""
    sample_content = b"""# TEST SMC Liquidity Sweeps
## Order Block & Fair Value Gap
Ch\xc3\xa1y theo d\xc3\xb2ng ti\xe1\xbb\x81n th\xc3\xb4ng minh SMC. Qu\xc3\xa9t thanh kho\xe1\xba\xa3n Low v\xc3\xa0 tap POI Discount.
CHoCH tr\xc3\xaan M15 l\xc3\xa0 t\xc3\xadn hi\xe1\xbb\x87u k\xc3\xadch ho\xe1\xba\xa1t l\xe1\xbb\x87nh Mua.
"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("test_smc_upload.md", sample_content, "text/markdown")}
        data = {
            "school_of_thought": "SMC",
            "custom_title": "TEST SMC Liquidity Ingestion",
            "is_test": "true",
        }
        resp = await client.post("/api/v1/knowledge/upload-file", files=files, data=data)
        assert resp.status_code == 200
        res_json = resp.json()
        assert res_json["status"] == "success"
        assert res_json["source_type"] == "MARKDOWN"
        assert res_json["detected_school"] == "SMC"
        assert len(res_json["file_saved_paths"]) == 2

        # Dọn dẹp files sinh ra
        for p in res_json["file_saved_paths"]:
            path = Path(p)
            if path.exists():
                path.unlink()


@pytest.mark.anyio
async def test_api_ingest_markdown_endpoint():
    """Kiểm tra API soạn thảo trực tiếp (/api/v1/knowledge/ingest-markdown)"""
    payload = {
        "title": "TEST ICT Silver Bullet Framework",
        "content": (
            "# TEST ICT Silver Bullet\n\n"
            "## London Kill Zone Setup\n"
            "Chờ cú Judas Swing trong khung giờ 14:00-17:00 ICT. "
            "Khi xuất hiện displacement tạo FVG, vào lệnh tại Consequent Encroachment 50% "
            "với R:R tối thiểu 1:2.0."
        ),
        "school_of_thought": "ICT",
        "is_test": True,
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/knowledge/ingest-markdown", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "ICT" in data["detected_school"]
        assert data["standardized_strategy"]["timeframe_focus"] == "M15"

        # Dọn dẹp files
        for p in data["file_saved_paths"]:
            path = Path(p)
            if path.exists():
                path.unlink()


@pytest.mark.anyio
async def test_api_list_and_get_standardized_strategies():
    """Kiểm tra API liệt kê và xem chi tiết cấu trúc chiến lược tiêu chuẩn"""
    # 1. Tạo 1 chiến lược test
    await knowledge_ingestion_engine.ingest_document(
        raw_text="# TEST CMT Polarity Framework\nRetest kháng cự cũ thành hỗ trợ mới.",
        source_name="test_cmt_doc.md",
        source_type="MARKDOWN",
        custom_title="TEST CMT Polarity Retest",
        forced_school="CMT",
        is_test=True,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Lấy danh sách bao gồm dữ liệu test
        list_resp = await client.get("/api/v1/knowledge/standardized-strategies?include_test=true")
        assert list_resp.status_code == 200
        strategies = list_resp.json()
        assert isinstance(strategies, list)
        test_strats = [s for s in strategies if "test_" in s["slug"]]
        assert len(test_strats) >= 1

        target_slug = test_strats[0]["slug"]

        # Lấy chi tiết
        detail_resp = await client.get(f"/api/v1/knowledge/standardized-strategies/{target_slug}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["slug"] == target_slug
        assert detail["school_of_thought"] == "CMT"
        assert "setup_checklist" in detail

        # Lấy raw markdown
        md_resp = await client.get(f"/api/v1/knowledge/standardized-strategies/{target_slug}/markdown")
        assert md_resp.status_code == 200
        assert "CẤU TRÚC GIAO DỊCH TIÊU CHUẨN" in md_resp.text

        # Dọn dẹp files
        json_f = knowledge_ingestion_engine.strategies_dir / f"{target_slug}.json"
        md_f = knowledge_ingestion_engine.strategies_dir / f"{target_slug}.md"
        if json_f.exists():
            json_f.unlink()
        if md_f.exists():
            md_f.unlink()


@pytest.mark.anyio
async def test_api_list_documents():
    """Kiểm tra API lấy danh sách các tài liệu đã nạp (/api/v1/knowledge/documents)"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/knowledge/documents")
        assert resp.status_code == 200
        docs = resp.json()
        assert isinstance(docs, list)
