"""
app/modules/backtest/strategies/base.py
─────────────────────────────────────────
Base class for all backtesting.py strategies.
"""

from __future__ import annotations

from backtesting import Strategy


class StrategyConfigError(ValueError):
    """Raised when strategy parameters fail validation."""


class BaseStrategy(Strategy):
    """
    Base strategy for backtesting.py.
    """

    display_name: str = ""
    strategy_id: str = ""
    source: str = "CLOSE" # Default source

    @classmethod
    def get_min_bars_required(cls) -> int:
        """
        Minimum number of historical bars needed before a valid signal.
        """
        return 0

    def get_source_series(self):
        """
        Returns the pandas series corresponding to self.source
        """
        src = str(self.source).upper()
        if src == "CLOSE":
            return self.data.Close.s
        elif src == "OPEN":
            return self.data.Open.s
        elif src == "HL2":
            return (self.data.High.s + self.data.Low.s) / 2
        else:
            raise StrategyConfigError(f"Unknown source '{src}'. Must be CLOSE, OPEN or HL2.")

    def execute_buy(self):
        """Execute buy logic respecting percentage/USDT settings."""
        # Spot Market constraint: we do not buy if we are already in a long position
        # because the original logic ignores subsequent BUY signals.
        if self.position.is_long:
            return

        order_mode = getattr(self, "_order_size_mode", "PERCENT_EQUITY")
        
        if order_mode == "PERCENT_EQUITY":
            size_pct = getattr(self, "_order_size_pct", 100.0) / 100.0
            size = min(0.9999, size_pct)  # backtesting max is 0.9999
            self.buy(size=size)
        else:
            usdt_size = getattr(self, "_order_size_usdt", 1000.0)
            size_fraction = usdt_size / self.equity
            size = min(0.9999, size_fraction)
            self.buy(size=size)

    def execute_sell(self):
        """Execute sell logic respecting Spot market constraints."""
        # Spot Market constraint: we only sell if we have a position. 
        # We do NOT open SHORT positions.
        if self.position.is_long:
            self.position.close()
