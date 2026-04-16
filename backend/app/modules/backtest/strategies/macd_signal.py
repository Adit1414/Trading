"""
app/modules/backtest/strategies/macd_signal.py
────────────────────────────────────────────────
MACD Signal Strategy — Binance Cryptocurrency
"""

from __future__ import annotations

import pandas as pd
from backtesting.lib import crossover

from app.modules.backtest.strategies.base import BaseStrategy, StrategyConfigError


def _macd_line(series: pd.Series, fast: int, slow: int) -> pd.Series:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    return ema_fast - ema_slow

def _macd_signal(series: pd.Series, fast: int, slow: int, signal: int) -> pd.Series:
    macd_l = _macd_line(series, fast, slow)
    return macd_l.ewm(span=signal, adjust=False).mean()


class MACDSignalStrategy(BaseStrategy):
    display_name = "MACD Signal"
    strategy_id  = "MACD_SIGNAL"

    fast_period = 12
    slow_period = 26
    signal_period = 9
    source = "CLOSE"

    @classmethod
    def get_min_bars_required(cls) -> int:
        return cls.slow_period + cls.signal_period

    def init(self):
        if self.fast_period < 2:
            raise StrategyConfigError("fast_period must be >= 2")
        if self.slow_period <= self.fast_period:
            raise StrategyConfigError("slow_period must be > fast_period")
        if self.signal_period < 2:
            raise StrategyConfigError("signal_period must be >= 2")

        prices = self.get_source_series()

        self.macd = self.I(_macd_line, prices, self.fast_period, self.slow_period, name="MACD Line", overlay=False, color="#00bcd4")
        self.signal_line = self.I(_macd_signal, prices, self.fast_period, self.slow_period, self.signal_period, name="Signal Line", overlay=False, color="#ff9800")
        
    def next(self):
        if crossover(self.macd, self.signal_line):
            self.execute_buy()
        elif crossover(self.signal_line, self.macd):
            self.execute_sell()