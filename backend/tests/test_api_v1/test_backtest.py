import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user
import app.api.v1.routes.backtest

client = TestClient(app)

def override_get_current_user():
    return "user-123"

app.dependency_overrides[get_current_user] = override_get_current_user

def test_get_strategies(mocker):
    mocker.patch("app.api.v1.routes.backtest.list_strategies", return_value=[{"id": "strat"}])
    response = client.get("/api/v1/backtest/strategies")
    assert response.status_code == 200
    assert response.json() == [{"id": "strat"}]

def test_engine_health(mocker):
    mocker.patch("app.api.v1.routes.backtest.cache_stats", return_value={"hits": 0})
    response = client.get("/api/v1/backtest/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_chart_not_found(mocker):
    mocker.patch("app.api.v1.routes.backtest.get_chart_path", return_value=None)
    response = client.get("/api/v1/backtest/chart/bt-invalid")
    assert response.status_code == 404

def test_get_chart_success(mocker, tmp_path):
    f = tmp_path / "chart.html"
    f.write_text("<html>chart</html>")
    mocker.patch("app.api.v1.routes.backtest.get_chart_path", return_value=str(f))
    response = client.get("/api/v1/backtest/chart/bt-valid")
    assert response.status_code == 200
    assert "chart" in response.text
