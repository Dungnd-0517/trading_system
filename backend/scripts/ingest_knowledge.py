import asyncio
import logging
import sys
from pathlib import Path

# Thêm đường dẫn backend vào sys.path nếu chạy trực tiếp
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from ai_engine.rag_service import rag_service
from core.database import close_database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingest_knowledge")


async def main():
    logger.info("Starting Knowledge Ingestion Pipeline for TradingAgents RAG...")
    results = await rag_service.ingest_all_knowledge()

    total_chunks = sum(results.values())
    logger.info("Ingestion complete. Details:")
    for filename, count in results.items():
        logger.info("  - %s: %d chunks", filename, count)
    logger.info("Total chunks ingested: %d", total_chunks)

    stats = await rag_service.get_stats()
    logger.info("Current Vector DB stats: %s", stats)

    await close_database()


if __name__ == "__main__":
    asyncio.run(main())
