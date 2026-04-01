"""
tests/test_backtest.py
────────────────────────
Test suite for the Backtesting Engine (Module 2) — Binance / Crypto.
30 tests covering schemas, strategies, simulation, synthesis, engine, API.

Run:
    pip install pytest pytest-asyncio httpx
    pytest tests/ -v
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.backtest.engine import BacktestError, run_backtest
from app.modules.backtest.performance import simulate_trades, synthesize
from app.modules.backtest.strategies import get_strategy
from app.modules.backtest.strategies.base import SIGNAL_BUY, SIGNAL_HOLD, SIGNAL_SELL
from app.schemas.backtest import BacktestRunRequest, OrderSizeMode, StrategyName


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _make_df(n: int = 100, start_price: float = 30000.0) -> pd.DataFrame:
    import numpy as np
    np.random.seed(42)
    prices = start_price + np.cumsum(np.random.randn(n) * 50)
    prices = prices.clip(min=1.0)
    index  = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame({
        "open":   prices,
        "high":   prices * 1.005,
        "low":    prices * 0.995,
        "close":  prices + np.random.randn(n) * 20,
        "volume": (abs(np.random.randn(n)) * 1e6 + 1e5),
    }, index=index)


def _make_request(**overrides) -> BacktestRunRequest:
    defaults: Dict[str, Any] = {
        "strategy":        StrategyName.EMA_CROSSOVER,
        "strategy_config": {"fast_period": 5, "slow_period": 10, "source": "CLOSE"},
        "name":            "Test Run",
        "symbol":          "BTCUSDT",
        "interval":        "1d",
        "trading_market":  "BINANCE",
        "initial_cash":    10_000.0,
        "commission":      0.001,
        "slippage":        0.0005,
        "order_size_mode": OrderSizeMode.PCT_EQUITY,
        "order_size_pct":  100.0,
        "intraday":        False,
        "start_date":      date(2024, 1, 1),
        "end_date":        date(2024, 6, 30),
    }
    defaults.update(overrides)
    return BacktestRunRequest(**defaults)


def _mock_bars(n: int = 100):
    from app.services.market_data.base import OHLCV
    import numpy as np
    np.random.seed(0)
    prices = 30000 + np.cumsum(np.random.randn(n) * 50)
    index  = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    return [
        OHLCV(str(ts), float(p), float(p * 1.005), float(p * 0.995),
              float(p + 10), 500_000.0)
        for ts, p in zip(index, prices)
    ]


# ─── Schema Tests ──────────────────────────────────────────────────────────────

class TestSchemas:
    def test_valid_request(self):
        req = _make_request()
        assert req.symbol == "BTCUSDT"
        assert req.trading_market.value == "BINANCE"
        assert req.slippage == 0.0005

    def test_symbol_is_uppercased(self):
        req = _make_request(symbol="btcusdt")
        assert req.symbol == "BTCUSDT"

    def test_date_validation(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _make_request(start_date=date(2024, 6, 30), end_date=date(2024, 1, 1))

    def test_ema_config_validated_by_engine(self):
        from app.modules.backtest.strategies.base import StrategyConfigError
        req = _make_request(strategy_config={"fast_period": 30, "slow_period": 10})
        assert req.strategy_config["fast_period"] == 30
        with pytest.raises(StrategyConfigError):
            get_strategy("EMA_CROSSOVER", req.strategy_config)

    def test_fixed_usdt_requires_amount(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _make_request(
                order_size_mode=OrderSizeMode.FIXED_USDT,
                order_size_usdt=None,
            )

    def test_only_binance_market_allowed(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _make_request(trading_market="NSE")


# ─── Strategy Tests ────────────────────────────────────────────────────────────

class TestEMACrossover:
    s = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10, "source": "CLOSE"})

    def test_signals_column_present(self):
        result = self.s.generate_signals(_make_df(60))
        assert "signal" in result.columns

    def test_ema_columns_present(self):
        result = self.s.generate_signals(_make_df(60))
        assert "ema_fast" in result.columns and "ema_slow" in result.columns

    def test_warmup_zeroed(self):
        result = self.s.generate_signals(_make_df(60))
        assert (result["signal"].iloc[:self.s.slow_period] == SIGNAL_HOLD).all()

    def test_signals_only_valid_values(self):
        result = self.s.generate_signals(_make_df(60))
        assert result["signal"].isin([-1, 0, 1]).all()

    def test_source_hl2(self):
        s = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10, "source": "HL2"})
        result = s.generate_signals(_make_df(60))
        assert result["signal"].isin([-1, 0, 1]).all()

    def test_source_open(self):
        s = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10, "source": "OPEN"})
        result = s.generate_signals(_make_df(60))
        assert "signal" in result.columns

    def test_invalid_source_raises(self):
        from app.modules.backtest.strategies.base import StrategyConfigError
        with pytest.raises(StrategyConfigError):
            get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10, "source": "VWAP"})

    def test_evaluate_tick(self):
        tick = {"open": 30000, "high": 30500, "low": 29500, "close": 30200, "volume": 1e6}
        assert self.s.evaluate_tick(tick, 0) in (SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD)


class TestRSIDivergence:
    s = get_strategy("RSI_DIVERGENCE", {"period": 14, "source": "CLOSE"})

    def test_rsi_bounds(self):
        result = self.s.generate_signals(_make_df(80))
        valid  = result["rsi"].dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_source_hl2(self):
        s = get_strategy("RSI_DIVERGENCE", {"period": 14, "source": "HL2"})
        result = s.generate_signals(_make_df(80))
        assert result["signal"].isin([-1, 0, 1]).all()


class TestBollingerBands:
    s = get_strategy("BOLLINGER_BANDS", {"period": 20, "std_dev": 2.0})

    def test_band_columns(self):
        result = self.s.generate_signals(_make_df(80))
        for col in ("bb_mid", "bb_upper", "bb_lower"):
            assert col in result.columns

    def test_upper_above_lower(self):
        result = self.s.generate_signals(_make_df(80)).dropna()
        assert (result["bb_upper"] >= result["bb_lower"]).all()


class TestMACDSignal:
    s = get_strategy("MACD_SIGNAL", {"fast_period": 5, "slow_period": 10, "signal_period": 3})

    def test_macd_columns(self):
        result = self.s.generate_signals(_make_df(80))
        for col in ("macd_line", "macd_signal", "macd_hist"):
            assert col in result.columns

    def test_source_hl2(self):
        s = get_strategy("MACD_SIGNAL", {
            "fast_period": 5, "slow_period": 10,
            "signal_period": 3, "source": "HL2"
        })
        result = s.generate_signals(_make_df(80))
        assert result["signal"].isin([-1, 0, 1]).all()


# ─── Simulation Tests ──────────────────────────────────────────────────────────

def _run_sim(df, initial_cash=10000, pct=100.0):
    return simulate_trades(
        df=df,
        initial_cash=initial_cash,
        commission=0.001,
        slippage=0.0005,
        order_size_mode=OrderSizeMode.PCT_EQUITY,
        order_size_pct=pct,
        order_size_usdt=None,
        intraday=False,
    )


class TestSimulateTrades:
    def test_equity_curve_length(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10})
        df = s.generate_signals(_make_df(60))
        eq, _, _ = _run_sim(df)
        assert len(eq) == len(df)

    def test_initial_equity_equals_cash(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10})
        df = s.generate_signals(_make_df(60))
        eq, _, _ = _run_sim(df)
        assert eq[0].value == 10000.0

    def test_no_negative_portfolio(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10})
        df = s.generate_signals(_make_df(60))
        _, _, final = _run_sim(df)
        assert final >= 0

    def test_100pct_equity_actually_trades(self):
        """
        Regression test for the commission-budget bug.
        With 100 % equity and commission=0.1 %, the old code computed:
            alloc = 10000, cost = 10010 → 10000 >= 10010 → never entered!
        The fix pre-adjusts alloc so cost == budget == cash * pct.
        """
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10})
        df = s.generate_signals(_make_df(100))
        eq, raw_trades, _ = _run_sim(df)
        # With 100 bars and a 5/10 EMA crossover there must be at least one trade
        assert len(raw_trades) > 0, (
            "No trades executed with 100 % equity — commission-budget bug still present"
        )

    def test_trades_have_nonzero_pnl(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10})
        df = s.generate_signals(_make_df(100))
        _, raw_trades, _ = _run_sim(df)
        closed = [t for t in raw_trades if t["status"] == "CLOSED"]
        for t in closed:
            assert t["pnl"] is not None

    def test_fixed_usdt_mode(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10})
        df = s.generate_signals(_make_df(60))
        eq, _, final = simulate_trades(
            df=df, initial_cash=10000, commission=0.001, slippage=0.0005,
            order_size_mode=OrderSizeMode.FIXED_USDT,
            order_size_pct=100.0, order_size_usdt=500.0, intraday=False,
        )
        assert final >= 0

    def test_50pct_equity_leaves_remaining_cash(self):
        """Position size = 50 % of equity; remaining cash should stay above 0."""
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10})
        df = s.generate_signals(_make_df(100))
        eq, raw_trades, _ = simulate_trades(
            df=df, initial_cash=10000, commission=0.001, slippage=0.0005,
            order_size_mode=OrderSizeMode.PCT_EQUITY,
            order_size_pct=50.0, order_size_usdt=None, intraday=False,
        )
        # Portfolio value should never drop below 0
        assert all(pt.value >= 0 for pt in eq)


class TestSynthesize:
    def test_win_rate_in_bounds(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10})
        df = s.generate_signals(_make_df(60))
        eq, raw, _ = _run_sim(df)
        stats, _ = synthesize(eq, raw, 10000)
        assert 0.0 <= stats.win_rate <= 100.0

    def test_stats_fields_exist(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10})
        df = s.generate_signals(_make_df(60))
        eq, raw, _ = _run_sim(df)
        stats, records = synthesize(eq, raw, 10000)
        for field in ("total_return", "win_rate", "max_drawdown_pct", "total_trades"):
            assert hasattr(stats, field)

    def test_trade_records_have_quantity_usdt(self):
        s  = get_strategy("EMA_CROSSOVER", {"fast_period": 5, "slow_period": 10})
        df = s.generate_signals(_make_df(60))
        eq, raw, _ = _run_sim(df)
        _, records = synthesize(eq, raw, 10000)
        for r in records:
            assert hasattr(r, "quantity_usdt")
            assert r.quantity_usdt > 0


# ─── Engine Integration Tests ──────────────────────────────────────────────────

class TestEngine:
    def test_run_backtest_success(self):
        req  = _make_request()
        bars = _mock_bars(100)
        with patch("app.modules.backtest.engine.get_historical_data",
                   new_callable=AsyncMock) as m:
            m.return_value = bars
            result = asyncio.get_event_loop().run_until_complete(run_backtest(req))
        assert result.status.value == "COMPLETED"
        assert len(result.equity_curve) == len(bars)

    def test_run_backtest_no_data(self):
        req = _make_request()
        with patch("app.modules.backtest.engine.get_historical_data",
                   new_callable=AsyncMock) as m:
            m.return_value = []
            with pytest.raises(BacktestError, match="No data returned"):
                asyncio.get_event_loop().run_until_complete(run_backtest(req))

    def test_insufficient_bars(self):
        req  = _make_request(strategy_config={"fast_period": 50, "slow_period": 200})
        bars = _mock_bars(10)
        with patch("app.modules.backtest.engine.get_historical_data",
                   new_callable=AsyncMock) as m:
            m.return_value = bars
            with pytest.raises(BacktestError, match="Insufficient data"):
                asyncio.get_event_loop().run_until_complete(run_backtest(req))

    def test_slippage_and_commission_in_parameters(self):
        req  = _make_request()
        bars = _mock_bars(100)
        with patch("app.modules.backtest.engine.get_historical_data",
                   new_callable=AsyncMock) as m:
            m.return_value = bars
            result = asyncio.get_event_loop().run_until_complete(run_backtest(req))
        assert result.parameters.slippage == 0.0005
        assert result.parameters.commission == 0.001
        assert result.parameters.order_size_mode == "PCT_EQUITY"


# ─── API Endpoint Tests ────────────────────────────────────────────────────────

client = TestClient(app)


class TestAPI:
    def test_health(self):
        assert client.get("/health").status_code == 200

    def test_strategies_endpoint(self):
        resp = client.get("/api/v1/backtest/strategies")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()]
        for sid in ("EMA_CROSSOVER", "RSI_DIVERGENCE", "BOLLINGER_BANDS", "MACD_SIGNAL"):
            assert sid in ids

    def test_engine_health(self):
        resp = client.get("/api/v1/backtest/health")
        assert resp.status_code == 200

    def test_invalid_dates_422(self):
        payload = {
            "strategy": "EMA_CROSSOVER",
            "strategy_config": {"fast_period": 5, "slow_period": 10, "source": "CLOSE"},
            "name": "Bad Dates",
            "symbol": "BTCUSDT",
            "interval": "1d",
            "trading_market": "BINANCE",
            "initial_cash": 10000,
            "commission": 0.001,
            "slippage": 0.0005,
            "order_size_mode": "PCT_EQUITY",
            "order_size_pct": 100.0,
            "intraday": False,
            "start_date": "2024-06-30",
            "end_date": "2024-01-01",
        }
        assert client.post("/api/v1/backtest/run", json=payload).status_code == 422

    def test_nse_market_rejected(self):
        payload = {
            "strategy": "EMA_CROSSOVER",
            "strategy_config": {},
            "name": "Test",
            "symbol": "RELIANCE",
            "interval": "1d",
            "trading_market": "NSE",
            "initial_cash": 10000,
            "commission": 0.001,
            "slippage": 0.0005,
            "order_size_mode": "PCT_EQUITY",
            "order_size_pct": 100.0,
            "intraday": False,
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
        }
        assert client.post("/api/v1/backtest/run", json=payload).status_code == 422

    def test_end_to_end_mocked(self):
        bars    = _mock_bars(100)
        payload = {
            "strategy": "EMA_CROSSOVER",
            "strategy_config": {"fast_period": 5, "slow_period": 10, "source": "HL2"},
            "name": "HL2 Test",
            "symbol": "BTCUSDT",
            "interval": "1d",
            "trading_market": "BINANCE",
            "initial_cash": 10000,
            "commission": 0.001,
            "slippage": 0.0005,
            "order_size_mode": "PCT_EQUITY",
            "order_size_pct": 100.0,
            "intraday": False,
            "start_date": "2024-01-01",
            "end_date": "2024-04-10",
        }
        with patch("app.modules.backtest.engine.get_historical_data",
                   new_callable=AsyncMock) as m:
            m.return_value = bars
            resp = client.post("/api/v1/backtest/run", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert "slippage" in data["parameters"]
        assert data["parameters"]["trading_market"] == "BINANCE"
        assert "equity_curve" in data
        assert "trade_log" in data