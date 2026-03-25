"""
app/services/market_data/base.py
─────────────────────────────────
Abstract interface for market data providers.

Adding a new broker (e.g. Upstox, Dhan – SRS §1.4 Future Scope) requires only:
  1. Subclassing MarketDataProvider
  2. Registering it in app/services/market_data/__init__.py

The backtesting engine (Module 2) and the future streaming module (Module 3)
both depend on this interface, not on a concrete implementation.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class OHLCV:
    """A single candlestick / K-line bar."""
    timestamp: str     # ISO-8601 UTC string
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataProvider(abc.ABC):
    """
    Abstract market data provider.

    Implementations:
      - BinanceMarketData  (current)
      - UpstoxMarketData   (future)
    """

    @abc.abstractmethod
    async def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_date: date,
        end_date: date,
    ) -> List[OHLCV]:
        """
        Fetch historical OHLCV bars for *symbol* in *interval* granularity
        from *start_date* to *end_date* (inclusive, UTC).

        Returns a time-ascending list of OHLCV objects.
        Implementations MUST handle pagination internally.
        """

    @abc.abstractmethod
    async def validate_symbol(self, symbol: str) -> bool:
        """Return True if *symbol* is recognised by this provider."""