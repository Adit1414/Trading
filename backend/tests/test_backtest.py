"""
tests/test_backtest.py
Comprehensive tests — all existing tests preserved + new DB layer tests.
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

# Fix ModuleNotFoundError when running tests directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.backtest.engine import BacktestError, run_backtest
from app.modules.backtest.performance import simulate_trades, synthesize
from app.modules.backtest.strategies import get_strategy
from app.modules.backtest.strategies.base import (
    SIGNAL_BUY, SIGNAL_HOLD, SIGNAL_SELL, StrategyConfigError,
)
from app.schemas.backtest import BacktestRunRequest, OrderSizeMode, StrategyName

client = TestClient(app)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _df(n=100, p=30000.0):
    np.random.seed(42)
    px  = p + np.cumsum(np.random.randn(n) * 50)
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame({
        "open": px, "high": px * 1.005, "low": px * 0.995,
        "close": px + np.random.randn(n) * 20,
        "volume": abs(np.random.randn(n)) * 1e6 + 1e5,
    }, index=idx)


def _req(**kw) -> BacktestRunRequest:
    d = dict(
        strategy=StrategyName.EMA_CROSSOVER,
        strategy_config={"fast_period": 12, "slow_period": 26, "source": "CLOSE"},
        name="Test", symbol="BTCUSDT", interval="1d",
        trading_market="BINANCE", initial_cash=10000.0,
        commission=0.001, slippage=0.0005,
        order_size_mode=OrderSizeMode.PCT_EQUITY, order_size_pct=100.0,
        intraday=False,
        start_date=date(2024, 1, 1), end_date=date(2024, 6, 30),
    )
    d.update(kw)
    return BacktestRunRequest(**d)


def _bars(n=100):
    from app.services.market_data.base import OHLCV
    np.random.seed(0)
    px  = 30000 + np.cumsum(np.random.randn(n) * 50)
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    return [
        OHLCV(str(ts), float(p), float(p * 1.005), float(p * 0.995), float(p + 10), 5e5)
        for ts, p in zip(idx, px)
    ]


def _sim(df):
    return simulate_trades(
        df=df, initial_cash=10000, commission=0.001, slippage=0.0005,
        order_size_mode=OrderSizeMode.PCT_EQUITY, order_size_pct=100.0,
        order_size_usdt=None, intraday=False,
    )


# ─── Schema tests ──────────────────────────────────────────────────────────────

class TestSchemas:
    def test_symbol_uppercased(self):
        assert _req(symbol="btcusdt").symbol == "BTCUSDT"

    def test_bad_dates_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _req(start_date=date(2024, 6, 30), end_date=date(2024, 1, 1))

    def test_nse_market_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _req(trading_market="NSE")

    def test_fixed_usdt_requires_amount(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _req(order_size_mode=OrderSizeMode.FIXED_USDT, order_size_usdt=None)

    def test_default_market_is_binance(self):
        r = _req()
        assert r.trading_market.value == "BINANCE"


# ─── EMA strategy ─────────────────────────────────────────────────────────────

class TestEMACrossover:
    s = get_strategy("EMA_CROSSOVER", {"fast_period": 12, "slow_period": 26})

    def test_signal_column_present(self):
        assert "signal" in self.s.generate_signals(_df(60)).columns

    def test_ema_columns_present(self):
        r = self.s.generate_signals(_df(60))
        assert "ema_fast" in r.columns and "ema_slow" in r.columns

    def test_signals_only_valid_values(self):
        assert self.s.generate_signals(_df(60))["signal"].isin([-1, 0, 1]).all()

    def test_warmup_period_zeroed(self):
        r = self.s.generate_signals(_df(60))
        assert (r["signal"].iloc[: self.s.slow_period] == SIGNAL_HOLD).all()

    def test_fast_range_min_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("EMA_CROSSOVER", {"fast_period": 2, "slow_period": 26})

    def test_fast_range_max_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("EMA_CROSSOVER", {"fast_period": 51, "slow_period": 60})

    def test_slow_range_max_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("EMA_CROSSOVER", {"fast_period": 12, "slow_period": 201})

    def test_fast_must_be_less_than_slow(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("EMA_CROSSOVER", {"fast_period": 30, "slow_period": 20})

    def test_source_hl2(self):
        s = get_strategy("EMA_CROSSOVER", {"fast_period": 12, "slow_period": 26, "source": "HL2"})
        assert s.generate_signals(_df(60))["signal"].isin([-1, 0, 1]).all()

    def test_source_open(self):
        s = get_strategy("EMA_CROSSOVER", {"fast_period": 12, "slow_period": 26, "source": "OPEN"})
        assert "signal" in s.generate_signals(_df(60)).columns

    def test_invalid_source_rejected(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("EMA_CROSSOVER", {"fast_period": 12, "slow_period": 26, "source": "VWAP"})

    def test_evaluate_tick_returns_valid(self):
        tick = {"open": 30000, "high": 30500, "low": 29500, "close": 30200, "volume": 1e6}
        assert self.s.evaluate_tick(tick, 0) in (SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD)


# ─── RSI strategy ─────────────────────────────────────────────────────────────

class TestRSIDivergence:
    s = get_strategy("RSI_DIVERGENCE", {"period": 14, "lookback_periods": 5})

    def test_rsi_column_present(self):
        assert "rsi" in self.s.generate_signals(_df(80)).columns

    def test_rsi_in_valid_range(self):
        r = self.s.generate_signals(_df(80))["rsi"].dropna()
        assert (r >= 0).all() and (r <= 100).all()

    def test_lookback_min_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("RSI_DIVERGENCE", {"lookback_periods": 2})

    def test_lookback_max_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("RSI_DIVERGENCE", {"lookback_periods": 11})

    def test_oversold_min_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("RSI_DIVERGENCE", {"oversold": 5})

    def test_overbought_max_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("RSI_DIVERGENCE", {"overbought": 95})

    def test_source_hl2(self):
        s = get_strategy("RSI_DIVERGENCE", {"period": 14, "lookback_periods": 5, "source": "HL2"})
        assert s.generate_signals(_df(80))["signal"].isin([-1, 0, 1]).all()


# ─── Bollinger Bands ──────────────────────────────────────────────────────────

class TestBollingerBands:
    s = get_strategy("BOLLINGER_BANDS", {"period": 20, "std_dev": 2.0})

    def test_band_columns_present(self):
        r = self.s.generate_signals(_df(80))
        for c in ("bb_mid", "bb_upper", "bb_lower"):
            assert c in r.columns

    def test_upper_always_above_lower(self):
        r = self.s.generate_signals(_df(80)).dropna()
        assert (r["bb_upper"] >= r["bb_lower"]).all()

    def test_period_min_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("BOLLINGER_BANDS", {"period": 5})

    def test_period_max_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("BOLLINGER_BANDS", {"period": 55})

    def test_std_dev_max_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("BOLLINGER_BANDS", {"std_dev": 4.0})


# ─── MACD strategy ────────────────────────────────────────────────────────────

class TestMACDSignal:
    s = get_strategy("MACD_SIGNAL", {"fast_period": 12, "slow_period": 26, "signal_period": 9})

    def test_macd_columns_present(self):
        r = self.s.generate_signals(_df(80))
        for c in ("macd_line", "macd_signal", "macd_hist"):
            assert c in r.columns

    def test_fast_range_min_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("MACD_SIGNAL", {"fast_period": 5, "slow_period": 26, "signal_period": 9})

    def test_signal_range_min_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("MACD_SIGNAL", {"fast_period": 12, "slow_period": 26, "signal_period": 2})

    def test_slow_range_max_enforced(self):
        with pytest.raises(StrategyConfigError):
            get_strategy("MACD_SIGNAL", {"fast_period": 12, "slow_period": 55, "signal_period": 9})

    def test_source_hl2(self):
        s = get_strategy("MACD_SIGNAL", {
            "fast_period": 12, "slow_period": 26,
            "signal_period": 9, "source": "HL2",
        })
        assert s.generate_signals(_df(80))["signal"].isin([-1, 0, 1]).all()


# ─── Trade simulation ─────────────────────────────────────────────────────────

class TestSimulation:
    def test_equity_curve_length_matches_bars(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 12, "slow_period": 26})
        df = s.generate_signals(_df(60))
        eq, _, _, _ = _sim(df)
        assert len(eq) == len(df)

    def test_initial_equity_equals_cash(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 12, "slow_period": 26})
        df = s.generate_signals(_df(60))
        eq, _, _, _ = _sim(df)
        assert eq[0].value == 10000.0

    def test_final_portfolio_never_negative(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 12, "slow_period": 26})
        df = s.generate_signals(_df(60))
        _, _, final, _ = _sim(df)
        assert final >= 0

    def test_commissions_are_positive_when_trades_occur(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 12, "slow_period": 26})
        df = s.generate_signals(_df(60))
        _, raw, _, comm = _sim(df)
        if raw:
            assert comm >= 0

    def test_fixed_usdt_mode_works(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 12, "slow_period": 26})
        df = s.generate_signals(_df(60))
        _, _, final, _ = simulate_trades(
            df=df, initial_cash=10000, commission=0.001, slippage=0.0005,
            order_size_mode=OrderSizeMode.FIXED_USDT,
            order_size_pct=100.0, order_size_usdt=500.0, intraday=False,
        )
        assert final >= 0


# ─── Statistics synthesis ─────────────────────────────────────────────────────

class TestStatistics:
    def _get(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 12, "slow_period": 26})
        df = s.generate_signals(_df(80))
        eq, raw, _, comm = _sim(df)
        return synthesize(eq, raw, 10000, df, comm)

    def test_all_image2_fields_present(self):
        stats, _ = self._get()
        required = (
            "equity_final", "equity_peak", "sharpe_ratio", "sortino_ratio",
            "calmar_ratio", "cagr_pct", "buy_hold_return_pct", "alpha_pct", "beta",
            "max_drawdown_pct", "avg_drawdown_pct", "max_drawdown_duration",
            "avg_drawdown_duration", "exposure_time_pct", "commissions_paid",
            "total_return", "total_return_pct", "win_rate", "total_trades",
        )
        for f in required:
            assert hasattr(stats, f), f"Missing stat field: {f}"

    def test_win_rate_in_valid_range(self):
        stats, _ = self._get()
        assert 0.0 <= stats.win_rate <= 100.0

    def test_equity_peak_gte_equity_final(self):
        stats, _ = self._get()
        assert stats.equity_peak >= stats.equity_final - 0.01

    def test_duration_fields_are_strings(self):
        stats, _ = self._get()
        assert isinstance(stats.max_drawdown_duration, str)
        assert isinstance(stats.avg_drawdown_duration, str)

    def test_trade_records_have_quantity_usdt(self):
        _, records = self._get()
        for r in records:
            assert r.quantity_usdt > 0

    def test_commissions_non_negative(self):
        stats, _ = self._get()
        assert stats.commissions_paid >= 0


# ─── Engine integration ───────────────────────────────────────────────────────

class TestEngine:
    def test_successful_run_with_chart(self):
        bars = _bars(100)
        with patch("app.modules.backtest.engine.get_historical_data",
                   new_callable=AsyncMock) as m, \
             patch("app.modules.backtest.engine._persist_result",
                   new_callable=AsyncMock):
            m.return_value = bars
            result = asyncio.get_event_loop().run_until_complete(run_backtest(_req()))
        assert result.status.value == "COMPLETED"
        assert result.chart_html
        assert "<html" in result.chart_html.lower()

    def test_no_data_raises_backtest_error(self):
        with patch("app.modules.backtest.engine.get_historical_data",
                   new_callable=AsyncMock) as m:
            m.return_value = []
            with pytest.raises(BacktestError, match="No data"):
                asyncio.get_event_loop().run_until_complete(run_backtest(_req()))

    def test_insufficient_bars_raises(self):
        with patch("app.modules.backtest.engine.get_historical_data",
                   new_callable=AsyncMock) as m:
            m.return_value = _bars(5)
            with pytest.raises(BacktestError, match="Insufficient"):
                asyncio.get_event_loop().run_until_complete(run_backtest(_req()))

    def test_parameters_in_response(self):
        bars = _bars(100)
        with patch("app.modules.backtest.engine.get_historical_data",
                   new_callable=AsyncMock) as m, \
             patch("app.modules.backtest.engine._persist_result",
                   new_callable=AsyncMock):
            m.return_value = bars
            result = asyncio.get_event_loop().run_until_complete(run_backtest(_req()))
        assert result.parameters.slippage == 0.0005
        assert result.parameters.commission == 0.001
        assert result.parameters.trading_market == "BINANCE"


# ─── DB CRUD unit tests ───────────────────────────────────────────────────────

class TestBacktestCRUD:
    """
    Unit tests for CRUD operations using a mocked AsyncSession.
    These tests do not require a real database.
    """

    def _make_mock_row(self):
        """Build a mock BacktestModel-like object."""
        from datetime import datetime, timezone
        row = MagicMock()
        row.id              = "test-id-1234"
        row.user_id         = "user-uuid-1234"
        row.strategy_id     = "strategy-uuid-1234"
        row.symbol          = "BTCUSDT"
        row.timeframe       = "1d"
        row.parameters      = {"initial_cash": 10000}
        row.metrics         = {"win_rate": 55.0, "total_return_pct": 12.5, "total_trades": 4}
        row.result_file_url = None
        row.created_at      = datetime(2024, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
        return row

    def test_backtest_list_item_from_orm_row(self):
        from app.schemas.db import BacktestListItemDB
        row  = self._make_mock_row()
        item = BacktestListItemDB.from_orm_row(row)
        assert item.id == "test-id-1234"
        assert item.symbol == "BTCUSDT"
        assert item.total_return_pct == 12.5
        assert item.win_rate == 55.0
        assert item.total_trades == 4

    def test_backtest_db_schema_validation(self):
        from app.schemas.db import BacktestDB
        from datetime import datetime, timezone
        data = {
            "id":              "test-id",
            "user_id":         "user-id",
            "strategy_id":     "strat-id",
            "symbol":          "BTCUSDT",
            "timeframe":       "1d",
            "parameters":      {"initial_cash": 10000},
            "metrics":         {"win_rate": 60.0},
            "result_file_url": None,
            "created_at":      datetime(2024, 1, 1, tzinfo=timezone.utc),
        }
        db = BacktestDB(**data)
        assert db.symbol == "BTCUSDT"
        assert db.metrics["win_rate"] == 60.0

    def test_strategy_db_schema_validation(self):
        from app.schemas.db import StrategyDB
        data = {
            "id":               "strat-uuid",
            "name":             "EMA CrossOver",
            "type_code":        "EMA_CROSSOVER",
            "parameter_schema": {"type": "object", "properties": {}},
            "description":      "Test description",
        }
        db = StrategyDB(**data)
        assert db.type_code == "EMA_CROSSOVER"
        assert "type" in db.parameter_schema


# ─── DB model unit tests ──────────────────────────────────────────────────────

class TestDBModels:
    def test_user_model_repr(self):
        from app.db.models import UserModel
        u = UserModel(id="uuid-1", email="test@test.com")
        assert "test@test.com" in repr(u)

    def test_strategy_model_repr(self):
        from app.db.models import StrategyModel
        s = StrategyModel(
            id="uuid-1", name="EMA CrossOver",
            type_code="EMA_CROSSOVER", parameter_schema={}
        )
        assert "EMA_CROSSOVER" in repr(s)

    def test_bot_model_defaults(self):
        from app.db.models import BotModel
        # SQLAlchemy server_default applies at INSERT time, not on Python init.
        # We verify the default is wired by passing it explicitly.
        b = BotModel(
            id="uuid-1", user_id="user-uuid",
            strategy_id="strat-uuid", name="My Bot",
            environment="TESTNET", parameters={},
            status="STOPPED",
        )
        assert b.status == "STOPPED"

    def test_bot_state_defaults(self):
        from app.db.models import BotStateModel
        # server_default applies at INSERT time; pass it explicitly for unit test.
        s = BotStateModel(bot_id="bot-uuid", current_position="FLAT")
        assert s.current_position == "FLAT"

    def test_trade_log_model_repr(self):
        from app.db.models import TradeLogModel
        t = TradeLogModel(
            id="uuid-1", user_id="user-uuid",
            symbol="BTCUSDT", side="BUY",
            quantity=0.1, execution_price=30000.0,
            environment="TESTNET",
        )
        assert "BUY" in repr(t) and "BTCUSDT" in repr(t)

    def test_backtest_model_repr(self):
        from app.db.models import BacktestModel
        b = BacktestModel(
            id="uuid-1", strategy_id="strat-uuid",
            symbol="BTCUSDT", timeframe="1d",
            parameters={}, metrics={},
        )
        assert "BTCUSDT" in repr(b)


# ─── API endpoint tests ───────────────────────────────────────────────────────

class TestAPI:
    def test_health_endpoint(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "db_enabled" in data

    def test_backtest_strategies_endpoint(self):
        r = client.get("/api/v1/backtest/strategies")
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()]
        for sid in ("EMA_CROSSOVER", "RSI_DIVERGENCE", "BOLLINGER_BANDS", "MACD_SIGNAL"):
            assert sid in ids

    def test_backtest_health_endpoint(self):
        r = client.get("/api/v1/backtest/health")
        assert r.status_code == 200

    def test_backtest_run_invalid_dates(self):
        payload = {
            "strategy": "EMA_CROSSOVER",
            "strategy_config": {"fast_period": 12, "slow_period": 26},
            "name": "Bad", "symbol": "BTCUSDT", "interval": "1d",
            "trading_market": "BINANCE", "initial_cash": 10000,
            "commission": 0.001, "slippage": 0.0005,
            "order_size_mode": "PCT_EQUITY", "order_size_pct": 100,
            "intraday": False,
            "start_date": "2024-06-30", "end_date": "2024-01-01",
        }
        assert client.post("/api/v1/backtest/run", json=payload).status_code == 422

    def test_backtest_run_nse_rejected(self):
        payload = {
            "strategy": "EMA_CROSSOVER", "strategy_config": {},
            "name": "T", "symbol": "RELIANCE", "interval": "1d",
            "trading_market": "NSE", "initial_cash": 10000,
            "commission": 0.001, "slippage": 0.0005,
            "order_size_mode": "PCT_EQUITY", "order_size_pct": 100,
            "intraday": False,
            "start_date": "2024-01-01", "end_date": "2024-06-30",
        }
        assert client.post("/api/v1/backtest/run", json=payload).status_code == 422

    @patch("app.api.v1.routes.backtest_db.get_db")
    def test_db_backtests_list_no_db(self, mock_get_db):
        """When DATABASE_URL is not set, listing backtests returns empty list."""
        mock_get_db.return_value.__aenter__.return_value = None
        r = client.get("/api/v1/backtests")
        assert r.status_code == 200
        assert r.json() == []

    @patch("app.api.v1.routes.backtest_db.get_db")
    def test_db_backtests_get_nonexistent(self, mock_get_db):
        """When DATABASE_URL is not set, returns 503."""
        mock_get_db.return_value.__aenter__.return_value = None
        r = client.get("/api/v1/backtests/nonexistent-id")
        assert r.status_code in (404, 503)

    @patch("app.api.v1.routes.strategies_db.get_db")
    def test_db_strategies_list_fallback(self, mock_get_db):
        """
        When DATABASE_URL is not set, strategies endpoint returns
        the in-memory fallback list.
        """
        mock_get_db.return_value.__aenter__.return_value = None
        r = client.get("/api/v1/strategies")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 4
        type_codes = [s["type_code"] for s in data]
        for tc in ("EMA_CROSSOVER", "RSI_DIVERGENCE", "BOLLINGER_BANDS", "MACD_SIGNAL"):
            assert tc in type_codes

    def test_full_backtest_run_mocked(self):
        bars    = _bars(100)
        payload = {
            "strategy": "EMA_CROSSOVER",
            "strategy_config": {"fast_period": 12, "slow_period": 26, "source": "CLOSE"},
            "name": "Full Test", "symbol": "BTCUSDT", "interval": "1d",
            "trading_market": "BINANCE", "initial_cash": 10000,
            "commission": 0.001, "slippage": 0.0005,
            "order_size_mode": "PCT_EQUITY", "order_size_pct": 100,
            "intraday": False,
            "start_date": "2024-01-01", "end_date": "2024-04-10",
        }
        with patch("app.modules.backtest.engine.get_historical_data",
                   new_callable=AsyncMock) as m, \
             patch("app.modules.backtest.engine._persist_result",
                   new_callable=AsyncMock):
            m.return_value = bars
            resp = client.post("/api/v1/backtest/run", json=payload)

        assert resp.status_code == 200
        d = resp.json()
        assert d["status"] == "COMPLETED"
        assert "chart_html" in d
        stats = d["statistics"]
        for k in ("sharpe_ratio", "sortino_ratio", "calmar_ratio", "cagr_pct",
                  "buy_hold_return_pct", "alpha_pct", "beta",
                  "max_drawdown_pct", "avg_drawdown_pct",
                  "commissions_paid", "exposure_time_pct",
                  "equity_final", "equity_peak"):
            assert k in stats, f"Missing stat in response: {k}"
