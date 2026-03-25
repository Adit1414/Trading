"""
app/modules/backtest/strategies/base.py
─────────────────────────────────────────
Abstract base class for all trading strategies.

Design Goals (HLD §4.2 & §4.4):
  • generate_signals()  – vectorised, used exclusively by Module 2 (Backtesting).
  • evaluate_tick()     – single-bar evaluation, used by Module 4 (Bot Execution &
                          State Manager) for live / paper trading.

Adding a new strategy:
  1. Subclass BaseStrategy.
  2. Implement generate_signals() and evaluate_tick().
  3. Register in app/modules/backtest/strategies/__init__.py.
"""

from __future__ import annotations

import abc
from typing import Any, Dict

import pandas as pd

# Signal constants (used throughout the engine and strategies)
SIGNAL_BUY = 1
SIGNAL_SELL = -1
SIGNAL_HOLD = 0


class StrategyConfigError(ValueError):
    """Raised when strategy parameters fail validation."""


class BaseStrategy(abc.ABC):
    """
    Abstract strategy contract.

    Subclasses receive raw config dicts and must validate them in __init__.
    """

    #: Human-readable name shown in the UI
    display_name: str = ""
    #: Strategy identifier matching StrategyName enum
    strategy_id: str = ""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self._validate_config(config)

    @abc.abstractmethod
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate and normalise config dict.
        Raise StrategyConfigError on invalid parameters.
        Store validated parameters as instance attributes.
        """

    @abc.abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Vectorised signal generation for backtesting (Module 2).

        Args:
            df: DataFrame with columns [open, high, low, close, volume]
                indexed by a DatetimeIndex (UTC).

        Returns:
            The same DataFrame with an additional integer column 'signal'
            where:
                 1  = BUY  (enter long)
                -1  = SELL (exit / enter short if strategy supports it)
                 0  = HOLD (no action)

        Contract:
            • Must NOT introduce look-ahead bias (signals are based solely
              on data up to and including the current row).
            • Signals for the first N rows (where N = warm-up period) should
              be 0 to avoid acting on incomplete indicators.
        """

    @abc.abstractmethod
    def evaluate_tick(
        self,
        tick: Dict[str, float],
        position: int,
    ) -> int:
        """
        Single-tick evaluation for Module 4 (Bot Execution).

        Args:
            tick:     Latest OHLCV as a plain dict
                      {'open', 'high', 'low', 'close', 'volume'}.
            position: Current bot position: 0 = flat, 1 = long.

        Returns:
            SIGNAL_BUY / SIGNAL_SELL / SIGNAL_HOLD

        Note:
            Stateful strategies must maintain their own internal history
            (e.g. a deque of recent closes) between tick calls.
        """

    @property
    def min_bars_required(self) -> int:
        """
        Minimum number of historical bars needed before a valid signal
        can be generated (warm-up period).  Returned as metadata.
        """
        return 0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(config={self.config!r})"
