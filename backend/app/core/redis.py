"""Redis client and a sliding-window rate limiter."""

from __future__ import annotations

import time

import redis.asyncio as aioredis

from app.core.config import settings

_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            str(settings.REDIS_URL), encoding="utf-8", decode_responses=True
        )
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def check_rate_limit(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Sliding-window counter over a sorted set.

    Returns (allowed, retry_after_seconds). A fixed-window counter would let a
    caller burst 2x the limit across a window boundary; for AI endpoints that
    each cost real money, that matters.
    """
    redis = get_redis()
    now = time.time()
    cutoff = now - window_seconds
    redis_key = f"ratelimit:{key}"

    async with redis.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(redis_key, 0, cutoff)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {f"{now}:{id(object())}": now})
        pipe.expire(redis_key, window_seconds + 1)
        results = await pipe.execute()

    count_before_add = int(results[1])
    if count_before_add >= limit:
        # Over limit: undo our own insertion so a caller hammering the endpoint
        # does not keep pushing their own reset time forward.
        oldest = await redis.zrange(redis_key, 0, 0, withscores=True)
        await redis.zpopmax(redis_key)
        retry_after = window_seconds
        if oldest:
            retry_after = max(1, int(oldest[0][1] + window_seconds - now))
        return False, retry_after

    return True, 0
