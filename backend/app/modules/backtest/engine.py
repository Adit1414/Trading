"""
app/modules/backtest/engine.py
────────────────────────────────
Backtesting Engine Orchestrator — HLD §4.2, Module 2
Binance / Cryptocurrency only (SRS §1.2)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from backtesting import Backtest

from app.core.config import settings
from app.crud.backtests import create_backtest
from app.crud.strategies import get_strategy_by_type_code
from app.db.session import get_db
from app.modules.backtest.data_cache import get_historical_data
from app.modules.backtest.strategies import get_strategy_class
from app.modules.backtest.strategies.base import StrategyConfigError
from app.schemas.backtest import (
    BacktestParameters,
    BacktestRunRequest,
    BacktestRunResponse,
    BacktestStatus,
    BacktestStatistics,
    EquityPoint,
    TradeRecord,
)
from app.services.market_data.base import OHLCV

logger = logging.getLogger(__name__)

_thread_pool = ThreadPoolExecutor(
    max_workers=settings.BACKTEST_THREAD_POOL_SIZE,
    thread_name_prefix="backtest-worker",
)

_CHARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "charts")


class BacktestError(RuntimeError):
    """Raised when a backtest cannot be completed."""


async def run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    """Primary entry point — called by the API route handler."""

    backtest_id = str(uuid.uuid4())
    created_at  = datetime.now(tz=timezone.utc)

    logger.info(
        "Backtest %s | strategy=%s symbol=%s interval=%s [%s → %s]",
        backtest_id, request.strategy.value, request.symbol,
        request.interval.value, request.start_date, request.end_date,
    )

    # ── 1. Fetch historical K-lines (LRU cached) ──────────────────────────────
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

    # ── 3. Find strategy class ────────────────────────────────────────────────
    try:
        strategy_class = get_strategy_class(request.strategy.value)
    except KeyError as exc:
        raise BacktestError(str(exc)) from exc

    if len(df) < strategy_class.get_min_bars_required():
        raise BacktestError(
            f"Insufficient data: {request.strategy.value} requires at least "
            f"{strategy_class.get_min_bars_required()} bars; got {len(df)}. "
            "Extend the date range or use a shorter interval."
        )

    # ── 4. Set class properties per config ───────────────────────────────────
    # Since backtesting.py uses class attributes for iteration/optimization mapping, 
    # we inject the config into the class dynamically for this run.
    # Note: In concurrent setups with the exact same class, this might race. 
    # A cleaner approach for backtesting is creating a dynamic subclass.
    DynamicStrategy = type("DynamicStrategy", (strategy_class,), request.strategy_config)

    # ── 5. Run backtest (thread pool) ─────────────────────────────────────────
    loop = asyncio.get_running_loop()
    try:
        stats_series, chart_html = await loop.run_in_executor(
            _thread_pool,
            _run_backtest_sync,
            df,
            DynamicStrategy,
            request,
            backtest_id
        )
    except Exception as exc:
        raise BacktestError(f"Trade simulation failed: {exc}") from exc

    # ── 6. Assemble response ──────────────────────────────────────────────────
    duration_days = (request.end_date - request.start_date).days

    parameters = BacktestParameters(
        name=request.name,
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
    
    # ── Map stats ─────────────────────────────────────────────────────────────
    # stats_series contains all backtesting output metrics.
    total_return_pct = stats_series["Return [%]"]
    final_equity = stats_series["Equity Final [$]"]
    
    # Drawdown metrics mapping
    max_dd_pct = stats_series["Max. Drawdown [%]"]
    max_dd = -abs(max_dd_pct) / 100 * stats_series["Equity Peak [$]"]

    statistics = BacktestStatistics(
        total_return=final_equity - request.initial_cash,
        total_return_pct=total_return_pct,
        final_portfolio_value=final_equity,
        win_rate=stats_series["Win Rate [%]"] if not pd.isna(stats_series["Win Rate [%]"]) else 0.0,
        max_drawdown=max_dd if not pd.isna(max_dd) else 0.0,
        max_drawdown_pct=max_dd_pct if not pd.isna(max_dd_pct) else 0.0,
        total_trades=int(stats_series["# Trades"]),
        winning_trades=len(stats_series["_trades"][stats_series["_trades"]["PnL"] > 0]),
        losing_trades=len(stats_series["_trades"][stats_series["_trades"]["PnL"] <= 0]),
        open_trades=0, # backtesting.py closes all if finalize_trades (default) OR we can't easily extract open
        avg_win=stats_series["_trades"][stats_series["_trades"]["PnL"] > 0]["PnL"].mean() if len(stats_series["_trades"][stats_series["_trades"]["PnL"] > 0]) > 0 else 0.0,
        avg_loss=stats_series["_trades"][stats_series["_trades"]["PnL"] <= 0]["PnL"].mean() if len(stats_series["_trades"][stats_series["_trades"]["PnL"] <= 0]) > 0 else 0.0,
        profit_factor=stats_series["Profit Factor"],
        avg_trade_duration_bars=int(stats_series["Avg. Trade Duration"].total_seconds() / (df.index[1] - df.index[0]).total_seconds()) if len(df) > 1 and not pd.isna(stats_series["Avg. Trade Duration"]) else 0,
    )

    # Trade records
    trade_records = []
    bt_trades = stats_series["_trades"]
    for i, row in bt_trades.iterrows():
        trade_records.append(TradeRecord(
            trade_number=i+1,
            direction="LONG" if row["Size"] > 0 else "SHORT",
            entry_date=str(row["EntryTime"]),
            entry_price=row["EntryPrice"],
            exit_date=str(row["ExitTime"]),
            exit_price=row["ExitPrice"],
            quantity_usdt=abs(row["Size"]) * row["EntryPrice"],
            pnl=row["PnL"],
            return_pct=row["ReturnPct"] * 100,
            status="CLOSED"
        ))

    equity_points = []
    eq_curve = stats_series["_equity_curve"]
    for ts, row in eq_curve.iterrows():
        equity_points.append(EquityPoint(
            timestamp=str(ts),
            value=row["Equity"]
        ))

    response = BacktestRunResponse(
        backtest_id=backtest_id,
        name=request.name,
        status=BacktestStatus.COMPLETED,
        created_at=created_at,
        equity_curve=equity_points,
        start_date=str(request.start_date),
        end_date=str(request.end_date),
        duration_days=duration_days,
        total_return=statistics.total_return,
        total_return_pct=statistics.total_return_pct,
        statistics=statistics,
        parameters=parameters,
        trade_log=trade_records,
    )

    logger.info(
        "Backtest %s completed | trades=%d return=%.2f%%",
        backtest_id, statistics.total_trades, statistics.total_return_pct,
    )

    await _persist_result_stub(backtest_id, request, response, chart_html)
    return response


# ─── Synchronous helpers (run inside thread pool) ─────────────────────────────

def _run_backtest_sync(df: pd.DataFrame, strategy_class, req: BacktestRunRequest, backtest_id: str) -> tuple:
    # Ensure charts directory exists
    os.makedirs(os.path.abspath(_CHARTS_DIR), exist_ok=True)
    chart_path = os.path.join(os.path.abspath(_CHARTS_DIR), f"{backtest_id}.html")
    
    # Initialize backtest
    bt = Backtest(
        df, 
        strategy=strategy_class, 
        cash=req.initial_cash,
        commission=req.commission,
        margin=1.0, 
        trade_on_close=False,
        hedging=False,
        exclusive_orders=True 
    )

    # Run
    stats = bt.run()
    
    # Try generating chart, fall back string if failed
    chart_html = ""
    try:
        # Generate bokeh interactive chart 
        # this will write full HTML to the file path specified.
        bt.plot(filename=chart_path, open_browser=False, resample=False)
        with open(chart_path, "r", encoding="utf-8") as f:
            chart_html = f.read()
    except Exception as e:
        logger.warning(f"Failed to generate backtesting chart: {e}")

    return stats, chart_html


def _bars_to_dataframe(bars: list[OHLCV]) -> pd.DataFrame:
    # backtesting.py expects capitalized columns including Open, High, Low, Close, Volume
    records = [
        {"timestamp": b.timestamp, "Open": b.open, "High": b.high,
         "Low": b.low, "Close": b.close, "Volume": b.volume}
        for b in bars
    ]
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()
    for col in ("Open", "High", "Low", "Close", "Volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["Open", "High", "Low", "Close"])


# ─── DB persistence stub ─────────────────────────────────────────────────────

async def _persist_result_stub(
    backtest_id: str,
    request: BacktestRunRequest,
    response: BacktestRunResponse,
    chart_html: Optional[str] = None,
) -> None:
    try:
        async with get_db() as session:
            if session is None:
                logger.warning("No DB session configured, skipping persistence for backtest %s", backtest_id)
                return

            strategy = await get_strategy_by_type_code(session, request.strategy.value)
            if not strategy:
                logger.warning("Could not find DB strategy %s, skipping persistence", request.strategy.value)
                return

            await create_backtest(
                session=session,
                id=backtest_id,
                user_id=request.user_id,
                strategy_id=strategy.id,
                symbol=request.symbol,
                timeframe=request.interval.value,
                parameters=response.parameters.model_dump(mode="json"),
                metrics=response.statistics.model_dump(mode="json"),
                result_file_url=None,
                chart_html=chart_html,
            )
            await session.commit()
            logger.debug("DB persist complete — backtest_id=%s", backtest_id)
    except Exception as exc:
        logger.exception("Failed to persist backtest %s to database", backtest_id)

def get_chart_path(backtest_id: str) -> Optional[str]:
    """Return the absolute path to a saved chart, or None if not found."""
    charts_dir = os.path.abspath(_CHARTS_DIR)
    filepath = os.path.join(charts_dir, f"{backtest_id}.html")
    if os.path.exists(filepath):
        return filepath
    return None