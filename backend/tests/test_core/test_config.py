import pytest
from app.core.config import Settings

def test_settings_defaults():
    settings = Settings()
    assert settings.APP_NAME == "Algo Kaisen"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.BACKTEST_RATE_LIMIT == 10
    
def test_binance_history_url():
    settings = Settings(BINANCE_USE_TESTNET_FOR_HISTORY=False)
    assert settings.binance_history_base_url == settings.BINANCE_MAINNET_BASE_URL
    
    settings_testnet = Settings(BINANCE_USE_TESTNET_FOR_HISTORY=True)
    assert settings_testnet.binance_history_base_url == settings_testnet.BINANCE_TESTNET_BASE_URL

def test_cors_origins_parsing():
    settings = Settings(CORS_ORIGINS='["http://example.com"]')
    assert settings.CORS_ORIGINS == ["http://example.com"]
