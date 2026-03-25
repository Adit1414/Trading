"""
app/main.py
────────────
FastAPI application factory for Algo Kaisen backend.

Startup sequence:
  1. Create async DB engine (if DATABASE_URL is set).
  2. Run Alembic migrations to HEAD (ensures schema is current).
  3. Seed STRATEGIES table (idempotent upsert).
  4. Register all routes.

Shutdown:
  Dispose of the async DB engine pool.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
            "Algo Kaisen — Automated Trading Strategy Development and Deployment Platform.\n\n"
            "**Active modules:**\n"
            "- Module 2: Backtesting Engine (`/api/v1/backtest/*`)\n"
            "- DB layer: Backtests, Strategies (`/api/v1/backtests/*`, `/api/v1/strategies/*`)\n\n"
            "Modules 1 (Auth), 3 (Streamer), 4 (Bots), 5 (Orders) are integrated incrementally."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Rate limiting ─────────────────────────────────────────────────────────
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

    # ── Module 1 JWT Auth stub ────────────────────────────────────────────────
    # Once Supabase Auth is wired, uncomment and complete this middleware.
    # It must set request.state.user_id from the decoded JWT.
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

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    @app.on_event("startup")
    async def _on_startup() -> None:
        logger.info("%s v%s starting — DEBUG=%s", settings.APP_NAME, settings.APP_VERSION, settings.DEBUG)

        if settings.db_enabled:
            await _init_db()
        else:
            logger.warning(
                "DATABASE_URL not set — DB persistence disabled. "
                "Backtest results will NOT be saved. Set DATABASE_URL in .env to enable."
            )

    @app.on_event("shutdown")
    async def _on_shutdown() -> None:
        from app.db.session import close_engine
        await close_engine()
        logger.info("%s shut down.", settings.APP_NAME)

    # ── Health ────────────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health() -> dict:
        return {
            "status": "ok",
            "version": settings.APP_VERSION,
            "db_enabled": settings.db_enabled,
        }

    return app


async def _init_db() -> None:
    """
    Run Alembic migrations to HEAD, then seed the STRATEGIES table.
    Both operations are idempotent and safe to run on every startup.
    """
    from alembic import command
    from alembic.config import Config

    # ── Migrations ────────────────────────────────────────────────────────────
    try:
        alembic_cfg = Config("alembic.ini")
        # Run synchronously via the sync engine (Alembic doesn't use asyncpg)
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine as sync_create_engine

        sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2", 1) \
            if settings.DATABASE_URL else None

        if sync_url:
            sync_engine = sync_create_engine(sync_url)
            with sync_engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current = context.get_current_revision()
            sync_engine.dispose()
            logger.info("DB current migration revision: %s", current)

        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied.")
    except Exception as exc:
        logger.error("Alembic migration failed: %s", exc, exc_info=True)
        logger.warning(
            "Continuing without running migrations. "
            "Ensure the schema is up to date manually."
        )

    # ── Seed strategies ───────────────────────────────────────────────────────
    try:
        from app.db.seed import seed_strategies
        from app.db.session import get_db
        async with get_db() as session:
            if session is not None:
                await seed_strategies(session)
    except Exception as exc:
        logger.error("Strategy seeding failed: %s", exc, exc_info=True)


app = create_app()