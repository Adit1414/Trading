"""
app/api/v1/routes/backtests_db.py
──────────────────────────────────
DB-backed endpoints for BACKTESTS table.

  GET  /api/v1/backtests          List saved backtest runs
  GET  /api/v1/backtests/{id}     Get one backtest by ID
  DELETE /api/v1/backtests/{id}   Delete a backtest
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.crud.backtests import (
    delete_backtest,
    get_backtest,
    list_all_backtests,
    list_backtests_for_user,
)
from app.core.auth import get_current_user
from app.db.session import get_db
from app.modules.backtest.engine import get_chart_path
from app.schemas.db import BacktestDB, BacktestListItemDB

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtests", tags=["Backtests (DB)"])


@router.get(
    "",
    response_model=List[BacktestListItemDB],
    summary="List saved backtest runs",
)
async def list_backtests(
    limit:   int = 50,
    offset:  int = 0,
    user_id: str = Depends(get_current_user),
) -> List[BacktestListItemDB]:
    async with get_db() as session:
        if session is None:
            return []
        rows = await list_backtests_for_user(session, user_id, limit=limit, offset=offset)
        return [BacktestListItemDB.from_orm_row(r) for r in rows]


@router.get(
    "/{backtest_id}",
    response_model=BacktestDB,
    summary="Get a single backtest by ID",
)
async def get_one_backtest(
    backtest_id: str,
    user_id: str = Depends(get_current_user),
) -> BacktestDB:
    async with get_db() as session:
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is not configured.",
            )
        row = await get_backtest(session, backtest_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest '{backtest_id}' not found.",
            )
        # Ensure user owns this backtest (allow NULL user_id for pre-auth legacy data if necessary, or enforce it)
        if row.user_id is not None and row.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this backtest.",
            )
            
        db_obj = BacktestDB.model_validate(row)

        # Prefer chart_html stored in the DB; fall back to disk for older rows
        if row.chart_html:
            db_obj.chart_html = row.chart_html
        else:
            try:
                chart_path = get_chart_path(backtest_id)
                if chart_path:
                    with open(chart_path, "r", encoding="utf-8") as f:
                        db_obj.chart_html = f.read()
            except Exception as e:
                logger.warning("Failed to load chart HTML for backtest %s: %s", backtest_id, e)

        return db_obj


@router.delete(
    "/{backtest_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a backtest",
)
async def delete_one_backtest(
    backtest_id: str,
    user_id: str = Depends(get_current_user),
) -> None:
    async with get_db() as session:
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is not configured.",
            )
        deleted = await delete_backtest(session, backtest_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest '{backtest_id}' not found.",
        )
        
    # Attempt to delete the chart file if it exists
    try:
        chart_path_str = get_chart_path(backtest_id)
        if chart_path_str:
            import os
            os.remove(chart_path_str)
    except Exception as e:
        logger.warning("Failed to delete chart HTML for backtest %s: %s", backtest_id, e)