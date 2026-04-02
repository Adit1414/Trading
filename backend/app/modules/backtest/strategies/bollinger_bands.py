"""
app/modules/backtest/strategies/bollinger_bands.py
────────────────────────────────────────────────────
Bollinger Bands Mean-Reversion Strategy — Binance Cryptocurrency
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from backtesting.lib import crossover

from app.modules.backtest.strategies.base import BaseStrategy, StrategyConfigError


def _bb_mid(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()

def _bb_upper(series: pd.Series, period: int, std_dev: float) -> pd.Series:
    mid = _bb_mid(series, period)
    std = series.rolling(period, min_periods=period).std(ddof=1)
    return mid + std_dev * std

def _bb_lower(series: pd.Series, period: int, std_dev: float) -> pd.Series:
    mid = _bb_mid(series, period)
    std = series.rolling(period, min_periods=period).std(ddof=1)
    return mid - std_dev * std


class BollingerBandsStrategy(BaseStrategy):
    display_name = "Bollinger Bands"
    strategy_id  = "BOLLINGER_BANDS"

    period = 20
    std_dev = 2.0
    source = "CLOSE"

    @classmethod
    def get_min_bars_required(cls) -> int:
        return cls.period

    def init(self):
        if self.period < 2:
            raise StrategyConfigError("period must be >= 2")
        if self.std_dev <= 0:
            raise StrategyConfigError("std_dev must be > 0")

        prices = self.get_source_series()

        self.bb_upper = self.I(_bb_upper, prices, self.period, self.std_dev, name="BB Upper", overlay=True, color="#ff9800", scatter=False)
        self.bb_mid   = self.I(_bb_mid,   prices, self.period, name="BB Mid", overlay=True, color="#9e9e9e", scatter=False)
        self.bb_lower = self.I(_bb_lower, prices, self.period, self.std_dev, name="BB Lower", overlay=True, color="#ff9800", scatter=False)
        
        # We want to access prices inside next as an array, backtesting passes self.data.Close inherently 
        # so we will use the series values itself, but for signal we can keep it simple
        self.prices_arr = self.I(lambda s: s, prices, overlay=True, plot=False) # plot=False because price is already plotted

    def next(self):
        # Buy when price crosses below lower band
        if len(self.data) > 1 and self.prices_arr[-2] >= self.bb_lower[-2] and self.prices_arr[-1] < self.bb_lower[-1]:
            self.execute_buy()
            
        # Sell when price crosses above upper band
        elif len(self.data) > 1 and self.prices_arr[-2] <= self.bb_upper[-2] and self.prices_arr[-1] > self.bb_upper[-1]:
            self.execute_sell()