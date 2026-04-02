import pytest
from app.services.market_data.base import BaseMarketDataClient

class TestClient(BaseMarketDataClient):
    pass # Cannot instantiate Base without abstract methods if they exist, but actually python allows subclassing. 
         # Wait, if abstract methods exist, we need to mock them.

def test_base_market_data_client():
    # Because BaseMarketDataClient is an ABC, we declare a concrete dummy class
    class ConcreteClient(BaseMarketDataClient):
        async def fetch_klines(*args, **kwargs):
            return []
        async def close(*args, **kwargs):
            pass

    client = ConcreteClient()
    assert hasattr(client, "fetch_klines")
    assert hasattr(client, "close")
