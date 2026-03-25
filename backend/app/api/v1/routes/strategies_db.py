"""
app/api/v1/routes/strategies_db.py
────────────────────────────────────
DB-backed endpoints for the STRATEGIES table.

  GET /api/v1/strategies          List all seeded strategies (with full parameter_schema)
  GET /api/v1/strategies/{id}     Get one strategy by UUID

The parameter_schema field is the JSON Schema for this strategy's config
parameters — used by the frontend to build dynamic configuration forms.
"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status

from app.crud.strategies import get_strategy_by_id, list_strategies
from app.db.session import get_db
from app.schemas.db import StrategyDB

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/strategies", tags=["Strategies (DB)"])


@router.get(
    "",
    response_model=List[StrategyDB],
    summary="List all available strategies from the database",
    description=(
        "Returns the seeded strategy catalogue. Each entry includes "
        "`parameter_schema` (JSON Schema) which the frontend can use to "
        "dynamically build configuration forms without hardcoding field definitions."
    ),
)
async def list_strategies_endpoint() -> List[StrategyDB]:
    async with get_db() as session:
        if session is None:
            # Fallback: return in-memory strategy list when DB is unavailable
            from app.modules.backtest.strategies import list_strategies as _list
            return [
                StrategyDB(
                    id="00000000-0000-0000-0000-000000000000",
                    name=s["display_name"],
                    type_code=s["id"],
                    description=s["description"],
                    parameter_schema=s["config_schema"],
                )
                for s in _list()
            ]
        rows = await list_strategies(session)
        return [StrategyDB.model_validate(r) for r in rows]


@router.get(
    "/{strategy_id}",
    response_model=StrategyDB,
    summary="Get a strategy by UUID",
)
async def get_strategy_endpoint(strategy_id: str) -> StrategyDB:
    async with get_db() as session:
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is not configured.",
            )
        row = await get_strategy_by_id(session, strategy_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy '{strategy_id}' not found.",
            )
        return StrategyDB.model_validate(row)