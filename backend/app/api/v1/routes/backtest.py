"""
app/api/v1/routes/backtest.py
───────────────────────────────
Backtest API endpoints — HLD §5.2

  POST /api/v1/backtest/run        Rate-limited: 10 req/min (per HLD)
  GET  /api/v1/backtest/strategies List all available strategies
  GET  /api/v1/backtest/health     Cache stats + engine health

Module 1 integration stub:
  Once the JWT Auth Middleware (Module 1) is wired into app/main.py,
  `user_id` will be populated from `request.state.user_id`.
  All endpoints are designed to accept an optional user_id so the
  transition requires zero breaking changes here.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, status

from app.core.rate_limiter import BACKTEST_LIMIT, limiter
from app.modules.backtest.data_cache import cache_stats
from app.modules.backtest.engine import BacktestError, run_backtest
from app.modules.backtest.strategies import list_strategies
from app.schemas.backtest import BacktestRunRequest, BacktestRunResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["Backtesting Engine"])


@router.post(
    "/run",
    response_model=BacktestRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Run a backtest simulation",
    description=(
        "Accepts strategy parameters and returns a full historical equity curve, "
        "trade log, and performance statistics.  "
        "**Rate-limited to 10 requests per minute** due to compute weight (HLD §5.2)."
    ),
)
@limiter.limit(BACKTEST_LIMIT)
async def run_backtest_endpoint(
    request: Request,         # required by slowapi for IP extraction
    body: BacktestRunRequest,
) -> BacktestRunResponse:
    """
    Execute a deterministic backtest and return the full report.

    Module 1 integration note:
        Replace the stub below with:
            body.user_id = request.state.user_id
        once the JWT middleware is active.
    """
    # ── Module 1 stub: inject user identity ───────────────────────────────────
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    body.user_id = user_id

    try:
        result = await run_backtest(body)
    except BacktestError as exc:
        logger.warning("Backtest failed for user=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in backtest engine for user=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        ) from exc

    return result


@router.get(
    "/strategies",
    summary="List available strategies",
    description="Returns all registered strategy IDs, display names, and minimum bar requirements.",
)
async def get_strategies() -> List[dict]:
    """Return the strategy registry metadata."""
    return list_strategies()


@router.get(
    "/health",
    summary="Engine health and cache stats",
    description="Returns the current LRU cache utilisation for monitoring / admin purposes.",
)
async def engine_health() -> dict:
    return {
        "status": "ok",
        "cache": cache_stats(),
    }