from redis.asyncio import Redis

from core.config import settings

client = Redis.from_url(settings.redis_url, decode_responses=True)


async def ping_redis() -> bool:
    try:
        return bool(await client.ping())
    except Exception:
        return False


async def close_redis() -> None:
    await client.aclose()