"""
app/db/cache.py
---------------
Redis-backed cache with a graceful no-op fallback.
If REDIS_URL is not configured, all cache calls are silent no-ops —
the app still works, just without caching.
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_redis: aioredis.Redis | None = None


async def init_cache() -> None:
    global _redis
    settings = get_settings()
    if not settings.REDIS_URL:
        log.info("cache_disabled", reason="REDIS_URL not set")
        return
    try:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        await _redis.ping()
        log.info("cache_connected", url=settings.REDIS_URL)
    except Exception as e:
        log.warning("cache_connect_failed", error=str(e))
        _redis = None


async def close_cache() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


async def cache_get(key: str) -> Any | None:
    if not _redis:
        return None
    try:
        val = await _redis.get(key)
        return json.loads(val) if val else None
    except Exception as e:
        log.warning("cache_get_error", key=key, error=str(e))
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """TTL in seconds. Default 5 minutes."""
    if not _redis:
        return
    try:
        await _redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        log.warning("cache_set_error", key=key, error=str(e))


async def cache_delete(key: str) -> None:
    if not _redis:
        return
    try:
        await _redis.delete(key)
    except Exception as e:
        log.warning("cache_delete_error", key=key, error=str(e))


async def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern (e.g. 'products:*')."""
    if not _redis:
        return
    try:
        keys = await _redis.keys(pattern)
        if keys:
            await _redis.delete(*keys)
    except Exception as e:
        log.warning("cache_delete_pattern_error", pattern=pattern, error=str(e))
