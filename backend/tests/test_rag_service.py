import math
import httpx
import pytest

from ai_engine.embeddings import embedding_service
from ai_engine.rag_service import rag_service
from main import app


@pytest.mark.anyio
async def test_embeddings_service_dimension_and_determinism():
    """Kiểm tra tính chuẩn xác của EmbeddingService: chiều 1536, L2 norm = 1.0, tính tất định"""
    text1 = "SMC Order Block and Fair Value Gap strategy for Gold"
    text2 = "Fair Value Gap imbalance entries on M15 timeframe"
    text3 = "US Federal Reserve interest rate policy and inflation"

    vec1 = await embedding_service.embed_text(text1)
    vec1_again = await embedding_service.embed_text(text1)
    vec2 = await embedding_service.embed_text(text2)
    vec3 = await embedding_service.embed_text(text3)

    # 1. Chiều vector bắt buộc là 1536
    assert len(vec1) == 1536
    assert len(vec2) == 1536
    assert len(vec3) == 1536

    # 2. Vector có độ dài chuẩn hóa xấp xỉ 1.0 (Unit Vector)
    norm = math.sqrt(sum(x * x for x in vec1))
    assert pytest.approx(norm, rel=1e-3) == 1.0

    # 3. Tính tất định (Deterministic)
    assert vec1 == vec1_again

    # 4. Tính tương quan ngữ nghĩa (Dot product của unit vectors chính là Cosine Similarity)
    sim_1_2 = sum(a * b for a, b in zip(vec1, vec2))
    sim_1_3 = sum(a * b for a, b in zip(vec1, vec3))
    # text1 và text2 cùng chủ đề SMC/FVG nên độ tương đồng phải cao hơn text3 (kinh tế vĩ mô)
    assert sim_1_2 > sim_1_3

    # 5. Batch embedding
    batch_vecs = await embedding_service.embed_batch([text1, text2])
    assert len(batch_vecs) == 2
    assert len(batch_vecs[0]) == 1536
    assert len(batch_vecs[1]) == 1536


@pytest.mark.anyio
async def test_markdown_parser_and_chunking():
    """Kiểm tra parser markdown tách đúng các chunk theo heading H2 và gán đúng metadata"""
    smc_file = rag_service.knowledge_dir / "smc_trading_rules.md"
    assert smc_file.exists()

    chunks = rag_service.parse_markdown_to_chunks(smc_file)
    assert len(chunks) >= 5

    titles = [c.title for c in chunks]
    assert any("Dealing Range and Equilibrium" in t for t in titles)
    assert any("Order Block" in t for t in titles)
    assert any("Fair Value Gap" in t for t in titles)

    for chunk in chunks:
        assert chunk.category == "SMC"
        assert chunk.metadata["source_file"] == "smc_trading_rules.md"
        assert len(chunk.content) > 50


@pytest.mark.anyio
async def test_knowledge_ingestion_and_semantic_retrieval():
    """Kiểm tra quy trình nạp tri thức vào PostgreSQL và semantic search bằng pgvector"""
    # 1. Nạp toàn bộ tài liệu vào DB
    indexed = await rag_service.ingest_all_knowledge()
    assert "smc_trading_rules.md" in indexed
    assert "macro_risk_playbook.md" in indexed
    assert sum(indexed.values()) >= 10

    # 2. Kiểm tra stats
    stats = await rag_service.get_stats()
    assert stats["total_chunks"] >= 10
    assert "SMC" in stats["categories"]
    assert "MACRO" in stats["categories"]
    assert "PRICE_ACTION" in stats["categories"]

    # 3. Tìm kiếm ngữ nghĩa: Truy vấn về Fair Value Gap
    fvg_results = await rag_service.search_knowledge(
        query="How to trade Fair Value Gap FVG imbalance?",
        top_k=2,
    )
    assert len(fvg_results) >= 1
    top_fvg = fvg_results[0]
    assert "Fair Value Gap" in top_fvg["title"] or top_fvg["category"] == "SMC"
    assert top_fvg["similarity"] > 0.05

    # 4. Tìm kiếm ngữ nghĩa: Truy vấn về quản lý tin tức đỏ CPI/NFP
    news_results = await rag_service.search_knowledge(
        query="What is the circuit breaker buffer around high-impact CPI release?",
        category="MACRO",
        top_k=2,
    )
    assert len(news_results) >= 1
    top_news = news_results[0]
    assert top_news["category"] == "MACRO"
    assert "Circuit Breaker" in top_news["title"] or "Macro" in top_news["title"]

    # 5. Lọc theo category
    filtered_results = await rag_service.search_knowledge(
        query="candlestick pattern",
        category="PRICE_ACTION",
        top_k=3,
    )
    for res in filtered_results:
        assert res["category"] == "PRICE_ACTION"


@pytest.mark.anyio
async def test_knowledge_api_endpoints():
    """Kiểm tra các REST API endpoints của RAG Knowledge"""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. GET /api/v1/knowledge/stats
        res_stats = await client.get("/api/v1/knowledge/stats")
        assert res_stats.status_code == 200
        stats_data = res_stats.json()
        assert stats_data["total_chunks"] >= 10
        assert "SMC" in stats_data["categories"]

        # 2. GET /api/v1/knowledge/search
        res_search = await client.get(
            "/api/v1/knowledge/search",
            params={"query": "Order Block mitigation and market structure", "top_k": 2},
        )
        assert res_search.status_code == 200
        search_data = res_search.json()
        assert len(search_data) == 2
        assert "title" in search_data[0]
        assert "similarity" in search_data[0]
        assert "metadata" in search_data[0]

        # 3. POST /api/v1/knowledge/reindex
        res_reindex = await client.post("/api/v1/knowledge/reindex")
        assert res_reindex.status_code == 200
        reindex_data = res_reindex.json()
        assert reindex_data["status"] == "success"
        assert reindex_data["total_chunks"] >= 10
