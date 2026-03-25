"""
app/crud/strategies.py
───────────────────────
CRUD (read-only) operations for the STRATEGIES table.

The strategies table is seeded at startup and never modified by users.
We only need read operations here.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StrategyModel

logger = logging.getLogger(__name__)


async def get_strategy_by_type_code(
    session:   AsyncSession,
    type_code: str,
) -> Optional[StrategyModel]:
    """
    Fetch a strategy row by its type_code (e.g. 'EMA_CROSSOVER').
    Returns None if not found.
    """
    result = await session.execute(
        select(StrategyModel).where(StrategyModel.type_code == type_code.upper())
    )
    return result.scalar_one_or_none()


async def get_strategy_by_id(
    session:     AsyncSession,
    strategy_id: str,
) -> Optional[StrategyModel]:
    """Fetch a strategy row by UUID primary key."""
    result = await session.execute(
        select(StrategyModel).where(StrategyModel.id == strategy_id)
    )
    return result.scalar_one_or_none()


async def list_strategies(session: AsyncSession) -> List[StrategyModel]:
    """Return all strategy rows ordered by name."""
    result = await session.execute(
        select(StrategyModel).order_by(StrategyModel.name)
    )
    return list(result.scalars().all())