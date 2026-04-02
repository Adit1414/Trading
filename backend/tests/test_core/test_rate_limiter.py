import pytest
from app.core.rate_limiter import limiter, BACKTEST_LIMIT
from app.core.config import settings

def test_rate_limiter_configured():
    assert limiter is not None
    assert BACKTEST_LIMIT == f"{settings.BACKTEST_RATE_LIMIT}/minute"
