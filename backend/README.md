# Algo Kaisen — Backend: Module 2 Backtesting Engine

To run: uvicorn app.main:app --reload
To test: python -m pytest tests/test_backtest.py -v


> **Status:** Module 2 (Strategy & Backtesting Engine) — fully implemented and tested.  
> Modules 1, 3, 4, 5 are stubbed and documented for seamless integration.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Alignment](#2-architecture-alignment)
3. [File-by-File Reference](#3-file-by-file-reference)
4. [Data Flow (Backtest Path)](#4-data-flow-backtest-path)
5. [API Reference](#5-api-reference)
6. [Adding a New Strategy](#6-adding-a-new-strategy)
7. [Adding a New Market / Broker](#7-adding-a-new-market--broker)
8. [Integration Guide for Future Modules](#8-integration-guide-for-future-modules)
9. [Running Locally](#9-running-locally)
10. [Running Tests](#10-running-tests)
11. [Configuration Reference](#11-configuration-reference)

---

## 1. Project Overview

Algo Kaisen is an automated trading strategy development and deployment platform (SRS v1.3, HLD March 2026).

This codebase delivers **Module 2 — Strategy & Backtesting Engine** as a standalone, independently testable FastAPI service. Every integration seam for the other four HLD modules is explicitly documented with stubs and comments.

---

## 2. Architecture Alignment

| HLD Module | Status | Entry Point |
|---|---|---|
| **1** – API Gateway & User Management | Stub (JWT middleware comment in `main.py`) | `app/main.py` |
| **2** – Strategy & Backtesting Engine | ✅ Implemented | `app/modules/backtest/` |
| **3** – Market Data Multiplexer (Streamer) | Stub (provider interface ready) | `app/services/market_data/` |
| **4** – Bot Execution & State Manager | Stub (`evaluate_tick()` on every strategy) | `app/modules/backtest/strategies/base.py` |
| **5** – Order Execution & Security Gateway | Stub (no dependency from Module 2) | — |

---

## 3. File-by-File Reference

```
backend/
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py                                  # FastAPI app factory
│   ├── core/
│   │   ├── config.py                            # Centralised settings (pydantic-settings)
│   │   └── rate_limiter.py                      # slowapi limiter — 10 req/min for backtest
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py                      # Aggregates all route routers
│   │       └── routes/
│   │           └── backtest.py                  # POST /run, GET /strategies, GET /health
│   ├── schemas/
│   │   └── backtest.py                          # All Pydantic I/O models
│   ├── services/
│   │   └── market_data/
│   │       ├── base.py                          # Abstract MarketDataProvider interface
│   │       ├── binance.py                       # Binance REST implementation (paginated)
│   │       └── __init__.py                      # Provider factory: get_market_data_provider()
│   └── modules/
│       └── backtest/
│           ├── data_cache.py                    # LRU TTL cache for historical K-lines
│           ├── engine.py                        # Orchestrator: fetch → signal → simulate → synthesize
│           ├── performance.py                   # Trade simulator + performance metrics
│           └── strategies/
│               ├── base.py                      # Abstract BaseStrategy
│               ├── ema_crossover.py             # EMA CrossOver strategy
│               ├── rsi_divergence.py            # RSI Divergence strategy
│               ├── bollinger_bands.py           # Bollinger Bands strategy
│               ├── macd_signal.py               # MACD Signal strategy
│               └── __init__.py                  # Strategy registry + get_strategy()
└── tests/
    └── test_backtest.py                         # 30 unit + integration tests
```

---

### `app/main.py`
FastAPI application factory. Wires together:
- CORS middleware
- slowapi rate-limiting middleware
- Module 1 JWT auth middleware **stub** (documented as a commented-out block)
- All v1 routes via `api_router`
- Startup / shutdown lifecycle hooks

**Module 1 integration point:**  
Uncomment and fill in the `jwt_auth_middleware` block. It must set `request.state.user_id`.

---

### `app/core/config.py`
Single source of truth for all environment configuration. Uses `pydantic-settings` to read from `.env` or OS environment.

Key settings relevant to Module 2:
- `BACKTEST_RATE_LIMIT` / `BACKTEST_RATE_LIMIT_WINDOW` — rate gate per HLD §5.2
- `HISTORICAL_CACHE_TTL` / `HISTORICAL_CACHE_MAXSIZE` — LRU cache sizing
- `BACKTEST_THREAD_POOL_SIZE` — parallelism for CPU-bound vectorised work
- `BINANCE_USE_TESTNET_FOR_HISTORY` — toggle Testnet vs Mainnet REST

Stubs for Modules 1, 4: `SUPABASE_*`, `DATABASE_URL`.

---

### `app/core/rate_limiter.py`
Shared `slowapi.Limiter` instance.

**Module 1 integration point:**  
Replace `_key_func = get_remote_address` with a function that extracts the Supabase user ID from `request.state.user_id` to enforce per-user limits instead of per-IP limits.

---

### `app/schemas/backtest.py`
All Pydantic v2 models for the backtest API:

| Model | Purpose |
|---|---|
| `BacktestRunRequest` | Input: matches the "Start New Backtest" UI modal |
| `BacktestRunResponse` | Output: full report (Overview + Parameters + Statistics tabs) |
| `BacktestStatistics` | Win rate, max drawdown, profit factor, etc. |
| `BacktestParameters` | Mirrors request fields for the Parameters tab |
| `EquityPoint` | Single data point on the Portfolio Performance chart |
| `TradeRecord` | Single row in the trade log table |
| `BacktestListItem` | Card on the Backtest Results listing page |

Enums: `StrategyName`, `ContractType`, `TradingMarket`, `Interval`, `BacktestStatus`.

---

### `app/services/market_data/base.py`
Abstract `MarketDataProvider` interface with two abstract methods:
- `fetch_klines(symbol, interval, start_date, end_date) → List[OHLCV]`
- `validate_symbol(symbol) → bool`

**Module 3 integration point:**  
The WebSocket Streamer (Module 3) handles live ticks via a separate WebSocket supervisor. This interface covers only the historical REST side used by Module 2.

---

### `app/services/market_data/binance.py`
Binance implementation:
- Paginates automatically through the 1 000-bar Binance API limit
- Retries with exponential backoff (up to 3 attempts) on HTTP errors and network failures
- Connects to Testnet or Mainnet based on `settings.BINANCE_USE_TESTNET_FOR_HISTORY`
- No API key required (uses public K-line endpoints)

---

### `app/services/market_data/__init__.py`
Provider factory. `get_market_data_provider(market)` resolves a market string (e.g. `"BINANCE"`) to a concrete provider instance.

**Module 3 / Future broker integration point:**  
Add new broker classes to `_PROVIDER_REGISTRY` here (see §7 below).

---

### `app/modules/backtest/data_cache.py`
**Historical Data Cacher** (HLD §4.2).

- `TTLCache` from `cachetools`: LRU eviction + time-to-live expiry
- Cache key = MD5 of `(market, symbol, interval, start_date, end_date)`
- Async-safe via `asyncio.Lock`
- `cache_stats()` exposes utilisation metrics to the `/backtest/health` endpoint

---

### `app/modules/backtest/strategies/base.py`
Abstract `BaseStrategy` with two abstract methods:

| Method | Used by | Description |
|---|---|---|
| `generate_signals(df)` | Module 2 (Backtest) | Vectorised, operates on full DataFrame |
| `evaluate_tick(tick, position)` | Module 4 (Bot) | Single-bar, stateful, incremental |

Signal constants: `SIGNAL_BUY = 1`, `SIGNAL_SELL = -1`, `SIGNAL_HOLD = 0`.

---

### `app/modules/backtest/strategies/ema_crossover.py`
EMA CrossOver strategy.
- **Buy:** Fast EMA crosses above Slow EMA
- **Sell:** Fast EMA crosses below Slow EMA
- Params: `fast_period` (default 12), `slow_period` (default 26)
- Warm-up: `slow_period` bars

---

### `app/modules/backtest/strategies/rsi_divergence.py`
RSI Divergence strategy.
- **Buy:** RSI crosses up through the oversold threshold
- **Sell:** RSI crosses down through the overbought threshold
- Params: `period` (14), `overbought` (70), `oversold` (30)
- Warm-up: `period + 1` bars

---

### `app/modules/backtest/strategies/bollinger_bands.py`
Bollinger Bands mean-reversion strategy.
- **Buy:** Close crosses below the lower band
- **Sell:** Close crosses above the upper band
- Params: `period` (20), `std_dev` (2.0)
- Warm-up: `period` bars

---

### `app/modules/backtest/strategies/macd_signal.py`
MACD Signal Line strategy.
- **Buy:** MACD line crosses above signal line
- **Sell:** MACD line crosses below signal line
- Params: `fast_period` (12), `slow_period` (26), `signal_period` (9)
- Warm-up: `slow_period + signal_period` bars

---

### `app/modules/backtest/strategies/__init__.py`
Strategy registry.
- `STRATEGY_REGISTRY`: maps strategy ID strings to concrete classes
- `get_strategy(strategy_id, config)`: instantiates and validates a strategy
- `list_strategies()`: returns metadata for the `/backtest/strategies` endpoint

---

### `app/modules/backtest/performance.py`
**Performance Synthesizer** (HLD §4.2).

Contains two pure functions:

#### `simulate_trades(df, initial_cash, commission, quantity, spread, intraday)`
Walk-forward trade simulation:
- Signals are shifted by 1 bar to prevent look-ahead bias
- Buy price = `open × (1 + spread)`, Sell price = `open × (1 − spread)`
- Commission charged on each leg
- Intraday mode: forces position closure at the last bar of each calendar day
- Returns: `(equity_curve, raw_trades, final_cash)`

#### `synthesize(equity_curve, raw_trades, initial_cash)`
Computes: total return, total return %, win rate, max drawdown (absolute + %), 
avg win, avg loss, profit factor, trade count breakdown.
Returns: `(BacktestStatistics, List[TradeRecord])`

---

### `app/modules/backtest/engine.py`
**Backtesting Engine Orchestrator** (HLD §4.2).

`run_backtest(request)` async function:
1. Fetch K-lines via `get_historical_data()` (cached)
2. Build Pandas DataFrame
3. Instantiate strategy from registry
4. Off-load `strategy.generate_signals(df)` to thread pool (non-blocking)
5. Off-load `simulate_trades(...)` to thread pool
6. Pass results through `synthesize()`
7. Build and return `BacktestRunResponse`
8. Call `_persist_result_stub()` — **replace with real DB write for Module 4**

**Module 4 integration point:**  
Replace `_persist_result_stub` with an `asyncpg` / SQLAlchemy async insert into the PostgreSQL `backtest_runs` table. The Backtest Results listing page depends on this.

---

### `app/api/v1/routes/backtest.py`
Three endpoints:

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/backtest/run` | Execute backtest — rate-limited 10 req/min |
| `GET` | `/api/v1/backtest/strategies` | List all registered strategies |
| `GET` | `/api/v1/backtest/health` | Engine + cache health check |

**Module 1 integration point:**  
Uncomment `body.user_id = request.state.user_id` once the JWT middleware is active.

---

### `tests/test_backtest.py`
30 tests across 7 test classes:

| Class | What it tests |
|---|---|
| `TestSchemas` | Pydantic validation, date range guard |
| `TestEMACrossover` | Signal generation, warmup, config validation, tick evaluation |
| `TestRSIDivergence` | RSI column, bounds, warmup |
| `TestBollingerBands` | Band columns, upper > lower, warmup |
| `TestMACDSignal` | MACD columns, signal validity |
| `TestSimulateTrades` | Equity curve length, initial cash, no negative cash |
| `TestSynthesize` | Stats fields, win-rate bounds |
| `TestEngine` | Full orchestration with mocked data, no-data error, insufficient-bars error |
| `TestAPI` | All three endpoints via TestClient, mocked end-to-end run |

---

## 4. Data Flow (Backtest Path)

```
React UI (POST /api/v1/backtest/run)
    │
    ▼
app/api/v1/routes/backtest.py   ← rate limiter, user_id injection stub
    │
    ▼
app/modules/backtest/engine.py  ← run_backtest()
    │
    ├─► app/modules/backtest/data_cache.py   ── cache hit? ──► return cached bars
    │       │ cache miss
    │       ▼
    │   app/services/market_data/binance.py  ── paginated Binance REST fetch
    │
    ├─► app/modules/backtest/strategies/     ── get_strategy() from registry
    │
    ├─► ThreadPoolExecutor                   ── strategy.generate_signals(df)  [CPU]
    │
    ├─► ThreadPoolExecutor                   ── simulate_trades(df, ...)        [CPU]
    │
    ├─► app/modules/backtest/performance.py  ── synthesize() → stats + trade log
    │
    └─► BacktestRunResponse  →  JSON → React UI
             │
             └─► _persist_result_stub()   [TODO: PostgreSQL insert for Module 4]
```

---

## 5. API Reference

### `POST /api/v1/backtest/run`

**Rate limit:** 10 requests / minute (per HLD §5.2)

**Request body:**
```json
{
  "strategy": "EMA_CROSSOVER",
  "strategy_config": { "fast_period": 12, "slow_period": 26 },
  "name": "EMA Test Run 1",
  "symbol": "BTCUSDT",
  "contract_type": "SPOT",
  "trading_market": "BINANCE",
  "interval": "1d",
  "initial_cash": 100000,
  "commission": 0.001,
  "quantity": 1,
  "spread": 0.0005,
  "intraday": false,
  "start_date": "2024-01-01",
  "end_date": "2024-06-30"
}
```

**Response:** Full `BacktestRunResponse` JSON with `equity_curve`, `statistics`, `trade_log`, `parameters`.

**Error codes:**
- `422` — Validation error (bad dates, unknown strategy, insufficient data)
- `429` — Rate limit exceeded
- `500` — Unexpected server error

---

### `GET /api/v1/backtest/strategies`
Returns all registered strategies with their IDs and display names.

### `GET /api/v1/backtest/health`
Returns engine status and LRU cache utilisation stats.

### `GET /health`
Top-level health check. Returns `{"status": "ok", "version": "0.1.0"}`.

---

## 6. Adding a New Strategy

1. Create `app/modules/backtest/strategies/my_strategy.py`, subclassing `BaseStrategy`.
2. Implement `_validate_config()`, `generate_signals()`, `evaluate_tick()`, and `min_bars_required`.
3. Add to `STRATEGY_REGISTRY` in `app/modules/backtest/strategies/__init__.py`:
   ```python
   from app.modules.backtest.strategies.my_strategy import MyStrategy
   STRATEGY_REGISTRY["MY_STRATEGY"] = MyStrategy
   ```
4. Add `MY_STRATEGY` to the `StrategyName` enum in `app/schemas/backtest.py`.
5. Write tests in `tests/test_backtest.py` following the existing class pattern.

---

## 7. Adding a New Market / Broker

1. Subclass `MarketDataProvider` in `app/services/market_data/my_broker.py`.
2. Implement `fetch_klines()` and `validate_symbol()`.
3. Register in `app/services/market_data/__init__.py`:
   ```python
   from app.services.market_data.my_broker import MyBrokerData
   _PROVIDER_REGISTRY["NSE"] = MyBrokerData
   ```
4. Add the market key to the `TradingMarket` enum in `app/schemas/backtest.py`.

---

## 8. Integration Guide for Future Modules

### Module 1 — JWT Auth Middleware
**File:** `app/main.py`  
Uncomment the `jwt_auth_middleware` skeleton. It should:
- Extract the `Authorization: Bearer <token>` header
- Call `supabase.auth.get_user(token)` (or the `python-jose` JWT decoder)
- Set `request.state.user_id`

**File:** `app/core/rate_limiter.py`  
Replace `_key_func = get_remote_address` with a lambda that reads `request.state.user_id`.

**File:** `app/api/v1/routes/backtest.py`  
Uncomment `body.user_id = request.state.user_id`.

---

### Module 3 — Market Data Multiplexer (WebSocket Streamer)
**Interface already ready:** `app/services/market_data/base.py`  
The Binance WebSocket Supervisor should push ticks into an `asyncio.Queue`. Bots subscribe to this queue — this is the `evaluate_tick()` path defined on every strategy.

---

### Module 4 — Bot Execution & State Manager
**File:** `app/modules/backtest/engine.py`  
Replace `_persist_result_stub()` with an actual `asyncpg` insert.

**Strategy `evaluate_tick()` method** — already implemented on all four strategies. Module 4's Bot Instance Orchestrator calls this on every incoming tick from Module 3's queue.

**Suggested DB schema for backtest results:**
```sql
CREATE TABLE backtest_runs (
    id          UUID PRIMARY KEY,
    user_id     UUID NOT NULL,
    name        TEXT,
    status      TEXT,
    strategy    TEXT,
    symbol      TEXT,
    parameters  JSONB,
    statistics  JSONB,
    equity_curve JSONB,
    trade_log   JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

### Module 5 — Order Execution & Security Gateway
No direct dependency from Module 2. Module 5 is only called by Module 4's `Tick Evaluator` when a `SIGNAL_BUY` or `SIGNAL_SELL` is emitted from `evaluate_tick()`.

---

## 9. Running Locally

```bash
# 1. Clone and enter
cd backend

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env if needed (defaults work out of the box for Module 2)

# 5. Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Open API docs
# http://localhost:8000/docs
```

---

## 10. Running Tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

All 30 tests should pass. Tests mock the Binance network calls so no internet connection is required.

---

## 11. Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `Algo Kaisen` | Application name |
| `DEBUG` | `false` | Enables debug logging |
| `BINANCE_USE_TESTNET_FOR_HISTORY` | `false` | Use Testnet REST for K-lines |
| `BINANCE_MAINNET_BASE_URL` | `https://api.binance.com` | Mainnet base URL |
| `BINANCE_TESTNET_BASE_URL` | `https://testnet.binance.vision` | Testnet base URL |
| `BACKTEST_RATE_LIMIT` | `10` | Max backtest requests per window |
| `BACKTEST_RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |
| `HISTORICAL_CACHE_TTL` | `3600` | Cache entry TTL in seconds |
| `HISTORICAL_CACHE_MAXSIZE` | `256` | Max LRU cache entries |
| `BACKTEST_THREAD_POOL_SIZE` | `4` | Thread pool workers for vectorised ops |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Allowed frontend origins |
| `SUPABASE_URL` | — | Module 1 stub |
| `SUPABASE_ANON_KEY` | — | Module 1 stub |
| `SUPABASE_SERVICE_ROLE_KEY` | — | Module 1 / 5 stub |
| `DATABASE_URL` | — | Module 4 stub (PostgreSQL DSN) |
