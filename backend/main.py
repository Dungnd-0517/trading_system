from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1 import router as api_router
from core.config import settings
from core.database import close_database, ping_database
from core.redis_client import close_redis, ping_redis


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
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