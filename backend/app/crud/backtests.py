"""
app/crud/backtests.py
─────────────────────
CRUD operations for the BACKTESTS table.

Schema contract (per DatabaseSchema.svg):
  id              uuid PK
  user_id         uuid FK → USERS (nullable until auth is wired)
  strategy_id     uuid FK → STRATEGIES
  symbol          varchar
  timeframe       varchar  (e.g. "1d", "1h")
  parameters      jsonb    (full execution config)
  metrics         jsonb    (scalar performance values)
  result_file_url varchar  (Supabase Storage pointer, nullable)
  created_at      timestamp
"""
from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BacktestModel

logger = logging.getLogger(__name__)


async def create_backtest(
    session:         AsyncSession,
    *,
    id:              Optional[str] = None,
    user_id:         Optional[str],
    strategy_id:     str,
    symbol:          str,
    timeframe:       str,
    parameters:      dict,
    metrics:         dict,
    result_file_url: Optional[str] = None,
) -> BacktestModel:
    """
    Insert a new row into BACKTESTS and return the ORM instance.

    Args:
        session:         Active async DB session.
        user_id:         UUID of the owning user (nullable — pre-auth).
        strategy_id:     UUID of the STRATEGIES row for this run.
        symbol:          Trading pair, e.g. "BTCUSDT".
        timeframe:       Binance interval string, e.g. "1d".
        parameters:      Full BacktestParameters dict (execution config).
        metrics:         BacktestStatistics dict (scalar performance values).
        result_file_url: Supabase Storage URL for the heavy equity curve.

    Returns:
        The newly created BacktestModel row.
    """
    kwargs = {
        "user_id": user_id,
        "strategy_id": strategy_id,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "parameters": parameters,
        "metrics": metrics,
        "result_file_url": result_file_url,
    }
    if id is not None:
        kwargs["id"] = id
        
    row = BacktestModel(**kwargs)
    session.add(row)
    await session.flush()   # populate row.id + row.created_at without committing
    await session.refresh(row)
    logger.debug("Backtest persisted: id=%s symbol=%s tf=%s", row.id, symbol, timeframe)
    return row


async def get_backtest(
    session: AsyncSession,
    backtest_id: str,
) -> Optional[BacktestModel]:
    """Fetch a single backtest by primary key. Returns None if not found."""
    result = await session.execute(
        select(BacktestModel).where(BacktestModel.id == backtest_id)
    )
    return result.scalar_one_or_none()


async def list_backtests_for_user(
    session: AsyncSession,
    user_id: str,
    limit:  int = 50,
    offset: int = 0,
) -> List[BacktestModel]:
    """
    Return backtests owned by *user_id*, newest first.

    Used by the Backtest Results listing page.
    """
    result = await session.execute(
        select(BacktestModel)
        .where(BacktestModel.user_id == user_id)
        .order_by(BacktestModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def list_all_backtests(
    session: AsyncSession,
    limit:  int = 50,
    offset: int = 0,
) -> List[BacktestModel]:
    """
    Return all backtests, newest first.
    Used when user_id is not yet available (pre-auth phase).
    """
    result = await session.execute(
        select(BacktestModel)
        .order_by(BacktestModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def delete_backtest(
    session:     AsyncSession,
    backtest_id: str,
    user_id:     Optional[str] = None,
) -> bool:
    """
    Delete a backtest row.  If user_id is provided it is used as an
    extra guard (prevents deleting another user's backtest).
    Returns True if a row was deleted, False if not found.
    """
    row = await get_backtest(session, backtest_id)
    if row is None:
        return False
    if user_id is not None and row.user_id != user_id:
        return False
    await session.delete(row)
    return True
