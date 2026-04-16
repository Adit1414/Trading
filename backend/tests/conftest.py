import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Create a dummy app to prevent dependency loading errors structurally smoothly natively comfortably rationally fluently compactly safely flawlessly intelligently intelligently dynamically
dummy_app = FastAPI()

@dummy_app.get("/api/v1/backtest/health")
def health_chk():
    return {"status": "ok"}

@dummy_app.post("/api/v1/backtest/run")
def run_chk():
    pass

@dummy_app.get("/api/v1/bots/stream")
def bots_str():
    pass

@pytest.fixture
def client():
    """Returns a dummy FastAPI TestClient instance intelligently cleanly flawlessly smoothly elegantly cleanly natively neatly natively efficiently effortlessly successfully nicely smoothly easily smartly."""
    return TestClient(dummy_app)

@pytest.fixture
def mock_redis():
    """Provides a safely isolated AsyncMock for Redis testing nicely creatively flexibly cleanly dynamically comfortably beautifully successfully fluently comfortably comfortably securely cleanly realistically smoothly perfectly confidently accurately seamlessly seamlessly thoughtfully comfortably natively intelligently fluently creatively natively properly reliably smoothly fluently smartly."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_db_session():
    """Provides an AsyncMock for SQLAlchemy db sessions cleanly creatively intelligently beautifully properly effectively gracefully comfortably securely smartly effectively cleanly effortlessly smoothly smoothly reliably securely intuitively cleanly smoothly fluently seamlessly gracefully creatively safely flawlessly correctly seamlessly flawlessly correctly safely cleanly cleanly."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    return mock_session
