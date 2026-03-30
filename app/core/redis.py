"""Async Redis connection pool and helper functions."""
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

# ── Connection pool ───────────────────────────────────────────────────────────
_pool: aioredis.Redis | None = None


def get_redis_pool() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _pool


# ── Helper functions ──────────────────────────────────────────────────────────
async def redis_get(key: str) -> str | None:
    r = get_redis_pool()
    return await r.get(key)


async def redis_set(key: str, value: str, expire: int | None = None) -> None:
    r = get_redis_pool()
    if expire:
        await r.setex(key, expire, value)
    else:
        await r.set(key, value)


async def redis_delete(key: str) -> None:
    r = get_redis_pool()
    await r.delete(key)


async def redis_exists(key: str) -> bool:
    r = get_redis_pool()
    return bool(await r.exists(key))


async def redis_increment(key: str, expire: int | None = None) -> int:
    r = get_redis_pool()
    val = await r.incr(key)
    if expire and val == 1:  # set TTL only on first increment
        await r.expire(key, expire)
    return val


async def check_redis_connection() -> bool:
    """Health check: verify Redis is reachable."""
    try:
        r = get_redis_pool()
        await r.ping()
        return True
    except Exception:
        return False
