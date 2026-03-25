"""
app/modules/backtest/strategies/bollinger_bands.py
────────────────────────────────────────────────────
Bollinger Bands Mean-Reversion Strategy — Binance Cryptocurrency

Parameters (xlsx: Bollinger Bands):
  period  : 10–50,   default 20
  std_dev : 0.5–3.0, default 2.0
  source  : CLOSE | OPEN | HL2
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


class BollingerBandsStrategy(BaseStrategy):
    display_name = "Bollinger Bands"
    strategy_id  = "BOLLINGER_BANDS"
    description  = (
        "Mean-reversion strategy. Buys when price crosses below the lower band "
        "(oversold) and sells when price crosses above the upper band (overbought)."
    )

    def _validate_config(self, config: Dict[str, Any]) -> None:
        try:
            self.period  = int(config.get("period", 20))
            self.std_dev = float(config.get("std_dev", 2.0))
            self.source  = str(config.get("source", "CLOSE")).upper()
        except (TypeError, ValueError) as exc:
            raise StrategyConfigError(f"Bollinger Bands: invalid config — {exc}") from exc

        if not (10 <= self.period <= 50):
            raise StrategyConfigError("period must be 10–50")
        if not (0.5 <= self.std_dev <= 3.0):
            raise StrategyConfigError("std_dev must be 0.5–3.0")
        if self.source not in ("CLOSE", "OPEN", "HL2"):
            raise StrategyConfigError("source must be CLOSE, OPEN or HL2")

        self._prices: deque[float] = deque(maxlen=self.period)
        self._prev_price: float | None = None
        self._prev_upper: float | None = None
        self._prev_lower: float | None = None

    @property
    def min_bars_required(self) -> int:
        return self.period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        prices = _get_price_series(df, self.source)
        df["bb_mid"]   = prices.rolling(self.period, min_periods=self.period).mean()
        df["bb_std"]   = prices.rolling(self.period, min_periods=self.period).std(ddof=1)
        df["bb_upper"] = df["bb_mid"] + self.std_dev * df["bb_std"]
        df["bb_lower"] = df["bb_mid"] - self.std_dev * df["bb_std"]

        buy_sig  = (prices < df["bb_lower"]) & (prices.shift(1) >= df["bb_lower"].shift(1))
        sell_sig = (prices > df["bb_upper"]) & (prices.shift(1) <= df["bb_upper"].shift(1))

        df["signal"] = np.where(buy_sig, SIGNAL_BUY,
                       np.where(sell_sig, SIGNAL_SELL, SIGNAL_HOLD))
        df.loc[df.index[: self.period], "signal"] = SIGNAL_HOLD
        return df

    def evaluate_tick(self, tick: Dict[str, float], position: int) -> int:
        price = _get_tick_price(tick, self.source)
        self._prices.append(price)
        if len(self._prices) < self.period:
            self._prev_price = price
            return SIGNAL_HOLD

        arr   = list(self._prices)
        mean  = np.mean(arr)
        std   = np.std(arr, ddof=1)
        upper = mean + self.std_dev * std
        lower = mean - self.std_dev * std

        signal = SIGNAL_HOLD
        if self._prev_price is not None and self._prev_upper is not None:
            if price < lower and self._prev_price >= self._prev_lower:
                signal = SIGNAL_BUY
            elif price > upper and self._prev_price <= self._prev_upper:
                signal = SIGNAL_SELL

        self._prev_price, self._prev_upper, self._prev_lower = price, upper, lower
        return signal