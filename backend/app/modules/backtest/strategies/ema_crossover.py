"""
app/modules/backtest/strategies/ema_crossover.py
──────────────────────────────────────────────────
EMA CrossOver Strategy — Binance Cryptocurrency
"""

from __future__ import annotations

import pandas as pd
from backtesting.lib import crossover

from app.modules.backtest.strategies.base import BaseStrategy, StrategyConfigError


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


class EMACrossoverStrategy(BaseStrategy):
    display_name = "EMA CrossOver"
    strategy_id  = "EMA_CROSSOVER"

    fast_period = 12
    slow_period = 26
    source = "CLOSE"

    @classmethod
    def get_min_bars_required(cls) -> int:
        return cls.slow_period

    def init(self):
        if self.fast_period < 2:
            raise StrategyConfigError("fast_period must be >= 2")
        if self.slow_period <= self.fast_period:
            raise StrategyConfigError("slow_period must be > fast_period")

        prices = self.get_source_series()
        
        # We declare the indicators inside self.I
        # Name overriding is optional but useful for chart plotting
        self.ema_fast = self.I(_ema, prices, self.fast_period, name="EMA Fast", overlay=True, color="#f9a825")
        self.ema_slow = self.I(_ema, prices, self.slow_period, name="EMA Slow", overlay=True, color="#7c4dff")

    def next(self):
        # We process things bar-by-bar
        # self.data.index points to timestamp. Currently, len(self.data) grows each iter
        
        # Bullish signal
        if crossover(self.ema_fast, self.ema_slow):
            self.execute_buy()
            
        # Bearish signal
        elif crossover(self.ema_slow, self.ema_fast):
            self.execute_sell()