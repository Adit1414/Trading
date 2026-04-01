"""
app/main.py
────────────
FastAPI application factory for Algo Kaisen backend.

Architecture (HLD §3):
  Module 1 – API Gateway & User Management  → JWT middleware stub
  Module 2 – Strategy & Backtesting Engine  → /api/v1/backtest/*  ✓ (implemented)
  Module 3 – Market Data Multiplexer        → WebSocket supervisor (future)
  Module 4 – Bot Execution & State Manager  → /api/v1/bots/*       (future)
  Module 5 – Order Execution & Security     → /api/v1/orders/*      (future)
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.rate_limiter import limiter

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Algo Kaisen – Automated Trading Strategy Development and Deployment Platform.\n\n"
            "**Currently active module:** Module 2 – Backtesting Engine.\n"
            "Modules 1, 3, 4 and 5 will be integrated incrementally."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Rate limiting (slowapi) ───────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Module 1 JWT Auth Middleware stub ─────────────────────────────────────
    # Replace this with actual Supabase JWT validation once Module 1 is built.
    # The middleware should set `request.state.user_id` from the decoded JWT.
    # Example skeleton:
    #
    # @app.middleware("http")
    # async def jwt_auth_middleware(request: Request, call_next):
    #     token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    #     try:
    #         payload = supabase.auth.get_user(token)
    #         request.state.user_id = payload.user.id
    #     except Exception:
    #         return JSONResponse({"detail": "Unauthorised"}, status_code=401)
    #     return await call_next(request)

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # ── Startup / shutdown lifecycle ──────────────────────────────────────────
    @app.on_event("startup")
    async def _on_startup() -> None:
        logger.info(
            "%s v%s starting up — DEBUG=%s",
            settings.APP_NAME, settings.APP_VERSION, settings.DEBUG,
        )
        logger.info("CORS origins: %s", settings.CORS_ORIGINS)
        logger.info(
            "Backtest rate limit: %d req / %ds",
            settings.BACKTEST_RATE_LIMIT,
            settings.BACKTEST_RATE_LIMIT_WINDOW,
        )

    @app.on_event("shutdown")
    async def _on_shutdown() -> None:
        logger.info("%s shutting down.", settings.APP_NAME)

    # ── Global health endpoint ────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=True)
    async def health() -> dict:
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


# Export the app instance for Uvicorn:  uvicorn app.main:app
app = create_app()
