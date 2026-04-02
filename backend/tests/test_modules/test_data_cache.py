import pytest
from app.modules.backtest.data_cache import cache_stats, get_cached_klines, set_cached_klines

def test_cache_stats():
    stats = cache_stats()
    assert "hits" in stats
    assert "misses" in stats
    assert "currsize" in stats
    assert "maxsize" in stats

def test_cache_klines():
    set_cached_klines("BTCUSDT", "1d", [1, 2, 3])
    klines = get_cached_klines("BTCUSDT", "1d")
    assert klines == [1, 2, 3]

def test_cache_miss():
    klines = get_cached_klines("UNKNOWN", "1m")
    assert klines is None
