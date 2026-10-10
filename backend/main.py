from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_engine.rag_service import rag_service
from ai_engine.reflexion_service import reflexion_worker
from ai_engine.sentiment import backfill_news_sentiment
from ai_engine.signal_worker import signal_worker
from ai_engine.strategy_governor import governor_worker
from api.v1 import router as api_router
from core.config import settings
from core.database import close_database, ping_database, session_factory
from core.migrations import run_migrations
from core.redis_client import close_redis, ping_redis
from data_ingestion.candle_healer import candle_integrity_worker
from data_ingestion.chart_streamer import ChartStreamer
from data_ingestion.news_worker import NewsCollector
from simulation.paper_worker import paper_worker


@asynccontextmanager
async def lifespan(_: FastAPI):
    await run_migrations()
    try:
        async with session_factory() as session:
            await backfill_news_sentiment(session, batch_size=2000)
    except Exception:
        pass
    try:
        stats = await rag_service.get_stats()
        if stats.get("total_chunks", 0) == 0:
            await rag_service.ingest_all_knowledge()
    except Exception:
        pass
    news_task = asyncio.create_task(NewsCollector().run(), name="news-collector")
    chart_task = asyncio.create_task(ChartStreamer().run(), name="chart-streamer")
    paper_task = asyncio.create_task(paper_worker.run(), name="paper-worker")
    signal_task = asyncio.create_task(signal_worker.run(), name="signal-worker")
    integrity_task = asyncio.create_task(candle_integrity_worker.run(), name="candle-integrity-worker")
    reflexion_task = asyncio.create_task(reflexion_worker.run(), name="reflexion-worker")
    governor_task = asyncio.create_task(governor_worker.run(), name="governor-worker")
    try:
        yield
    finally:
        for task in (news_task, chart_task, paper_task, signal_task, integrity_task, reflexion_task, governor_task):
            task.cancel()
        candle_integrity_worker.stop()
        paper_worker.stop()
        signal_worker.stop()
        reflexion_worker.stop()
        governor_worker.stop()
        await asyncio.gather(
            news_task,
            chart_task,
            paper_task,
            signal_task,
            integrity_task,
            reflexion_task,
            governor_task,
            return_exceptions=True,
        )
        await close_redis()
        await close_database()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health() -> dict[str, object]:
    database_ok = await ping_database()
    redis_ok = await ping_redis()
    return {
        "status": "ok" if database_ok and redis_ok else "degraded",
        "services": {"postgres": database_ok, "redis": redis_ok},
    }