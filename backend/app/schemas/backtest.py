"""
app/schemas/backtest.py
────────────────────────
All Pydantic request / response models for the Backtesting Engine.

Cryptocurrency / Binance specific (SRS §1.2):
  • TradingMarket is BINANCE only — no stock market support.
  • Commission default = 0.001 (0.1 %), standard Binance Spot fee.
  • `slippage` replaces `spread` — correct Binance terminology.
  • EMA / all strategies accept `source` (CLOSE | OPEN | HL2).
  • `order_size_mode` supports PCT_EQUITY or FIXED_USDT sizing.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ─── Enums ────────────────────────────────────────────────────────────────────

class StrategyName(str, Enum):
    EMA_CROSSOVER   = "EMA_CROSSOVER"
    RSI_DIVERGENCE  = "RSI_DIVERGENCE"
    BOLLINGER_BANDS = "BOLLINGER_BANDS"
    MACD_SIGNAL     = "MACD_SIGNAL"


class ContractType(str, Enum):
    """Binance contract types. SPOT = Binance Spot, FUTURE = USD-M Perp/Delivery."""
    SPOT   = "SPOT"
    FUTURE = "FUTURE"


class TradingMarket(str, Enum):
    """Binance only per SRS §1.2. SRS §1.4 will add NSE/Upstox/Dhan here."""
    BINANCE = "BINANCE"


class CandleSource(str, Enum):
    """
    Which candlestick value to use as price input for indicator calculations.
    Matches the Binance / TradingView `source` convention.
    """
    CLOSE = "CLOSE"   # closing price (most common, lowest noise)
    OPEN  = "OPEN"    # opening price
    HL2   = "HL2"     # (high + low) / 2  — median price


class Interval(str, Enum):
    """Binance K-line intervals accepted by GET /api/v3/klines."""
    M1  = "1m"
    M3  = "3m"
    M5  = "5m"
    M15 = "15m"
    M30 = "30m"
    H1  = "1h"
    H2  = "2h"
    H4  = "4h"
    H6  = "6h"
    H8  = "8h"
    H12 = "12h"
    D1  = "1d"
    D3  = "3d"
    W1  = "1w"
    MO1 = "1M"


class BacktestStatus(str, Enum):
    PENDING   = "PENDING"
    RUNNING   = "RUNNING"
    COMPLETED = "COMPLETED"
    ERROR     = "ERROR"


class OrderSizeMode(str, Enum):
    """
    How to size each order.
      FIXED_USDT – spend a fixed USDT amount per trade (order_size_usdt).
      PCT_EQUITY – spend a % of current portfolio equity per trade (order_size_pct).
    """
    FIXED_USDT = "FIXED_USDT"
    PCT_EQUITY = "PCT_EQUITY"


# ─── Strategy Parameter Schemas ───────────────────────────────────────────────

class EMACrossoverParams(BaseModel):
    """
    EMA CrossOver parameters (per Image 3).
    fast_period: short-term EMA (e.g. 9, 12, 20)
    slow_period: long-term EMA  (e.g. 26, 50, 200)
    source:      candle price input: CLOSE / OPEN / HL2
    """
    fast_period: int         = Field(default=12,  ge=2, le=200)
    slow_period: int         = Field(default=26,  ge=2, le=500)
    source:      CandleSource = Field(default=CandleSource.CLOSE)

    @model_validator(mode="after")
    def _check(self) -> "EMACrossoverParams":
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period")
        return self


class RSIDivergenceParams(BaseModel):
    period:     int          = Field(default=14,   ge=2,    le=100)
    overbought: float        = Field(default=70.0, ge=50.0, le=100.0)
    oversold:   float        = Field(default=30.0, ge=0.0,  le=50.0)
    source:     CandleSource = Field(default=CandleSource.CLOSE)

    @model_validator(mode="after")
    def _check(self) -> "RSIDivergenceParams":
        if self.oversold >= self.overbought:
            raise ValueError("oversold must be less than overbought")
        return self


class BollingerBandsParams(BaseModel):
    period:  int          = Field(default=20,  ge=2,   le=200)
    std_dev: float        = Field(default=2.0, ge=0.5, le=5.0)
    source:  CandleSource = Field(default=CandleSource.CLOSE)


class MACDSignalParams(BaseModel):
    fast_period:   int          = Field(default=12, ge=2, le=100)
    slow_period:   int          = Field(default=26, ge=2, le=300)
    signal_period: int          = Field(default=9,  ge=2, le=100)
    source:        CandleSource = Field(default=CandleSource.CLOSE)

    @model_validator(mode="after")
    def _check(self) -> "MACDSignalParams":
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period")
        return self


# ─── Request ─────────────────────────────────────────────────────────────────

class BacktestRunRequest(BaseModel):
    """
    Full backtest run request — matches 'Start New Backtest' UI modal.

    Simulation parameters (Image 3):
      initial_cash     – Starting USDT balance.
      commission       – Fee per trade leg (0.001 = 0.1 %, Binance Spot default).
      slippage         – Execution slippage fraction (0.0005 = 0.05 %).
      order_size_mode  – PCT_EQUITY (% of equity) or FIXED_USDT.
      order_size_pct   – % of equity per trade when mode = PCT_EQUITY.
      order_size_usdt  – Fixed USDT per trade when mode = FIXED_USDT.
      intraday         – Force-close all positions at end of each calendar day.
    """

    # Strategy
    strategy:        StrategyName    = Field(...)
    strategy_config: Dict[str, Any]  = Field(default_factory=dict)

    # Metadata
    name: str = Field(..., min_length=1, max_length=120)

    # Market — Binance only
    symbol:         str           = Field(..., min_length=1, max_length=20,
                                          description="Binance pair, e.g. BTCUSDT")
    contract_type:  ContractType  = ContractType.SPOT
    trading_market: TradingMarket = TradingMarket.BINANCE
    interval:       Interval      = Interval.D1

    # Simulation
    initial_cash: float = Field(default=10_000.0, ge=1.0,
                                description="Starting balance in USDT")
    commission:   float = Field(default=0.001, ge=0.0, le=0.1,
                                description="Fee per trade leg, e.g. 0.001 = 0.1 %")
    slippage:     float = Field(default=0.0005, ge=0.0, le=0.05,
                                description="Execution slippage fraction, e.g. 0.0005 = 0.05 %")
    intraday:     bool  = Field(default=False,
                                description="Close all positions at end of each trading day")

    # Order sizing
    order_size_mode: OrderSizeMode  = Field(default=OrderSizeMode.PCT_EQUITY)
    order_size_pct:  float          = Field(default=100.0, ge=1.0, le=100.0,
                                            description="% of current equity per trade (PCT_EQUITY mode)")
    order_size_usdt: Optional[float]= Field(default=None,  ge=1.0,
                                            description="Fixed USDT per trade (FIXED_USDT mode)")

    # Date range
    start_date: date = Field(..., description="Backtest start date (UTC)")
    end_date:   date = Field(..., description="Backtest end date (UTC)")

    # Injected by Module 1 JWT middleware once integrated
    user_id: Optional[str] = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def _validate(self) -> "BacktestRunRequest":
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        if self.order_size_mode == OrderSizeMode.FIXED_USDT and not self.order_size_usdt:
            raise ValueError("order_size_usdt is required when order_size_mode = FIXED_USDT")
        return self

    @field_validator("symbol")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    model_config = {"json_schema_extra": {"example": {
        "strategy": "EMA_CROSSOVER",
        "strategy_config": {"fast_period": 12, "slow_period": 26, "source": "CLOSE"},
        "name": "EMA Test Run 1",
        "symbol": "BTCUSDT",
        "contract_type": "SPOT",
        "trading_market": "BINANCE",
        "interval": "1d",
        "initial_cash": 10000,
        "commission": 0.001,
        "slippage": 0.0005,
        "order_size_mode": "PCT_EQUITY",
        "order_size_pct": 100.0,
        "intraday": False,
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
    }}}


# ─── Response models ──────────────────────────────────────────────────────────

class EquityPoint(BaseModel):
    timestamp: str
    value:     float


class TradeRecord(BaseModel):
    trade_number:  int
    direction:     str              # LONG (SHORT when strategies support it)
    entry_date:    str
    entry_price:   float
    exit_date:     Optional[str]
    exit_price:    Optional[float]
    quantity_usdt: float            # USDT value of the position at entry
    pnl:           Optional[float]
    return_pct:    Optional[float]
    status:        str              # OPEN / CLOSED


class BacktestStatistics(BaseModel):
    """Statistics tab — Performance Synthesizer output (HLD §4.2)."""
    total_return:            float
    total_return_pct:        float
    final_portfolio_value:   float
    win_rate:                float           # 0–100 %
    max_drawdown:            float           # absolute USDT
    max_drawdown_pct:        float           # percentage
    total_trades:            int
    winning_trades:          int
    losing_trades:           int
    open_trades:             int
    avg_win:                 float
    avg_loss:                float
    profit_factor:           Optional[float]
    avg_trade_duration_bars: Optional[float]


class BacktestParameters(BaseModel):
    """Parameters tab — mirrors the request for audit / reference."""
    name:            Optional[str] = Field(default=None)
    strategy:        str
    strategy_config: Dict[str, Any]
    symbol:          str
    interval:        str
    contract_type:   str
    trading_market:  str
    initial_cash:    float
    commission:      float
    slippage:        float
    order_size_mode: str
    order_size_usdt: Optional[float]
    order_size_pct:  float
    intraday:        bool
    start_date:      str
    end_date:        str
    duration_days:   int


class BacktestRunResponse(BaseModel):
    """Full backtest report returned on completion."""
    backtest_id:      str
    name:             str
    status:           BacktestStatus
    created_at:       datetime

    equity_curve:     List[EquityPoint]

    start_date:       str
    end_date:         str
    duration_days:    int
    total_return:     float
    total_return_pct: float

    statistics:  BacktestStatistics
    parameters:  BacktestParameters
    trade_log:   List[TradeRecord]

    error_message: Optional[str] = None


class BacktestListItem(BaseModel):
    """Card on the Backtest Results listing page."""
    backtest_id:      str
    name:             str
    status:           BacktestStatus
    strategy:         str
    symbol:           str
    total_return_pct: Optional[float]
    created_at:       datetime