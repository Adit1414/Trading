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

from fastapi import APIRouter, HTTPException, Query, status

from app.crud.backtests import (
    delete_backtest,
    get_backtest,
    list_all_backtests,
    list_backtests_for_user,
)
from app.db.session import get_db
from app.schemas.db import BacktestDB, BacktestListItemDB

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtests", tags=["Backtests (DB)"])


@router.get(
    "",
    response_model=List[BacktestListItemDB],
    summary="List saved backtest runs",
)
async def list_backtests(
    user_id: Optional[str] = Query(default=None, description="Filter by user UUID"),
    limit:   int           = Query(default=50, ge=1, le=200),
    offset:  int           = Query(default=0,  ge=0),
) -> List[BacktestListItemDB]:
    async with get_db() as session:
        if session is None:
            return []
        if user_id:
            rows = await list_backtests_for_user(session, user_id, limit, offset)
        else:
            rows = await list_all_backtests(session, limit, offset)
        return [BacktestListItemDB.from_orm_row(r) for r in rows]


@router.get(
    "/{backtest_id}",
    response_model=BacktestDB,
    summary="Get a single backtest by ID",
)
async def get_one_backtest(backtest_id: str) -> BacktestDB:
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
            
        db_obj = BacktestDB.model_validate(row)
        
        # Attempt to load chart_html from disk
        try:
            from pathlib import Path
            chart_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "charts" / f"{backtest_id}.html"
            if chart_path.exists():
                db_obj.chart_html = chart_path.read_text(encoding="utf-8")
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
    user_id: Optional[str] = Query(default=None),
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
        from pathlib import Path
        chart_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "charts" / f"{backtest_id}.html"
        if chart_path.exists():
            chart_path.unlink()
    except Exception as e:
        logger.warning("Failed to delete chart HTML for backtest %s: %s", backtest_id, e)