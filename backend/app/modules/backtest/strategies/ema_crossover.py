"""
app/modules/backtest/strategies/ema_crossover.py
──────────────────────────────────────────────────
EMA CrossOver Strategy — Binance Cryptocurrency

Parameters (Image 3):
  fast_period – Short-term EMA (e.g. 9, 12, 20).
  slow_period – Long-term EMA  (e.g. 26, 50, 200).
  source      – Price input: CLOSE | OPEN | HL2  (default: CLOSE).

Signal logic:
  BUY  when fast EMA crosses ABOVE slow EMA (bullish crossover).
  SELL when fast EMA crosses BELOW slow EMA (bearish crossover).
  HOLD otherwise.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict

import numpy as np
import pandas as pd

from app.modules.backtest.strategies.base import (
    SIGNAL_BUY,
    SIGNAL_HOLD,
    SIGNAL_SELL,
    BaseStrategy,
    StrategyConfigError,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_price_series(df: pd.DataFrame, source: str) -> pd.Series:
    """
    Extract the price series from a DataFrame based on the `source` enum value.
      CLOSE – df["close"]
      OPEN  – df["open"]
      HL2   – (df["high"] + df["low"]) / 2
    """
    s = source.upper()
    if s == "CLOSE":
        return df["close"]
    if s == "OPEN":
        return df["open"]
    if s == "HL2":
        return (df["high"] + df["low"]) / 2
    raise StrategyConfigError(f"Unknown source '{source}'. Must be CLOSE, OPEN or HL2.")


def _get_tick_price(tick: Dict[str, float], source: str) -> float:
    """Extract a single price value from a tick dict based on source."""
    s = source.upper()
    if s == "CLOSE":
        return tick["close"]
    if s == "OPEN":
        return tick["open"]
    if s == "HL2":
        return (tick["high"] + tick["low"]) / 2
    raise StrategyConfigError(f"Unknown source '{source}'.")


def _calc_ema(prices: list[float], period: int) -> float:
    """Compute the final EMA value from a list of prices."""
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return ema


# ─── Strategy ────────────────────────────────────────────────────────────────

class EMACrossoverStrategy(BaseStrategy):
    display_name = "EMA CrossOver"
    strategy_id  = "EMA_CROSSOVER"

    def _validate_config(self, config: Dict[str, Any]) -> None:
        try:
            self.fast_period = int(config.get("fast_period", 12))
            self.slow_period = int(config.get("slow_period", 26))
            self.source      = str(config.get("source", "CLOSE")).upper()
        except (TypeError, ValueError) as exc:
            raise StrategyConfigError(f"EMA CrossOver: invalid config — {exc}") from exc

        if self.fast_period < 2:
            raise StrategyConfigError("fast_period must be ≥ 2")
        if self.slow_period <= self.fast_period:
            raise StrategyConfigError("slow_period must be > fast_period")
        if self.source not in ("CLOSE", "OPEN", "HL2"):
            raise StrategyConfigError("source must be CLOSE, OPEN or HL2")

        # Live-tick state (Module 4 — Bot Execution)
        self._prices: deque[float] = deque(maxlen=self.slow_period * 3)
        self._prev_fast_ema: float | None = None
        self._prev_slow_ema: float | None = None

    @property
    def min_bars_required(self) -> int:
        return self.slow_period

    # ─── Backtesting (vectorised) ────────────────────────────────────────────

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        prices = _get_price_series(df, self.source)

        df["ema_fast"] = prices.ewm(span=self.fast_period, adjust=False).mean()
        df["ema_slow"] = prices.ewm(span=self.slow_period, adjust=False).mean()

        prev_fast = df["ema_fast"].shift(1)
        prev_slow = df["ema_slow"].shift(1)

        bullish = (df["ema_fast"] > df["ema_slow"]) & (prev_fast <= prev_slow)
        bearish = (df["ema_fast"] < df["ema_slow"]) & (prev_fast >= prev_slow)

        df["signal"] = np.where(bullish, SIGNAL_BUY,
                       np.where(bearish, SIGNAL_SELL, SIGNAL_HOLD))

        # Zero out warm-up period to avoid acting on incomplete EMAs
        df.loc[df.index[: self.slow_period], "signal"] = SIGNAL_HOLD
        return df

    # ─── Live tick evaluation (Module 4) ────────────────────────────────────

    def evaluate_tick(self, tick: Dict[str, float], position: int) -> int:
        price = _get_tick_price(tick, self.source)
        self._prices.append(price)

        if len(self._prices) < self.slow_period:
            return SIGNAL_HOLD

        prices_list = list(self._prices)
        fast_ema = _calc_ema(prices_list[-self.fast_period * 2:], self.fast_period)
        slow_ema = _calc_ema(prices_list,                          self.slow_period)

        signal = SIGNAL_HOLD
        if self._prev_fast_ema is not None:
            if fast_ema > slow_ema and self._prev_fast_ema <= self._prev_slow_ema:
                signal = SIGNAL_BUY
            elif fast_ema < slow_ema and self._prev_fast_ema >= self._prev_slow_ema:
                signal = SIGNAL_SELL

        self._prev_fast_ema = fast_ema
        self._prev_slow_ema = slow_ema
        return signal