"""
app/modules/backtest/strategies/rsi_divergence.py
───────────────────────────────────────────────────
RSI Divergence Strategy — Binance Cryptocurrency

Signal logic:
  BUY  when RSI crosses UP through oversold threshold.
  SELL when RSI crosses DOWN through overbought threshold.

Params: period (14), overbought (70), oversold (30), source (CLOSE|OPEN|HL2)
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

    def _validate_config(self, config: Dict[str, Any]) -> None:
        try:
            self.period     = int(config.get("period", 14))
            self.overbought = float(config.get("overbought", 70.0))
            self.oversold   = float(config.get("oversold", 30.0))
            self.source     = str(config.get("source", "CLOSE")).upper()
        except (TypeError, ValueError) as exc:
            raise StrategyConfigError(f"RSI Divergence: invalid config — {exc}") from exc

        if self.period < 2:
            raise StrategyConfigError("period must be ≥ 2")
        if not (0 < self.oversold < self.overbought < 100):
            raise StrategyConfigError("Must satisfy 0 < oversold < overbought < 100")
        if self.source not in ("CLOSE", "OPEN", "HL2"):
            raise StrategyConfigError("source must be CLOSE, OPEN or HL2")

        self._prices: deque[float] = deque(maxlen=self.period + 2)
        self._prev_rsi: float | None = None

    @property
    def min_bars_required(self) -> int:
        return self.period + 1

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        prices = _get_price_series(df, self.source)

        delta = prices.diff()
        gain  = delta.clip(lower=0).rolling(self.period, min_periods=self.period).mean()
        loss  = (-delta.clip(upper=0)).rolling(self.period, min_periods=self.period).mean()
        rs    = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))

        prev_rsi = df["rsi"].shift(1)
        buy_sig  = (df["rsi"] > self.oversold)   & (prev_rsi <= self.oversold)
        sell_sig = (df["rsi"] < self.overbought)  & (prev_rsi >= self.overbought)

        df["signal"] = np.where(buy_sig, SIGNAL_BUY,
                       np.where(sell_sig, SIGNAL_SELL, SIGNAL_HOLD))
        df.loc[df.index[: self.period + 1], "signal"] = SIGNAL_HOLD
        return df

    def evaluate_tick(self, tick: Dict[str, float], position: int) -> int:
        self._prices.append(_get_tick_price(tick, self.source))
        if len(self._prices) < self.period + 1:
            return SIGNAL_HOLD
        rsi = _calc_rsi(list(self._prices), self.period)
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