"""
app/modules/backtest/strategies/ema_crossover.py
──────────────────────────────────────────────────
EMA CrossOver Strategy — Binance Cryptocurrency

Parameters (xlsx: EMA Crossover parameters):
  fast_period : 3–50,   default 12
  slow_period : 15–200, default 26
  source      : CLOSE | OPEN | HL2

Signal:
  BUY  when fast EMA crosses ABOVE slow EMA.
  SELL when fast EMA crosses BELOW slow EMA.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict

import numpy as np
import pandas as pd

from app.modules.backtest.strategies.base import (
    SIGNAL_BUY, SIGNAL_HOLD, SIGNAL_SELL, BaseStrategy, StrategyConfigError,
)


# ─── Shared price-source helpers (imported by other strategy modules) ─────────

def _get_price_series(df: pd.DataFrame, source: str) -> pd.Series:
    s = source.upper()
    if s == "CLOSE": return df["close"]
    if s == "OPEN":  return df["open"]
    if s == "HL2":   return (df["high"] + df["low"]) / 2
    raise StrategyConfigError(f"Unknown source '{source}'. Must be CLOSE, OPEN or HL2.")

def _get_tick_price(tick: Dict[str, float], source: str) -> float:
    s = source.upper()
    if s == "CLOSE": return tick["close"]
    if s == "OPEN":  return tick["open"]
    if s == "HL2":   return (tick["high"] + tick["low"]) / 2
    raise StrategyConfigError(f"Unknown source '{source}'.")

def _calc_ema(prices: list[float], period: int) -> float:
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return ema


# ─── Strategy ────────────────────────────────────────────────────────────────

class EMACrossoverStrategy(BaseStrategy):
    display_name = "EMA CrossOver"
    strategy_id  = "EMA_CROSSOVER"
    description  = (
        "Generates buy signals when the fast EMA crosses above the slow EMA "
        "(bullish momentum) and sell signals on the reverse crossover."
    )

    def _validate_config(self, config: Dict[str, Any]) -> None:
        try:
            self.fast_period = int(config.get("fast_period", 12))
            self.slow_period = int(config.get("slow_period", 26))
            self.source      = str(config.get("source", "CLOSE")).upper()
        except (TypeError, ValueError) as exc:
            raise StrategyConfigError(f"EMA CrossOver: invalid config — {exc}") from exc

        if not (3 <= self.fast_period <= 50):
            raise StrategyConfigError("fast_period must be 3–50")
        if not (15 <= self.slow_period <= 200):
            raise StrategyConfigError("slow_period must be 15–200")
        if self.fast_period >= self.slow_period:
            raise StrategyConfigError("fast_period must be less than slow_period")
        if self.source not in ("CLOSE", "OPEN", "HL2"):
            raise StrategyConfigError("source must be CLOSE, OPEN, or HL2")

        self._prices: deque[float] = deque(maxlen=self.slow_period * 3)
        self._prev_fast: float | None = None
        self._prev_slow: float | None = None

    @property
    def min_bars_required(self) -> int:
        return self.slow_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        prices = _get_price_series(df, self.source)
        df["ema_fast"] = prices.ewm(span=self.fast_period, adjust=False).mean()
        df["ema_slow"] = prices.ewm(span=self.slow_period, adjust=False).mean()

        bullish = (df["ema_fast"] > df["ema_slow"]) & \
                  (df["ema_fast"].shift(1) <= df["ema_slow"].shift(1))
        bearish = (df["ema_fast"] < df["ema_slow"]) & \
                  (df["ema_fast"].shift(1) >= df["ema_slow"].shift(1))

        df["signal"] = np.where(bullish, SIGNAL_BUY,
                       np.where(bearish, SIGNAL_SELL, SIGNAL_HOLD))
        df.loc[df.index[: self.slow_period], "signal"] = SIGNAL_HOLD
        return df

    def evaluate_tick(self, tick: Dict[str, float], position: int) -> int:
        self._prices.append(_get_tick_price(tick, self.source))
        if len(self._prices) < self.slow_period:
            return SIGNAL_HOLD

        pl = list(self._prices)
        fast = _calc_ema(pl[-self.fast_period * 2:], self.fast_period)
        slow = _calc_ema(pl, self.slow_period)

        signal = SIGNAL_HOLD
        if self._prev_fast is not None:
            if fast > slow and self._prev_fast <= self._prev_slow:
                signal = SIGNAL_BUY
            elif fast < slow and self._prev_fast >= self._prev_slow:
                signal = SIGNAL_SELL

        self._prev_fast = fast
        self._prev_slow = slow
        return signal