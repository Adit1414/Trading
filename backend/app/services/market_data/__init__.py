"""
app/services/market_data/__init__.py
──────────────────────────────────────
Market data provider factory.

Currently supported: BINANCE only (SRS §1.2 — Out of Scope: other brokers).
To add a new broker (SRS §1.4 Future Scope):
  1. Subclass MarketDataProvider in a new file.
  2. Register it in _PROVIDER_REGISTRY below.
  3. Add its key to the TradingMarket enum in app/schemas/backtest.py.
"""

from app.services.market_data.base import OHLCV, MarketDataProvider
from app.services.market_data.binance import BinanceMarketData

_PROVIDER_REGISTRY: dict[str, type[MarketDataProvider]] = {
    "BINANCE": BinanceMarketData,
    # "NSE":  UpstoxMarketData,   # Future – SRS §1.4
    # "BSE":  DhanMarketData,     # Future – SRS §1.4
}


def get_market_data_provider(market: str) -> MarketDataProvider:
    """
    Return a MarketDataProvider instance for *market*.
    Raises KeyError for unsupported markets.
    """
    cls = _PROVIDER_REGISTRY.get(market.upper())
    if cls is None:
        raise KeyError(
            f"Market '{market}' is not supported. "
            f"Supported markets: {list(_PROVIDER_REGISTRY)}"
        )
    return cls()


__all__ = [
    "OHLCV",
    "MarketDataProvider",
    "BinanceMarketData",
    "get_market_data_provider",
]