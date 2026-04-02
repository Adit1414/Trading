import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user
from app.db.session import get_db

client = TestClient(app)

def override_get_current_user():
    return "user-123"

class MockSession:
    pass

async def override_get_db():
    yield MockSession()

app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_db] = override_get_db

def test_list_backtests(mocker):
    mocker.patch("app.api.v1.routes.backtest_db.list_backtests_for_user", return_value=[])
    response = client.get("/api/v1/backtests")
    assert response.status_code == 200
    assert response.json() == []

def test_get_one_backtest_not_found(mocker):
    mocker.patch("app.api.v1.routes.backtest_db.get_backtest", return_value=None)
    response = client.get("/api/v1/backtests/invalid")
    assert response.status_code == 404

def test_delete_one_backtest_not_found(mocker):
    mocker.patch("app.api.v1.routes.backtest_db.delete_backtest", return_value=False)
    response = client.delete("/api/v1/backtests/invalid")
    assert response.status_code == 404

def test_delete_one_backtest_success(mocker):
    mocker.patch("app.api.v1.routes.backtest_db.delete_backtest", return_value=True)
    mocker.patch("app.api.v1.routes.backtest_db.get_chart_path", return_value=None)
    response = client.delete("/api/v1/backtests/valid")
    assert response.status_code == 204
