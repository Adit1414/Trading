import pytest
import os
from app.modules.backtest.chart import get_chart_path, save_chart_html

def test_chart_path_resolution(tmp_path, mocker):
    mocker.patch("app.modules.backtest.chart.CHARTS_DIR", str(tmp_path))
    path = get_chart_path("bt-123")
    assert path is None  # Doesn't exist yet
    
    # Create mock file
    f = tmp_path / "bt-123.html"
    f.write_text("chart html")
    
    path_resolved = get_chart_path("bt-123")
    assert path_resolved == str(f)

def test_save_chart_html(tmp_path, mocker):
    mocker.patch("app.modules.backtest.chart.CHARTS_DIR", str(tmp_path))
    save_path = save_chart_html("bt-test", "<html>mock chart</html>")
    assert save_path.endswith("bt-test.html")
    with open(save_path, "r") as f:
        assert f.read() == "<html>mock chart</html>"
