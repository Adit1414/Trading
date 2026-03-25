"""
app/db/session.py
─────────────────
Async SQLAlchemy engine and session factory.

Usage:
    async with get_db() as session:
        result = await session.execute(select(BacktestModel))

The engine is created lazily on first use and shared for the lifetime
of the process.  When DATABASE_URL is not configured the engine is None
and all DB calls silently no-op (graceful degradation for local dev).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _build_engine() -> Optional[AsyncEngine]:
    """Create the async engine once. Returns None if DATABASE_URL is unset."""
    if not settings.DATABASE_URL:
        logger.warning(
            "DATABASE_URL is not configured — database persistence is disabled. "
            "Set DATABASE_URL in .env to enable it."
        )
        return None
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,          # detects stale connections
        pool_size=5,
        max_overflow=10,
    )


def get_engine() -> Optional[AsyncEngine]:
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> Optional[async_sessionmaker[AsyncSession]]:
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        if engine is None:
            return None
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


@asynccontextmanager
async def get_db() -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    Async context manager that yields a database session.
    Yields None if DATABASE_URL is not configured (graceful no-op).
    Commits on clean exit, rolls back on exception.
    """
    factory = get_session_factory()
    if factory is None:
        yield None
        return

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_engine() -> None:
    """Dispose of the engine — called on application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed.")
