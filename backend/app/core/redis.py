"""
app/core/redis.py
──────────────────
Async Redis client singleton using redis-py (aioredis-compatible API).

Import pattern:
    from app.core.redis import get_redis

Returns None when REDIS_URL is not configured — all callers must handle this
gracefully so the application degrades cleanly in dev without Redis.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False
    logger.warning(
        "redis package not installed — idempotency caching is disabled. "
        "Run: pip install redis"
    )

_client: Optional["aioredis.Redis"] = None  # type: ignore[name-defined]


def _build_client() -> Optional["aioredis.Redis"]:  # type: ignore[name-defined]
    """Create the async Redis client once. Returns None if REDIS_URL is unset."""
    if not _REDIS_AVAILABLE:
        return None

    from app.core.config import settings

    if not settings.REDIS_URL:
        logger.info(
            "REDIS_URL is not configured — idempotency caching disabled. "
            "Set REDIS_URL in .env to enable it."
        )
        return None

    client = aioredis.from_url(  # type: ignore[union-attr]
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    logger.info("Redis client initialised successfully (URL redacted)")
    return client


def get_redis() -> Optional["aioredis.Redis"]:  # type: ignore[name-defined]
    """Return the shared async Redis client (lazy-init, None if unconfigured)."""
    global _client
    if _client is None:
        _client = _build_client()
    return _client


async def close_redis() -> None:
    """Dispose the Redis connection — call on application shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("Redis connection closed.")
