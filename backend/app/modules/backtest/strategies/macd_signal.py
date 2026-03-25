"""
app/modules/backtest/strategies/macd_signal.py
────────────────────────────────────────────────
MACD Signal Strategy — Binance Cryptocurrency

Parameters (xlsx: MACD Signal):
  fast_period   : 6–30,  default 12
  slow_period   : 15–50, default 26
  signal_period : 5–15,  default 9
  source        : CLOSE | OPEN | HL2
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


class MACDSignalStrategy(BaseStrategy):
    display_name = "MACD Signal"
    strategy_id  = "MACD_SIGNAL"
    description  = (
        "Buys when the MACD line crosses above the signal line (bullish momentum) "
        "and sells on the reverse crossover."
    )

    def _validate_config(self, config: Dict[str, Any]) -> None:
        try:
            self.fast_period   = int(config.get("fast_period",   12))
            self.slow_period   = int(config.get("slow_period",   26))
            self.signal_period = int(config.get("signal_period",  9))
            self.source        = str(config.get("source",    "CLOSE")).upper()
        except (TypeError, ValueError) as exc:
            raise StrategyConfigError(f"MACD Signal: invalid config — {exc}") from exc

        if not (6 <= self.fast_period <= 30):
            raise StrategyConfigError("fast_period must be 6–30")
        if not (15 <= self.slow_period <= 50):
            raise StrategyConfigError("slow_period must be 15–50")
        if not (5 <= self.signal_period <= 15):
            raise StrategyConfigError("signal_period must be 5–15")
        if self.fast_period >= self.slow_period:
            raise StrategyConfigError("fast_period must be less than slow_period")
        if self.source not in ("CLOSE", "OPEN", "HL2"):
            raise StrategyConfigError("source must be CLOSE, OPEN or HL2")

        self._prices: deque[float] = deque(maxlen=self.slow_period * 3)
        self._prev_macd:   float | None = None
        self._prev_signal: float | None = None

    @property
    def min_bars_required(self) -> int:
        return self.slow_period + self.signal_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        prices = _get_price_series(df, self.source)
        df["macd_fast"]   = prices.ewm(span=self.fast_period,   adjust=False).mean()
        df["macd_slow"]   = prices.ewm(span=self.slow_period,   adjust=False).mean()
        df["macd_line"]   = df["macd_fast"] - df["macd_slow"]
        df["macd_signal"] = df["macd_line"].ewm(span=self.signal_period, adjust=False).mean()
        df["macd_hist"]   = df["macd_line"] - df["macd_signal"]

        buy_sig  = (df["macd_line"] > df["macd_signal"]) & \
                   (df["macd_line"].shift(1) <= df["macd_signal"].shift(1))
        sell_sig = (df["macd_line"] < df["macd_signal"]) & \
                   (df["macd_line"].shift(1) >= df["macd_signal"].shift(1))

        df["signal"] = np.where(buy_sig, SIGNAL_BUY,
                       np.where(sell_sig, SIGNAL_SELL, SIGNAL_HOLD))
        df.loc[df.index[: self.slow_period + self.signal_period], "signal"] = SIGNAL_HOLD
        return df

    def evaluate_tick(self, tick: Dict[str, float], position: int) -> int:
        self._prices.append(_get_tick_price(tick, self.source))
        if len(self._prices) < self.slow_period + self.signal_period:
            return SIGNAL_HOLD
        pl = list(self._prices)
        ml, sl = _calc_macd(pl, self.fast_period, self.slow_period, self.signal_period)
        result = SIGNAL_HOLD
        if self._prev_macd is not None:
            if ml > sl and self._prev_macd <= self._prev_signal:
                result = SIGNAL_BUY
            elif ml < sl and self._prev_macd >= self._prev_signal:
                result = SIGNAL_SELL
        self._prev_macd, self._prev_signal = ml, sl
        return result


def _ema_list(prices, period):
    k = 2 / (period + 1); ema = [prices[0]]
    for p in prices[1:]: ema.append(p * k + ema[-1] * (1 - k))
    return ema

def _calc_macd(prices, fast, slow, signal):
    fe = _ema_list(prices, fast); se = _ema_list(prices, slow)
    macd = [f - s for f, s in zip(fe, se)]
    sig  = _ema_list(macd[slow - 1:], signal)
    return macd[-1], sig[-1]