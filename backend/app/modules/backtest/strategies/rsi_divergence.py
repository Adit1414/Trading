"""
app/modules/backtest/strategies/rsi_divergence.py
───────────────────────────────────────────────────
RSI Divergence Strategy — Binance Cryptocurrency

Parameters (xlsx):
  period:           2–50,  default 14  — RSI calculation window
  oversold:         10–40, default 30  — buy signal threshold
  overbought:       60–90, default 70  — sell signal threshold
  lookback_periods: 3–10,  default 5   — bars to scan for divergence
  source:           CLOSE | OPEN | HL2

Signal logic (divergence detection):
  BULLISH DIVERGENCE (BUY):
    Price makes a lower low in the last `lookback_periods` bars
    while RSI makes a higher low → momentum diverging upward.

  BEARISH DIVERGENCE (SELL):
    Price makes a higher high in the last `lookback_periods` bars
    while RSI makes a lower high → momentum diverging downward.

  OVERSOLD / OVERBOUGHT crossover fallback:
    If no divergence is found, falls back to simple RSI threshold crossover.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict

import numpy as np
import pandas as pd

from app.modules.backtest.strategies.base import (
    SIGNAL_BUY, SIGNAL_HOLD, SIGNAL_SELL, BaseStrategy, StrategyConfigError,
)
from app.modules.backtest.strategies.ema_crossover import _get_price_series, _get_tick_price


class RSIDivergenceStrategy(BaseStrategy):
    display_name = "RSI Divergence"
    strategy_id  = "RSI_DIVERGENCE"
    description  = (
        "Detects bullish/bearish divergence between price and RSI momentum. "
        "Buy when price makes a lower low but RSI makes a higher low; "
        "sell when price makes a higher high but RSI makes a lower high. "
        "Falls back to oversold/overbought threshold crossovers."
    )

    def _validate_config(self, config: Dict[str, Any]) -> None:
        try:
            self.period           = int(config.get("period",           14))
            self.oversold         = int(config.get("oversold",         30))
            self.overbought       = int(config.get("overbought",       70))
            self.lookback_periods = int(config.get("lookback_periods",  5))
            self.source           = str(config.get("source",        "CLOSE")).upper()
        except (TypeError, ValueError) as exc:
            raise StrategyConfigError(f"RSI Divergence: invalid config — {exc}") from exc

        if not (2 <= self.period <= 50):
            raise StrategyConfigError("period must be 2–50")
        if not (10 <= self.oversold <= 40):
            raise StrategyConfigError("oversold must be 10–40")
        if not (60 <= self.overbought <= 90):
            raise StrategyConfigError("overbought must be 60–90")
        if self.oversold >= self.overbought:
            raise StrategyConfigError("oversold must be less than overbought")
        if not (3 <= self.lookback_periods <= 10):
            raise StrategyConfigError("lookback_periods must be 3–10")
        if self.source not in ("CLOSE", "OPEN", "HL2"):
            raise StrategyConfigError("source must be CLOSE, OPEN, or HL2")

        # Live state
        self._prices: deque[float] = deque(maxlen=self.period + self.lookback_periods + 2)
        self._prev_rsi: float | None = None

    @property
    def min_bars_required(self) -> int:
        return self.period + self.lookback_periods + 1

    # ─── Backtesting (vectorised) ─────────────────────────────────────────────

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        prices = _get_price_series(df, self.source)
        lb     = self.lookback_periods

        # ── RSI ───────────────────────────────────────────────────────────────
        delta = prices.diff()
        gain  = delta.clip(lower=0).rolling(self.period, min_periods=self.period).mean()
        loss  = (-delta.clip(upper=0)).rolling(self.period, min_periods=self.period).mean()
        rs    = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))

        # ── Divergence detection ──────────────────────────────────────────────
        signals = np.full(len(df), SIGNAL_HOLD, dtype=int)

        for i in range(self.min_bars_required, len(df)):
            price_window = prices.iloc[i - lb : i + 1].values
            rsi_window   = df["rsi"].iloc[i - lb : i + 1].values

            if np.any(np.isnan(rsi_window)):
                continue

            cur_price = price_window[-1]
            cur_rsi   = rsi_window[-1]

            # Bullish divergence: price lower low + RSI higher low
            prev_price_min = np.min(price_window[:-1])
            prev_rsi_min   = np.min(rsi_window[:-1])
            if cur_price < prev_price_min and cur_rsi > prev_rsi_min:
                if cur_rsi < self.overbought:      # not already overbought
                    signals[i] = SIGNAL_BUY
                    continue

            # Bearish divergence: price higher high + RSI lower high
            prev_price_max = np.max(price_window[:-1])
            prev_rsi_max   = np.max(rsi_window[:-1])
            if cur_price > prev_price_max and cur_rsi < prev_rsi_max:
                if cur_rsi > self.oversold:         # not already oversold
                    signals[i] = SIGNAL_SELL
                    continue

            # Fallback: simple threshold crossover
            prev_rsi_val = df["rsi"].iloc[i - 1]
            if not np.isnan(prev_rsi_val):
                if cur_rsi > self.oversold and prev_rsi_val <= self.oversold:
                    signals[i] = SIGNAL_BUY
                elif cur_rsi < self.overbought and prev_rsi_val >= self.overbought:
                    signals[i] = SIGNAL_SELL

        df["signal"] = signals
        df.loc[df.index[: self.min_bars_required], "signal"] = SIGNAL_HOLD
        return df

    # ─── Live tick evaluation (Module 4) ────────────────────────────────────

    def evaluate_tick(self, tick: Dict[str, float], position: int) -> int:
        self._prices.append(_get_tick_price(tick, self.source))
        if len(self._prices) < self.period + 1:
            return SIGNAL_HOLD

        prices_list = list(self._prices)
        rsi = _calc_rsi(prices_list, self.period)

        signal = SIGNAL_HOLD
        if self._prev_rsi is not None:
            if rsi > self.oversold and self._prev_rsi <= self.oversold:
                signal = SIGNAL_BUY
            elif rsi < self.overbought and self._prev_rsi >= self.overbought:
                signal = SIGNAL_SELL

        self._prev_rsi = rsi
        return signal


def _calc_rsi(prices: list[float], period: int) -> float:
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains  = [d for d in deltas if d > 0]
    losses = [-d for d in deltas if d < 0]
    ag = sum(gains[-period:])  / period if gains  else 0.0
    al = sum(losses[-period:]) / period if losses else 0.0
    return 100.0 if al == 0 else 100 - (100 / (1 + ag / al))
