"""
app/modules/backtest/strategies/macd_signal.py
────────────────────────────────────────────────
MACD Signal Strategy — Binance Cryptocurrency

Signal logic:
  BUY  when MACD line crosses ABOVE signal line.
  SELL when MACD line crosses BELOW signal line.

Params: fast_period (12), slow_period (26), signal_period (9), source (CLOSE|OPEN|HL2)
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

    def _validate_config(self, config: Dict[str, Any]) -> None:
        try:
            self.fast_period   = int(config.get("fast_period",   12))
            self.slow_period   = int(config.get("slow_period",   26))
            self.signal_period = int(config.get("signal_period",  9))
            self.source        = str(config.get("source",    "CLOSE")).upper()
        except (TypeError, ValueError) as exc:
            raise StrategyConfigError(f"MACD Signal: invalid config — {exc}") from exc

        if self.fast_period < 2:
            raise StrategyConfigError("fast_period must be ≥ 2")
        if self.slow_period <= self.fast_period:
            raise StrategyConfigError("slow_period must be > fast_period")
        if self.signal_period < 2:
            raise StrategyConfigError("signal_period must be ≥ 2")
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

        prev_macd   = df["macd_line"].shift(1)
        prev_signal = df["macd_signal"].shift(1)

        buy_sig  = (df["macd_line"] > df["macd_signal"]) & (prev_macd <= prev_signal)
        sell_sig = (df["macd_line"] < df["macd_signal"]) & (prev_macd >= prev_signal)

        df["signal"] = np.where(buy_sig, SIGNAL_BUY,
                       np.where(sell_sig, SIGNAL_SELL, SIGNAL_HOLD))
        warmup = self.slow_period + self.signal_period
        df.loc[df.index[:warmup], "signal"] = SIGNAL_HOLD
        return df

    def evaluate_tick(self, tick: Dict[str, float], position: int) -> int:
        self._prices.append(_get_tick_price(tick, self.source))
        if len(self._prices) < self.slow_period + self.signal_period:
            return SIGNAL_HOLD

        prices = list(self._prices)
        macd_line, signal_line = _calc_macd(
            prices, self.fast_period, self.slow_period, self.signal_period
        )
        result = SIGNAL_HOLD
        if self._prev_macd is not None:
            if macd_line > signal_line and self._prev_macd <= self._prev_signal:
                result = SIGNAL_BUY
            elif macd_line < signal_line and self._prev_macd >= self._prev_signal:
                result = SIGNAL_SELL
        self._prev_macd   = macd_line
        self._prev_signal = signal_line
        return result


def _ema_list(prices: list[float], period: int) -> list[float]:
    k   = 2 / (period + 1)
    ema = [prices[0]]
    for p in prices[1:]:
        ema.append(p * k + ema[-1] * (1 - k))
    return ema


def _calc_macd(prices, fast, slow, signal):
    fast_ema = _ema_list(prices, fast)
    slow_ema = _ema_list(prices, slow)
    macd     = [f - s for f, s in zip(fast_ema, slow_ema)]
    sig_ema  = _ema_list(macd[slow - 1:], signal)
    return macd[-1], sig_ema[-1]