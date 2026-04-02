import pytest
from app.services.market_data.binance import BinanceClient

@pytest.mark.asyncio
async def test_binance_client_init():
    client = BinanceClient(use_testnet=True)
    assert client.base_url == "https://testnet.binance.vision"

@pytest.mark.asyncio
async def test_fetch_klines_mocked(mocker):
    client = BinanceClient(use_testnet=True)
    
    # Mock httpx response
    mock_response = mocker.AsyncMock()
    mock_response.json.return_value = [
        [1600000000000, "100", "110", "90", "105", "1000"],
        [1600000060000, "105", "115", "95", "110", "1200"]
    ]
    mock_response.raise_for_status = mocker.MagicMock()
    
    mocker.patch("httpx.AsyncClient.get", return_value=mock_response)
    
    klines = await client.fetch_klines("BTCUSDT", "1m", limit=2)
    assert len(klines) == 2
    assert getattr(klines[0], "open") == 100.0
    assert getattr(klines[0], "close") == 105.0
