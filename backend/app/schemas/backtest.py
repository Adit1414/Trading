"""
app/schemas/backtest.py
────────────────────────
All Pydantic request / response models for the Backtesting Engine.

Parameter ranges sourced from trading_strategy_parameters.xlsx.
Statistics output.
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
    """Price input for indicator calculations (per xlsx: CLOSE, OPEN, HL2)."""
    CLOSE = "CLOSE"
    OPEN  = "OPEN"
    HL2   = "HL2"     # (high + low) / 2


class Interval(str, Enum):
    """Binance K-line intervals — matches GET /api/v3/klines `interval` enum."""
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
    FIXED_USDT – spend a fixed USDT amount per trade.
    PCT_EQUITY – spend a % of current portfolio equity per trade.
    """
    FIXED_USDT = "FIXED_USDT"
    PCT_EQUITY = "PCT_EQUITY"


# ─── Strategy-specific parameter schemas ─────────────────────────────────────
# Ranges taken verbatim from trading_strategy_parameters.xlsx

class EMACrossoverConfig(BaseModel):
    """
    EMA CrossOver parameters (xlsx: EMA Crossover parameters).
    fast_period : 3–50,   default 12
    slow_period : 15–200, default 26
    source      : CLOSE | OPEN | HL2
    """
    fast_period: int         = Field(default=12, ge=3,   le=50,
                                     description="Short-term EMA period (range 3–50)")
    slow_period: int         = Field(default=26, ge=15,  le=200,
                                     description="Long-term EMA period (range 15–200)")
    source:      CandleSource = Field(default=CandleSource.CLOSE,
                                      description="Price source: CLOSE | OPEN | HL2")

    @model_validator(mode="after")
    def _check(self) -> "EMACrossoverConfig":
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period")
        return self


class RSIDivergenceConfig(BaseModel):
    """
    RSI Divergence parameters (xlsx: RSI Divergence).
    period          : 2–50,  default 14
    oversold        : 10–40, default 30
    overbought      : 60–90, default 70
    lookback_periods: 3–10,  default 5  — bars to scan for divergence
    source          : CLOSE | OPEN | HL2
    """
    period:           int          = Field(default=14, ge=2,  le=50,
                                           description="RSI calculation period (range 2–50)")
    oversold:         int          = Field(default=30, ge=10, le=40,
                                           description="Oversold threshold (range 10–40)")
    overbought:       int          = Field(default=70, ge=60, le=90,
                                           description="Overbought threshold (range 60–90)")
    lookback_periods: int          = Field(default=5,  ge=3,  le=10,
                                           description="Bars to look back for divergence (range 3–10)")
    source:           CandleSource = Field(default=CandleSource.CLOSE,
                                           description="Price source: CLOSE | OPEN | HL2")

    @model_validator(mode="after")
    def _check(self) -> "RSIDivergenceConfig":
        if self.oversold >= self.overbought:
            raise ValueError("oversold must be less than overbought")
        return self


class BollingerBandsConfig(BaseModel):
    """
    Bollinger Bands parameters (xlsx: Bollinger Bands).
    period  : 10–50,    default 20
    std_dev : 0.5–3.0,  default 2.0
    source  : CLOSE | OPEN | HL2
    """
    period:  int          = Field(default=20,  ge=10,  le=50,
                                  description="SMA/std period (range 10–50)")
    std_dev: float        = Field(default=2.0, ge=0.5, le=3.0,
                                  description="Std deviation multiplier (range 0.5–3.0)")
    source:  CandleSource = Field(default=CandleSource.CLOSE,
                                  description="Price source: CLOSE | OPEN | HL2")


class MACDSignalConfig(BaseModel):
    """
    MACD Signal parameters (xlsx: MACD Signal).
    fast_period   : 6–30,  default 12
    slow_period   : 15–50, default 26
    signal_period : 5–15,  default 9
    source        : CLOSE | OPEN | HL2
    """
    fast_period:   int          = Field(default=12, ge=6,  le=30,
                                        description="Fast EMA period (range 6–30)")
    slow_period:   int          = Field(default=26, ge=15, le=50,
                                        description="Slow EMA period (range 15–50)")
    signal_period: int          = Field(default=9,  ge=5,  le=15,
                                        description="Signal line EMA period (range 5–15)")
    source:        CandleSource = Field(default=CandleSource.CLOSE,
                                        description="Price source: CLOSE | OPEN | HL2")

    @model_validator(mode="after")
    def _check(self) -> "MACDSignalConfig":
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period")
        return self


# ─── Strategy config registry (used by the frontend to build forms) ───────────

STRATEGY_CONFIG_SCHEMAS: Dict[str, type] = {
    "EMA_CROSSOVER":   EMACrossoverConfig,
    "RSI_DIVERGENCE":  RSIDivergenceConfig,
    "BOLLINGER_BANDS": BollingerBandsConfig,
    "MACD_SIGNAL":     MACDSignalConfig,
}


# ─── Main Request ─────────────────────────────────────────────────────────────

class BacktestRunRequest(BaseModel):
    """
    Full backtest run request.

    Common parameters (xlsx: Backtest Common Parameters):
      initial_cash     – Starting USDT balance.
      commission       – Fee per trade leg (0.001 = 0.1 %, Binance Spot default).
      slippage         – Execution slippage fraction (0.0005 = 0.05 %).
      order_size_mode  – PCT_EQUITY or FIXED_USDT.
      order_size_pct   – % of equity per trade (PCT_EQUITY mode).
      order_size_usdt  – Fixed USDT per trade (FIXED_USDT mode).
      intraday         – Force-close positions at end of each day.

    Strategy-specific parameters go in `strategy_config` as a free-form dict
    and are validated by the strategy class at engine run time.
    """

    # Strategy
    strategy:        StrategyName   = Field(...)
    strategy_config: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Strategy-specific parameters. See EMACrossoverConfig / "
            "RSIDivergenceConfig / BollingerBandsConfig / MACDSignalConfig "
            "for the accepted fields, types, and allowed ranges."
        ),
    )

    # Metadata
    name: str = Field(..., min_length=1, max_length=120)

    # Market — Binance only (SRS §1.2)
    symbol:         str           = Field(..., min_length=1, max_length=20,
                                          description="Binance trading pair, e.g. BTCUSDT")
    contract_type:  ContractType  = ContractType.SPOT
    trading_market: TradingMarket = TradingMarket.BINANCE
    interval:       Interval      = Interval.D1

    # Common simulation parameters (xlsx: Backtest Common Parameters)
    initial_cash: float = Field(
        default=10_000.0, ge=1.0,
        description="Starting simulated USDT balance",
    )
    commission: float = Field(
        default=0.001, ge=0.0, le=0.1,
        description="Trading fee per leg. Binance Spot = 0.001 (0.1%)",
    )
    slippage: float = Field(
        default=0.0005, ge=0.0, le=0.05,
        description="Execution slippage fraction. e.g. 0.0005 = 0.05%",
    )

    # Order sizing
    order_size_mode: OrderSizeMode   = Field(default=OrderSizeMode.PCT_EQUITY)
    order_size_pct:  float           = Field(
        default=100.0, ge=1.0, le=100.0,
        description="% of current equity to use per trade (PCT_EQUITY mode)",
    )
    order_size_usdt: Optional[float] = Field(
        default=None, ge=1.0,
        description="Fixed USDT per trade (FIXED_USDT mode)",
    )
    intraday: bool = Field(
        default=False,
        description="Close all positions at end of each calendar day",
    )

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
            raise ValueError("order_size_usdt required when order_size_mode = FIXED_USDT")
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


# ─── Response: equity point + trade record ────────────────────────────────────

class EquityPoint(BaseModel):
    timestamp: str
    value:     float


class TradeRecord(BaseModel):
    trade_number:  int
    direction:     str              # LONG (SHORT reserved for future)
    entry_date:    str
    entry_price:   float
    exit_date:     Optional[str]
    exit_price:    Optional[float]
    quantity_usdt: float            # USDT value of position at entry
    pnl:           Optional[float]
    return_pct:    Optional[float]
    status:        str              # OPEN | CLOSED


# ─── Response: full statistics ────────────

class BacktestStatistics(BaseModel):
    """
    Complete performance statistics.
    All monetary values in USDT. All ratios are dimensionless unless noted.
    """

    # ── Portfolio summary ─────────────────────────────────────────────────────
    equity_final:   float  = Field(description="Final portfolio value in USDT")
    equity_peak:    float  = Field(description="Maximum portfolio value reached in USDT")
    total_return:   float  = Field(description="Net profit/loss in USDT")
    total_return_pct: float= Field(description="Return as % of initial capital")

    # ── Time-based metrics ────────────────────────────────────────────────────
    exposure_time_pct: float = Field(
        description="% of total bars where capital was deployed in a position"
    )
    return_ann_pct:  float = Field(description="Annualised return %")
    volatility_ann_pct: float = Field(
        description="Annualised volatility of daily returns %"
    )
    cagr_pct:        float = Field(description="Compound Annual Growth Rate %")

    # ── Benchmark comparison ──────────────────────────────────────────────────
    buy_hold_return_pct: float = Field(
        description="Return % of a simple buy-and-hold strategy over the same period"
    )
    alpha_pct:  float = Field(
        description="Excess return over buy-and-hold benchmark %"
    )
    beta:       float = Field(
        description="Portfolio return sensitivity to the benchmark (buy-and-hold)"
    )

    # ── Risk-adjusted ratios ──────────────────────────────────────────────────
    sharpe_ratio:  float = Field(
        description="(Ann. return − risk-free rate) / Ann. volatility. Risk-free = 0"
    )
    sortino_ratio: float = Field(
        description="Ann. return / downside deviation (penalises only negative volatility)"
    )
    calmar_ratio:  float = Field(
        description="Ann. return / max drawdown % (higher = better risk/reward)"
    )

    # ── Drawdown ──────────────────────────────────────────────────────────────
    max_drawdown_pct:  float = Field(description="Maximum peak-to-trough decline %")
    avg_drawdown_pct:  float = Field(description="Average drawdown across all drawdown periods %")
    max_drawdown_duration: str = Field(
        description="Longest time from peak to recovery (e.g. '7 days 01:46:00')"
    )
    avg_drawdown_duration: str = Field(
        description="Average drawdown duration (e.g. '2 days 08:43:00')"
    )

    # ── Trade statistics ──────────────────────────────────────────────────────
    total_trades:   int
    winning_trades: int
    losing_trades:  int
    open_trades:    int
    win_rate:       float  = Field(description="% of closed trades that were profitable")
    avg_win:        float  = Field(description="Average profit per winning trade in USDT")
    avg_loss:       float  = Field(description="Average loss per losing trade in USDT")
    profit_factor:  Optional[float] = Field(
        description="Gross wins / gross losses. None when no losing trades"
    )
    avg_trade_duration_bars: Optional[float] = Field(
        description="Average trade duration in bars"
    )
    commissions_paid: float = Field(
        description="Total commissions paid across all trades in USDT"
    )


# ─── Response: parameters mirror ─────────────────────────────────────────────

class BacktestParameters(BaseModel):
    """Parameters tab — mirrors the request for audit / reference."""
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


# ─── Full response ────────────────────────────────────────────────────────────

class BacktestRunResponse(BaseModel):
    """Complete backtest report."""
    backtest_id: str
    name:        str
    status:      BacktestStatus
    created_at:  datetime

    # Overview tab
    equity_curve:     List[EquityPoint]
    start_date:       str
    end_date:         str
    duration_days:    int
    total_return:     float
    total_return_pct: float

    # Statistics tab (all Image 2 metrics)
    statistics: BacktestStatistics

    # Parameters tab
    parameters: BacktestParameters

    # Trade log
    trade_log: List[TradeRecord]

    # Interactive Plotly chart as self-contained HTML string
    chart_html: str = Field(
        description="Self-contained Plotly HTML with candlestick, indicator lines, "
                    "trade markers, equity curve, and volume. Embed directly in the frontend."
    )

    # Non-null only on ERROR
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


# ─── Strategy metadata endpoint schema ───────────────────────────────────────

class StrategyInfo(BaseModel):
    """Returned by GET /backtest/strategies — used by frontend to build config forms."""
    id:               str
    display_name:     str
    description:      str
    min_bars_required: int
    config_schema:    Dict[str, Any]   # JSON Schema of the config model
