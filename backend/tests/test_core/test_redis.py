import pytest
from app.core.redis import _build_client, close_redis
import app.core.redis as redis_mod

def test_build_client_no_url(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.REDIS_URL", None)
    client = _build_client()
    assert client is None

def test_build_client_with_url(monkeypatch, mocker):
    monkeypatch.setattr("app.core.config.settings.REDIS_URL", "redis://localhost")
    if redis_mod._REDIS_AVAILABLE:
        mock_from_url = mocker.patch("redis.asyncio.from_url")
        client = _build_client()
        mock_from_url.assert_called_once_with(
            "redis://localhost",
            encoding="utf-8",
            decode_responses=True
        )

@pytest.mark.asyncio
async def test_close_redis(mocker):
    redis_mod._client = mocker.AsyncMock()
    await close_redis()
    assert redis_mod._client is None
