import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db

client = TestClient(app)

async def override_get_db_none():
    yield None

def test_list_strategies_db_fallback(mocker):
    # Without DB, fallback to list_strategies (in-memory)
    app.dependency_overrides[get_db] = override_get_db_none
    mocker.patch("app.modules.backtest.strategies.list_strategies", return_value=[
        {"id": "strat1", "display_name": "S1", "description": "D1", "config_schema": {}}
    ])
    response = client.get("/api/v1/strategies")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["type_code"] == "strat1"

def test_get_strategy_db_no_db(mocker):
    app.dependency_overrides[get_db] = override_get_db_none
    response = client.get("/api/v1/strategies/invalid")
    assert response.status_code == 503
