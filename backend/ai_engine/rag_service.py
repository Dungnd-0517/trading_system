from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.embeddings import embedding_service
from core.database import session_factory
from core.models import TradingKnowledge

logger = logging.getLogger(__name__)

_DEFAULT_KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge_base"

# Mapping từ tên file sang category chuẩn
_CATEGORY_MAPPING = {
    "smc_trading_rules": "SMC",
    "price_action_patterns": "PRICE_ACTION",
    "macro_risk_playbook": "MACRO",
    "post_mortem_playbook": "POST_MORTEM",
}


@dataclass
class KnowledgeChunk:
    title: str
    category: str
    content: str
    metadata: dict[str, Any]


class RAGService:
    """
    Dịch vụ RAG (Retrieval-Augmented Generation) cho Trading Knowledge:
    - Phân tách và nạp tài liệu chiến lược từ thư mục knowledge_base/.
    - Vectorize và lưu trữ vào PostgreSQL qua pgvector.
    - Truy vấn tri thức theo ngữ nghĩa (Semantic Search với Cosine Similarity).
    """

    def __init__(self, knowledge_dir: Path | None = None):
        self.knowledge_dir = knowledge_dir or _DEFAULT_KNOWLEDGE_DIR

    def parse_markdown_to_chunks(self, file_path: Path) -> list[KnowledgeChunk]:
        """
        Phân tích cú pháp tài liệu Markdown và chia thành các chunk logic theo tiêu đề (H2/H3).
        """
        text = file_path.read_text(encoding="utf-8")
        stem = file_path.stem.lower()
        category = _CATEGORY_MAPPING.get(stem, "GENERAL")

        # Lấy tiêu đề chính H1
        h1_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
        doc_title = h1_match.group(1).strip() if h1_match else file_path.name

        # Tách theo các heading H2 và H3 (## ... hoặc ### ...)
        sections = re.split(r"\n(?=#{2,3}\s+)", text)
        chunks: list[KnowledgeChunk] = []

        for section in sections:
            section_clean = section.strip()
            if not section_clean:
                continue

            heading_match = re.match(r"^(#{2,3})\s+(.+)$", section_clean, flags=re.MULTILINE)
            if heading_match:
                section_title = heading_match.group(2).strip()
                chunk_content = f"{doc_title} - {section_title}\n\n{section_clean}"
            else:
                # Kiểm tra nếu phần mở đầu có nội dung thực tế ngoài tiêu đề H1
                body_lines = [
                    line for line in section_clean.splitlines()
                    if not line.strip().startswith("# ")
                ]
                body_text = "\n".join(body_lines).strip()
                if not body_text:
                    continue
                section_title = "Overview"
                chunk_content = f"{doc_title} - Overview\n\n{body_text}"

            chunks.append(
                KnowledgeChunk(
                    title=f"{doc_title}: {section_title}",
                    category=category,
                    content=chunk_content,
                    metadata={
                        "source_file": file_path.name,
                        "section": section_title,
                        "category": category,
                        "length": len(chunk_content),
                    },
                )
            )

        return chunks

    async def ingest_file(self, file_path: Path, session: AsyncSession) -> int:
        """Nạp một file Markdown vào bảng trading_knowledge (ghi đè các chunk cũ của file đó)"""
        chunks = self.parse_markdown_to_chunks(file_path)
        if not chunks:
            return 0

        # Xóa các chunk cũ của file này để tránh nhân bản dữ liệu
        await session.execute(
            delete(TradingKnowledge).where(
                TradingKnowledge.metadata_["source_file"].as_string() == file_path.name
            )
        )

        # Trích xuất embeddings theo lô
        texts = [chunk.content for chunk in chunks]
        vectors = await embedding_service.embed_batch(texts)

        db_records: list[TradingKnowledge] = []
        for chunk, vec in zip(chunks, vectors):
            db_records.append(
                TradingKnowledge(
                    title=chunk.title,
                    category=chunk.category,
                    content=chunk.content,
                    metadata_=chunk.metadata,
                    embedding=vec,
                )
            )

        session.add_all(db_records)
        await session.commit()
        logger.info("Ingested %d chunks from %s", len(db_records), file_path.name)
        return len(db_records)

    async def ingest_all_knowledge(
        self, dir_path: Path | None = None
    ) -> dict[str, int]:
        """Nạp toàn bộ tài liệu Markdown trong thư mục knowledge_base/ vào Vector DB"""
        target_dir = dir_path or self.knowledge_dir
        if not target_dir.exists():
            logger.warning("Knowledge directory does not exist: %s", target_dir)
            return {}

        results: dict[str, int] = {}
        md_files = sorted(target_dir.glob("*.md"))

        async with session_factory() as session:
            for md_file in md_files:
                count = await self.ingest_file(md_file, session)
                results[md_file.name] = count

        return results

    async def search_knowledge(
        self,
        query: str,
        category: str | None = None,
        top_k: int = 3,
        similarity_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Tìm kiếm tri thức tương đồng ngữ nghĩa bằng Cosine Distance qua pgvector.
        Độ tương đồng: similarity = 1.0 - cosine_distance.
        """
        query_vec = await embedding_service.embed_text(query)

        async with session_factory() as session:
            distance_col = TradingKnowledge.embedding.cosine_distance(query_vec).label(
                "distance"
            )
            stmt = select(TradingKnowledge, distance_col)

            if category:
                stmt = stmt.where(TradingKnowledge.category == category)

            # Lọc bỏ các chunk test nếu có
            stmt = stmt.where(TradingKnowledge.category != "TEST")
            stmt = stmt.order_by(distance_col).limit(top_k)

            res = await session.execute(stmt)
            matches: list[dict[str, Any]] = []

            for row in res.all():
                knowledge_obj: TradingKnowledge = row[0]
                dist: float = float(row[1]) if row[1] is not None else 1.0
                similarity: float = max(0.0, min(1.0, 1.0 - dist))

                if similarity >= similarity_threshold:
                    matches.append(
                        {
                            "id": knowledge_obj.id,
                            "title": knowledge_obj.title,
                            "category": knowledge_obj.category,
                            "content": knowledge_obj.content,
                            "metadata": knowledge_obj.metadata_,
                            "similarity": round(similarity, 4),
                            "distance": round(dist, 4),
                        }
                    )

            return matches

    async def get_stats(self) -> dict[str, Any]:
        """Lấy thống kê số lượng tài liệu và phân bổ danh mục trong RAG Vector DB"""
        async with session_factory() as session:
            total_stmt = select(func.count(TradingKnowledge.id)).where(
                TradingKnowledge.category != "TEST"
            )
            total = (await session.execute(total_stmt)).scalar_one()

            cat_stmt = (
                select(TradingKnowledge.category, func.count(TradingKnowledge.id))
                .where(TradingKnowledge.category != "TEST")
                .group_by(TradingKnowledge.category)
            )
            cat_rows = (await session.execute(cat_stmt)).all()
            category_counts = {row[0]: row[1] for row in cat_rows}

            return {
                "total_chunks": total,
                "categories": category_counts,
                "knowledge_dir": str(self.knowledge_dir),
            }


rag_service = RAGService()
