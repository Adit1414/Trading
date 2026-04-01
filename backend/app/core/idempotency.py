"""
app/core/idempotency.py
────────────────────────
FastAPI dependency that enforces idempotency on mutating endpoints.

Usage
─────
Add `idempotency: IdempotencyResult = Depends(idempotency_dep)` to any route
that the frontend will retry with the same Idempotency-Key header.

Protocol
────────
1. Client sends:  POST /bots   Idempotency-Key: <uuid-v4>
2. First request  → key absent in Redis → execute route → store response → return 201
3. Retry          → key present in Redis → return cached 200 response immediately
   (status is intentionally 200 on replay so the client can distinguish first vs retry)

Redis key format:  idempotency:<uuid>
TTL:               settings.IDEMPOTENCY_TTL_SECONDS  (default 24 h)

Stored value (JSON):
{
  "status_code": 201,
  "body": { ...BotResponse... }
}

Graceful degradation
────────────────────
If Redis is not configured (REDIS_URL unset) the dependency silently no-ops and
lets the route execute normally — functionally identical to no idempotency guard.
This allows running in dev without a Redis instance.

Validation-first guarantee
───────────────────────────
Because this is a FastAPI *dependency* (not ASGI middleware), Pydantic body
validation runs before this code touches Redis.  A 422 from a bad payload will
never pollute the idempotency cache.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from fastapi import Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

# Only valid UUID v4 strings are accepted as idempotency keys
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_KEY_PREFIX = "idempotency:"


def _redis_key(idem_key: str) -> str:
    return f"{_KEY_PREFIX}{idem_key}"


@dataclass
class IdempotencyContext:
    """
    Passed into the route via `Depends(idempotency_dep)`.

    The route calls `await ctx.store(response_body, status_code)` just before
    returning so the idempotency layer can cache it.

    If `cached_response` is not None the dependency already returned early —
    the route body will NOT run (FastAPI short-circuits via the raised exception).
    """
    key: Optional[str] = None              # raw UUID string, None when Redis unavailable
    cached_response: Optional[JSONResponse] = None
    _stored: bool = field(default=False, init=False, repr=False)

    async def store(self, body: dict, status_code: int = 200) -> None:
        """
        Persist `body` in Redis under this idempotency key.
        Safe to call even when Redis is unavailable (silently no-ops).
        """
        if not self.key:
            return
        redis = get_redis()
        if redis is None:
            return
        try:
            payload = json.dumps({"status_code": status_code, "body": body})
            await redis.set(
                _redis_key(self.key),
                payload,
                ex=settings.IDEMPOTENCY_TTL_SECONDS,
            )
            logger.debug("Idempotency key stored: %s (TTL %ds)", self.key, settings.IDEMPOTENCY_TTL_SECONDS)
            self._stored = True
        except Exception as exc:
            # Never fail the request because of a Redis write error
            logger.warning("Failed to store idempotency key %s: %s", self.key, exc)


async def idempotency_dep(
    request: Request,
    idempotency_key: Optional[str] = Header(
        default=None,
        alias="Idempotency-Key",
        description="UUID v4 — if present, enables idempotent request handling.",
    ),
) -> IdempotencyContext:
    """
    FastAPI dependency.  Wire into any route that needs idempotency:

        @router.post("")
        async def create_bot(
            body: BotCreate,
            ctx: IdempotencyContext = Depends(idempotency_dep),
        ):
            ...
            await ctx.store(response.model_dump(mode="json"), status_code=201)
            return response
    """
    # No header supplied → pass through with a no-op context
    if not idempotency_key:
        return IdempotencyContext()

    # Validate key format
    if not _UUID_RE.match(idempotency_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Idempotency-Key must be a valid UUID v4, "
                f"got: '{idempotency_key}'"
            ),
        )

    redis = get_redis()

    # Redis unavailable → degrade gracefully, still track the key in context
    if redis is None:
        logger.debug("Redis unavailable — skipping idempotency lookup for key %s", idempotency_key)
        return IdempotencyContext(key=idempotency_key)

    # Cache hit → return the stored response immediately (short-circuit the route)
    try:
        cached = await redis.get(_redis_key(idempotency_key))
    except Exception as exc:
        logger.warning("Redis GET failed for key %s: %s — continuing without cache", idempotency_key, exc)
        cached = None

    if cached is not None:
        try:
            payload = json.loads(cached)
            cached_status = payload.get("status_code", 200)
            cached_body   = payload.get("body", {})
            logger.info("Idempotency cache HIT for key %s → returning cached %d", idempotency_key, cached_status)
            # Raise as an HTTP exception so FastAPI stops route execution.
            # We use 200 on replay to signal "already processed" to the client
            # while preserving the original body.
            raise _CachedResponse(
                JSONResponse(
                    content=cached_body,
                    status_code=200,
                    headers={"X-Idempotency-Replayed": "true"},
                )
            )
        except _CachedResponse:
            raise
        except Exception as exc:
            logger.warning("Failed to deserialise cached idempotency payload: %s", exc)

    # Cache miss → let the route run normally
    logger.debug("Idempotency cache MISS for key %s", idempotency_key)
    return IdempotencyContext(key=idempotency_key)


# ─── Internal sentinel exception ─────────────────────────────────────────────

class _CachedResponse(Exception):
    """
    Internal sentinel raised to short-circuit FastAPI's route execution
    and return a pre-built JSONResponse from the cache.

    Caught by the custom exception handler registered in main.py.
    """
    def __init__(self, response: JSONResponse) -> None:
        self.response = response
        super().__init__("idempotency cache hit")
