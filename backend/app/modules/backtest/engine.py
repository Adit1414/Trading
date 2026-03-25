"""
app/modules/backtest/engine.py
────────────────────────────────
Backtesting Engine Orchestrator — HLD §4.2, Module 2

Pipeline:
  1. Fetch historical K-lines (LRU cached, Binance REST).
  2. Build Pandas DataFrame.
  3. Instantiate + validate strategy.
  4. Vectorised signal generation → thread pool.
  5. Trade simulation → thread pool.
  6. Performance synthesis (all statistics).
  7. Generate interactive Plotly HTML chart.
  8. Persist result to BACKTESTS table (real DB — replaces stub).
  9. Return BacktestRunResponse.

DB persistence (step 8):
  Looks up STRATEGIES row by type_code, then inserts into BACKTESTS with:
    - parameters : full BacktestParameters dict
    - metrics    : full BacktestStatistics dict
    - result_file_url : None (Supabase Storage upload is a future enhancement)
  Gracefully no-ops when DATABASE_URL is not configured.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from app.core.config import settings
from app.crud.backtests import create_backtest
from app.crud.strategies import get_strategy_by_type_code
from app.db.session import get_db
from app.modules.backtest.chart_generator import generate_chart
from app.modules.backtest.data_cache import get_historical_data
from app.modules.backtest.performance import simulate_trades, synthesize
from app.modules.backtest.strategies import get_strategy
from app.modules.backtest.strategies.base import StrategyConfigError
from app.schemas.backtest import (
    BacktestParameters,
    BacktestRunRequest,
    BacktestRunResponse,
    BacktestStatus,
)
from app.services.market_data.base import OHLCV

logger = logging.getLogger(__name__)

_thread_pool = ThreadPoolExecutor(
    max_workers=settings.BACKTEST_THREAD_POOL_SIZE,
    thread_name_prefix="backtest-worker",
)


class BacktestError(RuntimeError):
    pass


async def run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    """Primary entry point — called by the API route handler."""
    backtest_id = str(uuid.uuid4())
    created_at  = datetime.now(tz=timezone.utc)

    logger.info(
        "Backtest %s | %s %s %s [%s → %s]",
        backtest_id, request.strategy.value, request.symbol,
        request.interval.value, request.start_date, request.end_date,
    )

    # ── 1. Fetch K-lines ──────────────────────────────────────────────────────
    try:
        bars = await get_historical_data(
            market=request.trading_market.value,
            symbol=request.symbol,
            interval=request.interval.value,
            start_date=request.start_date,
            end_date=request.end_date,
        )
    except KeyError as exc:
        raise BacktestError(f"Unsupported market: {exc}") from exc
    except Exception as exc:
        raise BacktestError(f"Failed to fetch market data: {exc}") from exc

    if not bars:
        raise BacktestError(
            f"No data returned for {request.symbol} "
            f"[{request.start_date} → {request.end_date}]. "
            "Check the symbol name and date range."
        )

    # ── 2. Build DataFrame ────────────────────────────────────────────────────
    df = _bars_to_dataframe(bars)

    # ── 3. Strategy ───────────────────────────────────────────────────────────
    try:
        strategy = get_strategy(request.strategy.value, request.strategy_config)
    except KeyError as exc:
        raise BacktestError(str(exc)) from exc
    except StrategyConfigError as exc:
        raise BacktestError(f"Strategy config error: {exc}") from exc

    if len(df) < strategy.min_bars_required:
        raise BacktestError(
            f"Insufficient data: {request.strategy.value} needs ≥ "
            f"{strategy.min_bars_required} bars; got {len(df)}. "
            "Extend the date range or use a shorter interval."
        )

    # ── 4. Signal generation (thread pool) ───────────────────────────────────
    loop = asyncio.get_running_loop()
    try:
        df_signals = await loop.run_in_executor(
            _thread_pool, strategy.generate_signals, df
        )
    except Exception as exc:
        raise BacktestError(f"Signal generation failed: {exc}") from exc

    # ── 5. Trade simulation (thread pool) ────────────────────────────────────
    try:
        equity_curve, raw_trades, final_value, commissions_paid = \
            await loop.run_in_executor(
                _thread_pool, _run_simulation, df_signals, request
            )
    except Exception as exc:
        raise BacktestError(f"Trade simulation failed: {exc}") from exc

    # ── 6. Performance synthesis ──────────────────────────────────────────────
    statistics, trade_records = synthesize(
        equity_curve=equity_curve,
        raw_trades=raw_trades,
        initial_cash=request.initial_cash,
        df=df_signals,
        commissions_paid=commissions_paid,
    )

    # ── 7. Plotly chart ───────────────────────────────────────────────────────
    try:
        chart_html = await loop.run_in_executor(
            _thread_pool,
            _generate_chart_sync,
            df_signals, equity_curve, raw_trades,
            request.strategy.value, request.symbol, request.initial_cash,
        )
        
        # Save to disk for later retrieval by the /backtests/{id} endpoint
        charts_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)
        chart_path = charts_dir / f"{backtest_id}.html"
        chart_path.write_text(chart_html, encoding="utf-8")
        
    except Exception as exc:
        logger.warning("Chart generation failed (non-fatal): %s", exc)
        chart_html = "<p>Chart unavailable</p>"

    # ── 8. Assemble response ──────────────────────────────────────────────────
    duration_days = (request.end_date - request.start_date).days

    parameters = BacktestParameters(
        strategy=request.strategy.value,
        strategy_config=request.strategy_config,
        symbol=request.symbol,
        interval=request.interval.value,
        contract_type=request.contract_type.value,
        trading_market=request.trading_market.value,
        initial_cash=request.initial_cash,
        commission=request.commission,
        slippage=request.slippage,
        order_size_mode=request.order_size_mode.value,
        order_size_usdt=request.order_size_usdt,
        order_size_pct=request.order_size_pct,
        intraday=request.intraday,
        start_date=str(request.start_date),
        end_date=str(request.end_date),
        duration_days=duration_days,
    )

    response = BacktestRunResponse(
        backtest_id=backtest_id,
        name=request.name,
        status=BacktestStatus.COMPLETED,
        created_at=created_at,
        equity_curve=equity_curve,
        start_date=str(request.start_date),
        end_date=str(request.end_date),
        duration_days=duration_days,
        total_return=statistics.total_return,
        total_return_pct=statistics.total_return_pct,
        statistics=statistics,
        parameters=parameters,
        trade_log=trade_records,
        chart_html=chart_html,
    )

    logger.info(
        "Backtest %s done | trades=%d return=%.2f%% sharpe=%.2f",
        backtest_id, statistics.total_trades,
        statistics.total_return_pct, statistics.sharpe_ratio,
    )

    # ── 9. Persist to BACKTESTS table (real DB) ───────────────────────────────
    await _persist_result(
        backtest_id=backtest_id,
        request=request,
        parameters=parameters,
        statistics=statistics,
    )

    return response


# ─── DB persistence ───────────────────────────────────────────────────────────

async def _persist_result(
    backtest_id: str,
    request:     BacktestRunRequest,
    parameters:  BacktestParameters,
    statistics,
) -> None:
    """
    Persist the backtest result to the BACKTESTS table.

    Flow:
      1. Open a DB session (no-ops gracefully if DATABASE_URL is unset).
      2. Look up the STRATEGIES row by type_code to get the strategy_id FK.
      3. Insert into BACKTESTS:
           - parameters : full execution config as JSONB
           - metrics    : scalar stats as JSONB
           - result_file_url : None (Supabase Storage upload is future work)
    """
    async with get_db() as session:
        if session is None:
            logger.debug("DB not configured — skipping backtest persistence.")
            return

        try:
            # Resolve strategy FK
            strategy_row = await get_strategy_by_type_code(
                session, request.strategy.value
            )
            if strategy_row is None:
                logger.error(
                    "Strategy type_code '%s' not found in STRATEGIES table. "
                    "Did the seed run on startup?",
                    request.strategy.value,
                )
                return

            # Serialise statistics to a plain dict for JSONB storage
            metrics_dict = statistics.model_dump()

            row = await create_backtest(
                session=session,
                id=backtest_id,
                user_id=request.user_id,           # None until Module 1 auth
                strategy_id=strategy_row.id,
                symbol=request.symbol,
                timeframe=request.interval.value,
                parameters=parameters.model_dump(),
                metrics=metrics_dict,
                result_file_url=None,              # Supabase Storage: future
            )
            logger.info(
                "Backtest persisted to DB: db_id=%s backtest_id=%s",
                row.id, backtest_id,
            )

        except Exception as exc:
            logger.error(
                "Failed to persist backtest %s to DB: %s",
                backtest_id, exc, exc_info=True,
            )
            # Non-fatal — the API response is already assembled


# ─── Sync helpers (run in thread pool) ───────────────────────────────────────

def _run_simulation(df: pd.DataFrame, req: BacktestRunRequest) -> tuple:
    return simulate_trades(
        df=df,
        initial_cash=req.initial_cash,
        commission=req.commission,
        slippage=req.slippage,
        order_size_mode=req.order_size_mode,
        order_size_pct=req.order_size_pct,
        order_size_usdt=req.order_size_usdt,
        intraday=req.intraday,
    )


def _generate_chart_sync(df, equity_curve, raw_trades, strategy_id, symbol, initial_cash):
    return generate_chart(
        df=df,
        equity_curve=equity_curve,
        raw_trades=raw_trades,
        strategy_id=strategy_id,
        symbol=symbol,
        initial_cash=initial_cash,
    )


def _bars_to_dataframe(bars: list[OHLCV]) -> pd.DataFrame:
    records = [
        {"timestamp": b.timestamp, "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in bars
    ]
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["open", "high", "low", "close"])