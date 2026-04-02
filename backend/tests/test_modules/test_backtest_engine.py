import pytest

def test_backtest_engine_import():
    import app.modules.backtest.engine
    assert hasattr(app.modules.backtest.engine, 'run_backtest')
