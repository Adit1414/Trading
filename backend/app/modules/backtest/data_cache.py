"""
app/modules/backtest/data_cache.py
────────────────────────────────────
Historical Data Cacher — HLD §4.2

Wraps the market data provider with a TTLCache (LRU eviction) to prevent
rate-limit exhaustion on the Binance API.  The cache key is derived from
(market, symbol, interval, start_date, end_date) so identical backtests
hit the cache without a network round-trip.

Integration with Module 3 (Streamer):
  The streamer is responsible for *live* ticks; this cache covers only the
  historical / REST side used by the backtesting engine.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import date
from typing import List

from cachetools import TTLCache

from app.core.config import settings
from app.services.market_data import OHLCV, get_market_data_provider

logger = logging.getLogger(__name__)

# Shared in-process TTL LRU cache (thread-safe for read; asyncio-safe via lock)
_cache: TTLCache[str, List[OHLCV]] = TTLCache(
    maxsize=settings.HISTORICAL_CACHE_MAXSIZE,
    ttl=settings.HISTORICAL_CACHE_TTL,
)
_cache_lock = asyncio.Lock()


def _make_cache_key(
    market: str,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
) -> str:
    raw = f"{market}:{symbol.upper()}:{interval}:{start_date}:{end_date}"
    return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324 – not cryptographic


async def get_historical_data(
    market: str,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
) -> List[OHLCV]:
    """
    Return historical OHLCV bars, served from cache if available.

    Args:
        market:     Provider key, e.g. "BINANCE".
        symbol:     Asset symbol, e.g. "BTCUSDT".
        interval:   K-line interval string, e.g. "1d".
        start_date: Inclusive start date (UTC).
        end_date:   Inclusive end date (UTC).

    Returns:
        Time-ascending list of OHLCV bars.

    Raises:
        KeyError:   If *market* is not registered.
        httpx.*:    On unrecoverable network errors after retries.
    """
    key = _make_cache_key(market, symbol, interval, start_date, end_date)

    async with _cache_lock:
        if key in _cache:
            logger.debug("Cache HIT  – %s %s %s", symbol, interval, key[:8])
            return _cache[key]

    # Cache miss — fetch from provider (outside lock to allow concurrency)
    logger.debug("Cache MISS – %s %s %s", symbol, interval, key[:8])
    provider = get_market_data_provider(market)
    bars = await provider.fetch_klines(symbol, interval, start_date, end_date)

    async with _cache_lock:
        _cache[key] = bars

    return bars


def invalidate_cache(
    market: str,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
) -> bool:
    """Manually remove a specific entry from the cache. Returns True if removed."""
    key = _make_cache_key(market, symbol, interval, start_date, end_date)
    if key in _cache:
        del _cache[key]
        return True
    return False


def cache_stats() -> dict:
    """Return current cache utilisation metrics (for /health or admin endpoints)."""
    return {
        "current_size": len(_cache),
        "maxsize": _cache.maxsize,
        "ttl_seconds": _cache.ttl,
    }