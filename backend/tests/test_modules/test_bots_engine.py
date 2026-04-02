import pytest

def test_bots_engine_import():
    import app.modules.bots.engine
    assert hasattr(app.modules.bots.engine, 'dispatch')
