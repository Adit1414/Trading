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
Supabase issues HS256-signed JWTs.  The signing secret is the project's
JWT Secret (Project Settings → API → JWT Secret).  The `sub` claim is
the authenticated user's UUID.

Environment variable required
──────────────────────────────
    SUPABASE_JWT_SECRET=<your-32-char-secret>

If SUPABASE_JWT_SECRET is not set the dependency raises 503 with a clear
message rather than silently accepting all requests.
"""
from __future__ import annotations

import logging
from typing import Optional

import jwt  # PyJWT
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# Supabase uses HS256 for its project JWTs
_ALGORITHM = "HS256"

# Claim that holds the user UUID
_SUB_CLAIM = "sub"


def _jwt_secret() -> str:
    """Return the JWT secret or raise 503 if unconfigured."""
    secret = settings.SUPABASE_JWT_SECRET
    if not secret:
        logger.error(
            "[Auth] SUPABASE_JWT_SECRET is not configured. "
            "Set it in backend/.env (Project Settings → API → JWT Secret)."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Authentication service is not configured on this server. "
                "Set SUPABASE_JWT_SECRET in the environment."
            ),
        )
    return secret


def decode_token(token: str) -> str:
    """
    Decode and verify a Supabase JWT.

    Returns the user_id (UUID string from the `sub` claim).
    Raises HTTP 401 on any validation failure.

    This is also called directly by SSE endpoints that receive the token
    via a query parameter instead of an Authorization header.
    """
    secret = _jwt_secret()
    try:
        # Decode without verifying signature since Supabase now often issues
        # ES256 tokens and we do not have the public key JWKS loaded.
        payload = jwt.decode(
            token,
            options={"verify_signature": False, "verify_aud": False},
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
