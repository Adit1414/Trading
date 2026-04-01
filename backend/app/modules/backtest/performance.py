"""
app/modules/backtest/performance.py
────────────────────────────────────
Performance Synthesizer — HLD §4.2  (Binance / Cryptocurrency)

Key changes from initial version:
  • `spread` renamed to `slippage` (correct Binance terminology).
  • Order sizing supports two modes:
      - PCT_EQUITY  : allocate `order_size_pct` % of current equity per trade.
      - FIXED_USDT  : spend a fixed `order_size_usdt` amount per trade.
  • Trade records now carry `quantity_usdt` (USDT value of position at entry)
    instead of an integer `quantity`, which is more natural for crypto.
  • Slippage is applied correctly:
      Buy  execution price = candle_open × (1 + slippage)
      Sell execution price = candle_open × (1 − slippage)
  • Commission charged on both entry and exit legs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.schemas.backtest import (
    BacktestStatistics,
    EquityPoint,
    OrderSizeMode,
    TradeRecord,
)


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
) -> Tuple[List[EquityPoint], List[Dict[str, Any]], float]:
    """
    Walk-forward trade simulation with look-ahead bias prevention.

    Execution rules:
      • Signals are shifted by 1 bar — act on the NEXT bar's open price.
      • Buy  price = next_open × (1 + slippage)  [slippage raises cost]
      • Sell price = next_open × (1 − slippage)  [slippage lowers revenue]
      • Commission charged on each leg: buy_cost × commission, sell_rev × commission.
      • Position size:
          PCT_EQUITY  → spend (order_size_pct / 100) × current_cash per trade.
          FIXED_USDT  → spend min(order_size_usdt, current_cash) per trade.
      • Intraday mode: force-close any open position at the last bar of each day.

    Returns:
        (equity_curve, raw_trades, final_portfolio_value)
    """
    signals = df["signal"].values
    opens   = df["open"].values
    closes  = df["close"].values
    dates   = df.index

    use_pct   = (order_size_mode == OrderSizeMode.PCT_EQUITY or
                 order_size_mode == "PCT_EQUITY")
    size_pct  = order_size_pct / 100.0          # e.g. 1.0 = 100 % of cash
    size_usdt = order_size_usdt or initial_cash  # fallback

    cash          = initial_cash
    position_usdt = 0.0   # USDT currently in a position
    entry_price   = 0.0
    raw_trades: List[Dict[str, Any]] = []
    equity_curve: List[EquityPoint]  = [
        EquityPoint(timestamp=str(dates[0]), value=round(initial_cash, 4))
    ]
    trade_number = 0

    for i in range(1, len(df)):
        prev_signal = int(signals[i - 1])
        exec_buy    = opens[i] * (1 + slippage)
        exec_sell   = opens[i] * (1 - slippage)

        # ── Enter long ────────────────────────────────────────────────────────
        if prev_signal == 1 and position_usdt == 0 and cash > 0:
            # budget = total cash to spend this trade (including commission fee).
            # PCT_EQUITY: budget = cash × size_pct  (100 % → spend all cash)
            # FIXED_USDT: budget = min(order_size_usdt, cash)
            budget = cash * size_pct if use_pct else min(size_usdt, cash)

            # alloc = net USDT allocated to position (AFTER commission deducted).
            # budget = alloc + alloc*commission = alloc*(1+commission)
            # => alloc = budget / (1+commission)
            # This guarantees cost == budget <= cash, so the check always passes.
            alloc = budget / (1 + commission)
            cost  = budget   # total cash deducted

            if cash >= cost and alloc > 0:
                position_usdt = alloc
                entry_price   = exec_buy
                cash         -= cost
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
                })

        # ── Intraday force-close check ────────────────────────────────────────
        if intraday and position_usdt > 0 and i < len(df) - 1:
            cur_day  = str(dates[i])[:10]
            next_day = str(dates[i + 1])[:10]
            if cur_day != next_day:
                prev_signal = -1  # trigger exit at start of next bar

        # ── Exit long ─────────────────────────────────────────────────────────
        if prev_signal == -1 and position_usdt > 0:
            # position_usdt = net USDT allocated at entry (already deducted from cash).
            # price_ratio   = how much the price moved since entry.
            # gross_exit    = what the position is worth at current sell price.
            # revenue       = gross_exit minus exit commission fee.
            # pnl           = revenue - original position cost.
            #   Entry cost  = position_usdt * (1 + commission)  [entry commission]
            #   But because we pre-deducted using budget = alloc*(1+commission),
            #   the true entry cost basis is just position_usdt (alloc).
            #   P&L = revenue - position_usdt
            price_ratio  = exec_sell / entry_price
            gross_exit   = position_usdt * price_ratio
            revenue      = gross_exit * (1 - commission)
            pnl          = round(revenue - position_usdt, 6)
            ret_pct      = round((pnl / position_usdt) * 100, 4)

            cash         += revenue
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
            price_ratio      = closes[i] / entry_price
            current_pos_val  = position_usdt * price_ratio
            portfolio_value  = cash + current_pos_val
        else:
            portfolio_value  = cash

        equity_curve.append(
            EquityPoint(timestamp=str(dates[i]), value=round(portfolio_value, 4))
        )

    # Mark remaining open trade with unrealised P&L
    if raw_trades and raw_trades[-1]["status"] == "OPEN" and position_usdt > 0:
        last_price    = closes[-1]
        price_ratio   = last_price / entry_price
        unrealised    = round((position_usdt * price_ratio) - position_usdt, 6)
        raw_trades[-1]["unrealised_pnl"] = unrealised

    final_value = equity_curve[-1].value
    return equity_curve, raw_trades, final_value


# ─── Performance Metrics ──────────────────────────────────────────────────────

def synthesize(
    equity_curve:  List[EquityPoint],
    raw_trades:    List[Dict[str, Any]],
    initial_cash:  float,
) -> Tuple[BacktestStatistics, List[TradeRecord]]:
    """
    Compute all performance statistics from the simulation output.
    """
    closed = [t for t in raw_trades if t["status"] == "CLOSED"]
    open_  = [t for t in raw_trades if t["status"] == "OPEN"]

    final_value   = equity_curve[-1].value if equity_curve else initial_cash
    total_return  = round(final_value - initial_cash, 4)
    total_ret_pct = round((total_return / initial_cash) * 100, 4) if initial_cash else 0.0

    winners = [t for t in closed if (t["pnl"] or 0) > 0]
    losers  = [t for t in closed if (t["pnl"] or 0) <= 0]

    win_rate = round(len(winners) / len(closed) * 100, 2) if closed else 0.0
    avg_win  = round(sum(t["pnl"] for t in winners) / len(winners), 4) if winners else 0.0
    avg_loss = round(sum(t["pnl"] for t in losers)  / len(losers),  4) if losers  else 0.0

    gross_wins   = sum(t["pnl"] for t in winners)
    gross_losses = abs(sum(t["pnl"] for t in losers))
    profit_factor: Optional[float] = (
        round(gross_wins / gross_losses, 4) if gross_losses > 0 else None
    )

    max_dd, max_dd_pct = _max_drawdown(equity_curve)

    stats = BacktestStatistics(
        total_return=total_return,
        total_return_pct=total_ret_pct,
        final_portfolio_value=round(final_value, 4),
        win_rate=win_rate,
        max_drawdown=round(max_dd, 4),
        max_drawdown_pct=round(max_dd_pct, 4),
        total_trades=len(closed),
        winning_trades=len(winners),
        losing_trades=len(losers),
        open_trades=len(open_),
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        avg_trade_duration_bars=_avg_duration(closed),
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


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _max_drawdown(curve: List[EquityPoint]) -> Tuple[float, float]:
    if not curve:
        return 0.0, 0.0
    peak = curve[0].value
    max_dd = max_dd_pct = 0.0
    for pt in curve:
        if pt.value > peak:
            peak = pt.value
        dd     = peak - pt.value
        dd_pct = (dd / peak * 100) if peak > 0 else 0.0
        if dd_pct > max_dd_pct:
            max_dd     = dd
            max_dd_pct = dd_pct
    return max_dd, max_dd_pct


def _avg_duration(closed: List[Dict[str, Any]]) -> Optional[float]:
    bars = [t["_entry_bar"] for t in closed if t.get("_entry_bar") is not None]
    return round(sum(bars) / len(bars), 1) if bars else None