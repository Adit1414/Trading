"""
app/modules/backtest/strategies/rsi_divergence.py
───────────────────────────────────────────────────
RSI Divergence Strategy — Binance Cryptocurrency
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from app.modules.backtest.strategies.base import BaseStrategy, StrategyConfigError


def _calc_rsi_series(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


class RSIDivergenceStrategy(BaseStrategy):
    display_name = "RSI Divergence"
    strategy_id  = "RSI_DIVERGENCE"

    period = 14
    overbought = 70.0
    oversold = 30.0
    source = "CLOSE"

    @classmethod
    def get_min_bars_required(cls) -> int:
        return cls.period + 1

    def init(self):
        if self.period < 2:
            raise StrategyConfigError("period must be >= 2")
        if not (0 < self.oversold < self.overbought < 100):
            raise StrategyConfigError("Must satisfy 0 < oversold < overbought < 100")

        prices = self.get_source_series()

        self.rsi = self.I(_calc_rsi_series, prices, self.period, name="RSI", overlay=False, color="#e040fb")

    def next(self):
        # Buy when RSI crosses UP through oversold threshold
        if len(self.data) > 1 and self.rsi[-2] <= self.oversold and self.rsi[-1] > self.oversold:
            self.execute_buy()
            
        # Sell when RSI crosses DOWN through overbought threshold
        elif len(self.data) > 1 and self.rsi[-2] >= self.overbought and self.rsi[-1] < self.overbought:
            self.execute_sell()