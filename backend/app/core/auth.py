"""
app/core/auth.py
─────────────────
FastAPI JWT authentication dependency using Supabase-issued tokens.

Usage
─────
    from app.core.auth import get_current_user

    @router.get("/protected")
    async def my_route(user_id: str = Depends(get_current_user)):
        ...

SSE endpoints (cannot use headers) use decode_token() directly with the
token supplied via a GET query parameter:

    @router.get("/events")
    async def events(token: str = Query(...)):
        user_id = decode_token(token)

How Supabase JWTs work
──────────────────────
Supabase can issue either HS256-signed JWTs (legacy, uses SUPABASE_JWT_SECRET)
or ES256-signed JWTs (modern, uses asymmetric keys).  This module supports
both: it first tries JWKS-based validation (works for ES256 and HS256), then
falls back to the shared secret if SUPABASE_URL is not configured.

Environment variables
──────────────────────
    SUPABASE_URL=https://<ref>.supabase.co          (required for JWKS path)
    SUPABASE_JWT_SECRET=<your-secret>               (fallback / legacy)
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

import jwt  # PyJWT
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# Claim that holds the user UUID
_SUB_CLAIM = "sub"

# JWKS URL for Supabase asymmetric key validation (ES256 / RS256)
_JWKS_URL_TEMPLATE = "{supabase_url}/auth/v1/.well-known/jwks.json"


@lru_cache(maxsize=1)
def _get_jwks_client() -> Optional[PyJWKClient]:
    """Return a cached PyJWKClient if SUPABASE_URL is configured, else None."""
    url = settings.SUPABASE_URL
    if not url:
        return None
    jwks_url = _JWKS_URL_TEMPLATE.format(supabase_url=url.rstrip("/"))
    logger.info("[Auth] Using JWKS endpoint: %s", jwks_url)
    return PyJWKClient(jwks_url, cache_keys=True)


def decode_token(token: str) -> str:
    """
    Decode and verify a Supabase JWT.

    Validation strategy (in order):
    1. JWKS-based validation  — works for ES256 / RS256 (modern Supabase projects).
    2. HS256 shared-secret    — fallback for legacy projects using SUPABASE_JWT_SECRET.

    Returns the user_id (UUID string from the `sub` claim).
    Raises HTTP 401 on any validation failure.

    This is also called directly by SSE endpoints that receive the token
    via a query parameter instead of an Authorization header.
    """
    # ── Path 1: JWKS (asymmetric, works for ES256 / RS256) ────────────────────
    jwks_client = _get_jwks_client()
    if jwks_client is not None:
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256", "HS256"],
                options={"verify_aud": False},
            )
            user_id: Optional[str] = payload.get(_SUB_CLAIM)
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token is missing the 'sub' claim.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return user_id
        except HTTPException:
            raise
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as exc:
            logger.warning("[Auth] JWKS validation failed, trying HS256 fallback: %s", exc)
            # Fall through to HS256 path below

    # ── Path 2: HS256 shared-secret (legacy) ──────────────────────────────────
    secret = settings.SUPABASE_JWT_SECRET
    if not secret:
        logger.error(
            "[Auth] Neither JWKS validation succeeded nor SUPABASE_JWT_SECRET is set."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured on this server.",
        )
    try:
        payload = jwt.decode(
            token,
            key=secret,
            algorithms=["HS256"],
            options={"verify_signature": True, "verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        logger.warning("[Auth] JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get(_SUB_CLAIM)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing the 'sub' claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> str:
    """
    FastAPI dependency — extract and validate the Bearer JWT from the
    Authorization header.

    Returns the authenticated user_id (UUID string).
    Raises HTTP 401 if the header is absent or the token is invalid.

    Inject as:
        user_id: str = Depends(get_current_user)
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing or empty.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return decode_token(credentials.credentials)
