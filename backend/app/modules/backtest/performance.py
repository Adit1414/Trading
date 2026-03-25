"""
app/modules/backtest/performance.py
────────────────────────────────────
Performance Synthesizer — HLD §4.2

Computes the full statistics set:
  Equity Final/Peak, Return, Exposure Time, Annualised Return,
  Annualised Volatility, CAGR, Buy & Hold Return, Alpha, Beta,
  Sharpe, Sortino, Calmar, Max/Avg Drawdown + Durations,
  Commissions Paid, Win Rate, Avg Win/Loss, Profit Factor.
"""

from __future__ import annotations

import math
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.schemas.backtest import (
    BacktestStatistics,
    EquityPoint,
    OrderSizeMode,
    TradeRecord,
)

TRADING_DAYS_PER_YEAR = 365   # crypto trades 24/7/365


# ─── Trade Simulation ─────────────────────────────────────────────────────────

def simulate_trades(
    df:              pd.DataFrame,
    initial_cash:    float,
    commission:      float,
    slippage:        float,
    order_size_mode: str,
    order_size_pct:  float,
    order_size_usdt: Optional[float],
    intraday:        bool,
) -> Tuple[List[EquityPoint], List[Dict[str, Any]], float, float]:
    """
    Walk-forward simulation with look-ahead bias prevention.

    Returns: (equity_curve, raw_trades, final_value, total_commissions_paid)
    """
    signals = df["signal"].values
    opens   = df["open"].values
    closes  = df["close"].values
    dates   = df.index

    use_pct   = (order_size_mode in (OrderSizeMode.PCT_EQUITY, "PCT_EQUITY"))
    size_pct  = order_size_pct / 100.0
    size_usdt = order_size_usdt or initial_cash

    cash          = initial_cash
    position_usdt = 0.0
    entry_price   = 0.0
    total_commissions = 0.0
    raw_trades: List[Dict[str, Any]] = []
    equity_curve: List[EquityPoint] = [
        EquityPoint(timestamp=str(dates[0]), value=round(initial_cash, 4))
    ]
    trade_number = 0

    for i in range(1, len(df)):
        prev_signal = int(signals[i - 1])
        exec_buy    = opens[i] * (1 + slippage)
        exec_sell   = opens[i] * (1 - slippage)

        # ── Enter long ────────────────────────────────────────────────────────
        if prev_signal == 1 and position_usdt == 0 and cash > 0:
            # Gross budget is the total cash we are willing to spend (alloc + fee).
            # Divide by (1 + commission) so that fee is drawn from within the budget
            # rather than added on top — otherwise cost always exceeds cash and no
            # trade ever executes (the original bug).
            budget    = cash * size_pct if use_pct else min(size_usdt, cash)
            alloc     = budget / (1 + commission)
            entry_fee = alloc * commission
            cost      = alloc + entry_fee  # == budget, guaranteed <= cash

            # Floating-point precision fix: cost can be slightly > budget (100000.00000000001)
            if cash + 1e-8 >= cost:
                position_usdt = alloc
                entry_price   = exec_buy
                cash          = max(0.0, cash - cost)
                total_commissions += entry_fee
                trade_number += 1
                raw_trades.append({
                    "trade_number":  trade_number,
                    "direction":     "LONG",
                    "entry_date":    str(dates[i]),
                    "entry_price":   round(exec_buy, 8),
                    "exit_date":     None,
                    "exit_price":    None,
                    "quantity_usdt": round(alloc, 4),
                    "pnl":           None,
                    "return_pct":    None,
                    "status":        "OPEN",
                    "_entry_bar":    i,
                    "_entry_cost":   cost,
                })

        # ── Intraday force-close ──────────────────────────────────────────────
        if intraday and position_usdt > 0 and i < len(df) - 1:
            if str(dates[i])[:10] != str(dates[i + 1])[:10]:
                prev_signal = -1

        # ── Exit long ─────────────────────────────────────────────────────────
        if prev_signal == -1 and position_usdt > 0:
            price_ratio = exec_sell / entry_price
            exit_value  = position_usdt * price_ratio
            exit_fee    = exit_value * commission
            revenue     = exit_value - exit_fee
            entry_cost  = raw_trades[-1]["_entry_cost"] if raw_trades else position_usdt
            pnl         = round(revenue - entry_cost, 6)
            ret_pct     = round((pnl / entry_cost) * 100, 4)

            cash += revenue
            total_commissions += exit_fee
            position_usdt = 0.0

            if raw_trades and raw_trades[-1]["status"] == "OPEN":
                raw_trades[-1].update({
                    "exit_date":  str(dates[i]),
                    "exit_price": round(exec_sell, 8),
                    "pnl":        pnl,
                    "return_pct": ret_pct,
                    "status":     "CLOSED",
                })

        # ── Mark-to-market equity ─────────────────────────────────────────────
        if position_usdt > 0:
            portfolio_value = cash + position_usdt * (closes[i] / entry_price)
        else:
            portfolio_value = cash

        equity_curve.append(
            EquityPoint(timestamp=str(dates[i]), value=round(portfolio_value, 4))
        )

    # Mark remaining open trade
    if raw_trades and raw_trades[-1]["status"] == "OPEN" and position_usdt > 0:
        raw_trades[-1]["unrealised_pnl"] = round(
            (position_usdt * (closes[-1] / entry_price)) - position_usdt, 6
        )

    final_value = equity_curve[-1].value
    return equity_curve, raw_trades, final_value, round(total_commissions, 4)


# ─── Performance Synthesis ────────────────────────────────────────────────────

def synthesize(
    equity_curve:    List[EquityPoint],
    raw_trades:      List[Dict[str, Any]],
    initial_cash:    float,
    df:              pd.DataFrame,
    commissions_paid: float,
) -> Tuple[BacktestStatistics, List[TradeRecord]]:
    """
    Build all statistics.
    """
    closed = [t for t in raw_trades if t["status"] == "CLOSED"]
    open_  = [t for t in raw_trades if t["status"] == "OPEN"]

    final_value  = equity_curve[-1].value if equity_curve else initial_cash
    peak_value   = max(p.value for p in equity_curve) if equity_curve else initial_cash
    total_return = round(final_value - initial_cash, 4)
    total_ret_pct = round((total_return / initial_cash) * 100, 4)

    # ── Equity series as numpy array ──────────────────────────────────────────
    eq_vals  = np.array([p.value for p in equity_curve], dtype=float)
    n_bars   = len(eq_vals)

    # ── Daily returns ─────────────────────────────────────────────────────────
    daily_ret = np.diff(eq_vals) / eq_vals[:-1]          # fraction change per bar

    # ── Exposure time ─────────────────────────────────────────────────────────
    bars_in_position = sum(
        max(0, t.get("_entry_bar", 0)) for t in closed + open_
    )
    exposure_time_pct = round((bars_in_position / max(n_bars, 1)) * 100, 3)

    # ── Annualised metrics ────────────────────────────────────────────────────
    # Use actual calendar days if index has datetime; fall back to bar count
    try:
        start_dt = pd.Timestamp(equity_curve[0].timestamp)
        end_dt   = pd.Timestamp(equity_curve[-1].timestamp)
        years    = max((end_dt - start_dt).total_seconds() / (365.25 * 86400), 1e-9)
    except Exception:
        years    = max(n_bars / TRADING_DAYS_PER_YEAR, 1e-9)

    vol_daily  = float(np.std(daily_ret, ddof=1)) if len(daily_ret) > 1 else 0.0
    vol_ann    = round(vol_daily * math.sqrt(TRADING_DAYS_PER_YEAR) * 100, 4)

    ret_ann    = round(((final_value / initial_cash) ** (1 / years) - 1) * 100, 4)
    cagr       = ret_ann   # same formula; CAGR IS the annualised return

    # ── Buy & Hold benchmark ──────────────────────────────────────────────────
    first_close = float(df["close"].iloc[0])
    last_close  = float(df["close"].iloc[-1])
    bh_return   = round(((last_close / first_close) - 1) * 100, 4)

    # ── Alpha & Beta vs buy-and-hold ──────────────────────────────────────────
    bh_ret_series = np.diff(df["close"].values) / df["close"].values[:-1]
    alpha, beta   = _alpha_beta(daily_ret, bh_ret_series)

    # ── Risk-adjusted ratios ──────────────────────────────────────────────────
    sharpe  = _sharpe(daily_ret)
    sortino = _sortino(daily_ret)
    max_dd_pct, avg_dd_pct, max_dd_dur, avg_dd_dur = _drawdown_metrics(eq_vals, equity_curve)
    calmar  = round(ret_ann / max_dd_pct, 4) if max_dd_pct > 0 else 0.0

    # ── Trade stats ───────────────────────────────────────────────────────────
    winners = [t for t in closed if (t.get("pnl") or 0) > 0]
    losers  = [t for t in closed if (t.get("pnl") or 0) <= 0]
    win_rate = round(len(winners) / len(closed) * 100, 2) if closed else 0.0
    avg_win  = round(sum(t["pnl"] for t in winners) / len(winners), 4) if winners else 0.0
    avg_loss = round(sum(t["pnl"] for t in losers)  / len(losers),  4) if losers  else 0.0
    gross_wins   = sum(t["pnl"] for t in winners)
    gross_losses = abs(sum(t["pnl"] for t in losers))
    profit_factor = round(gross_wins / gross_losses, 4) if gross_losses > 0 else None

    avg_dur = None
    if closed:
        bars = [t["_entry_bar"] for t in closed if t.get("_entry_bar")]
        avg_dur = round(sum(bars) / len(bars), 1) if bars else None

    stats = BacktestStatistics(
        equity_final=round(final_value, 4),
        equity_peak=round(peak_value, 4),
        total_return=total_return,
        total_return_pct=total_ret_pct,
        exposure_time_pct=exposure_time_pct,
        return_ann_pct=ret_ann,
        volatility_ann_pct=vol_ann,
        cagr_pct=cagr,
        buy_hold_return_pct=bh_return,
        alpha_pct=alpha,
        beta=beta,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        max_drawdown_pct=max_dd_pct,
        avg_drawdown_pct=avg_dd_pct,
        max_drawdown_duration=max_dd_dur,
        avg_drawdown_duration=avg_dd_dur,
        total_trades=len(closed),
        winning_trades=len(winners),
        losing_trades=len(losers),
        open_trades=len(open_),
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        avg_trade_duration_bars=avg_dur,
        commissions_paid=commissions_paid,
    )

    trade_records = [
        TradeRecord(
            trade_number=t["trade_number"],
            direction=t["direction"],
            entry_date=t["entry_date"],
            entry_price=t["entry_price"],
            exit_date=t.get("exit_date"),
            exit_price=t.get("exit_price"),
            quantity_usdt=t["quantity_usdt"],
            pnl=t.get("pnl"),
            return_pct=t.get("return_pct"),
            status=t["status"],
        )
        for t in raw_trades
    ]
    return stats, trade_records


# ─── Statistical helpers ──────────────────────────────────────────────────────

def _sharpe(daily_ret: np.ndarray, risk_free: float = 0.0) -> float:
    if len(daily_ret) < 2:
        return 0.0
    mean = np.mean(daily_ret) - risk_free / TRADING_DAYS_PER_YEAR
    std  = np.std(daily_ret, ddof=1)
    return round(float(mean / std * math.sqrt(TRADING_DAYS_PER_YEAR)) if std > 0 else 0.0, 4)


def _sortino(daily_ret: np.ndarray, risk_free: float = 0.0) -> float:
    if len(daily_ret) < 2:
        return 0.0
    mean       = np.mean(daily_ret) - risk_free / TRADING_DAYS_PER_YEAR
    neg        = daily_ret[daily_ret < 0]
    downside   = np.std(neg, ddof=1) if len(neg) > 1 else 0.0
    return round(float(mean / downside * math.sqrt(TRADING_DAYS_PER_YEAR)) if downside > 0 else 0.0, 4)


def _alpha_beta(
    port_ret: np.ndarray,
    bench_ret: np.ndarray,
) -> Tuple[float, float]:
    n = min(len(port_ret), len(bench_ret))
    if n < 2:
        return 0.0, 0.0
    p, b = port_ret[:n], bench_ret[:n]
    var_b = np.var(b, ddof=1)
    beta  = float(np.cov(p, b, ddof=1)[0, 1] / var_b) if var_b > 0 else 0.0
    alpha = float((np.mean(p) - beta * np.mean(b)) * TRADING_DAYS_PER_YEAR * 100)
    return round(alpha, 4), round(beta, 4)


def _drawdown_metrics(
    eq_vals: np.ndarray,
    equity_curve: List[EquityPoint],
) -> Tuple[float, float, str, str]:
    """
    Returns: (max_dd_pct, avg_dd_pct, max_dd_duration_str, avg_dd_duration_str)
    """
    peak = eq_vals[0]
    max_dd_pct = 0.0
    drawdowns: List[float] = []
    dd_durations_bars: List[int] = []

    in_dd        = False
    dd_start_bar = 0
    current_dd_bars = 0

    for i, v in enumerate(eq_vals):
        if v > peak:
            if in_dd:
                dd_durations_bars.append(current_dd_bars)
                in_dd = False
                current_dd_bars = 0
            peak = v
        else:
            dd = (peak - v) / peak * 100 if peak > 0 else 0.0
            if dd > 0:
                if not in_dd:
                    in_dd = True
                    dd_start_bar = i
                current_dd_bars += 1
                drawdowns.append(dd)
                if dd > max_dd_pct:
                    max_dd_pct = dd

    if in_dd:
        dd_durations_bars.append(current_dd_bars)

    avg_dd_pct  = round(float(np.mean(drawdowns)), 4) if drawdowns else 0.0
    max_dd_pct  = round(max_dd_pct, 4)

    # Convert bars to time strings using equity_curve timestamps
    max_dd_dur = _bars_to_duration(max(dd_durations_bars) if dd_durations_bars else 0, equity_curve)
    avg_dd_dur = _bars_to_duration(
        int(np.mean(dd_durations_bars)) if dd_durations_bars else 0, equity_curve
    )
    return max_dd_pct, avg_dd_pct, max_dd_dur, avg_dd_dur


def _bars_to_duration(n_bars: int, equity_curve: List[EquityPoint]) -> str:
    """Estimate a human-readable duration from bar count using the equity curve timestamps."""
    if n_bars <= 0 or len(equity_curve) < 2:
        return "0 days 00:00:00"
    try:
        t0 = pd.Timestamp(equity_curve[0].timestamp)
        t1 = pd.Timestamp(equity_curve[1].timestamp)
        bar_duration = t1 - t0
        total = bar_duration * n_bars
        days  = total.days
        secs  = int(total.seconds)
        h, rem = divmod(secs, 3600)
        m, s   = divmod(rem, 60)
        return f"{days} days {h:02d}:{m:02d}:{s:02d}"
    except Exception:
        return f"{n_bars} bars"
