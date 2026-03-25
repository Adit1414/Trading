"""
app/schemas/db.py
──────────────────
Pydantic response schemas for all database entities.

These are used:
  1. As FastAPI response_model types for DB-backed endpoints.
  2. To serialise ORM rows to JSON cleanly.
  3. As the source of truth for what the frontend receives from the DB layer.

Naming convention: <Entity>DB  (e.g. BacktestDB, StrategyDB)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Shared config: read ORM attributes directly ──────────────────────────────
_orm = ConfigDict(from_attributes=True)


# ─── USERS ────────────────────────────────────────────────────────────────────

class UserDB(BaseModel):
    model_config = _orm
    id:         str
    email:      str
    created_at: datetime


# ─── API_CREDENTIALS ──────────────────────────────────────────────────────────

class ApiCredentialDB(BaseModel):
    """
    API credential reference — vault_secret_id is intentionally exposed
    here only as an opaque UUID (the actual API keys live in Supabase Vault).
    """
    model_config = _orm
    id:              str
    user_id:         str
    environment:     str   # MAINNET | TESTNET
    vault_secret_id: str
    created_at:      datetime


# ─── STRATEGIES ───────────────────────────────────────────────────────────────

class StrategyDB(BaseModel):
    """
    Full strategy row from the STRATEGIES table.
    parameter_schema is returned as-is (JSON Schema dict) so the frontend
    can use it to build dynamic configuration forms.
    """
    model_config = _orm
    id:               str
    name:             str
    type_code:        str
    parameter_schema: Dict[str, Any]
    description:      Optional[str]


# ─── BOTS ─────────────────────────────────────────────────────────────────────

class BotDB(BaseModel):
    model_config = _orm
    id:                    str
    user_id:               str
    strategy_id:           str
    name:                  str
    environment:           str              # MAINNET | TESTNET
    status:                str              # RUNNING | STOPPED | PAUSED_LIMIT_REACHED
    trade_quantity:        Optional[float]
    daily_pnl_upper_limit: Optional[float]
    daily_pnl_lower_limit: Optional[float]
    parameters:            Dict[str, Any]   # user's strategy parameter values
    created_at:            datetime
    updated_at:            datetime


# ─── BOT_STATE ────────────────────────────────────────────────────────────────

class BotStateDB(BaseModel):
    model_config = _orm
    bot_id:                    str
    current_position:          str     # LONG | SHORT | FLAT
    active_quantity:           float
    average_entry_price:       float
    daily_realized_pnl:        float
    daily_unrealized_pnl:      float
    last_pnl_reset_timestamp:  Optional[datetime]
    updated_at:                datetime


# ─── TRADE_LOGS ───────────────────────────────────────────────────────────────

class TradeLogDB(BaseModel):
    model_config = _orm
    id:              str
    user_id:         str
    bot_id:          Optional[str]      # NULL = manual trade
    is_manual_trade: bool
    symbol:          str
    side:            str                # BUY | SELL
    quantity:        float
    execution_price: float
    environment:     str                # MAINNET | TESTNET
    executed_at:     datetime


# ─── BACKTESTS ────────────────────────────────────────────────────────────────

class BacktestDB(BaseModel):
    """
    Full backtest row as returned by the DB layer.

    parameters : full execution config (BacktestParameters)
    metrics    : full statistics dict (BacktestStatistics)
    result_file_url : Supabase Storage pointer to the heavy equity_curve
                      array.  NULL when storage is not configured.
    """
    model_config = _orm
    id:              str
    user_id:         Optional[str]
    strategy_id:     str
    symbol:          str
    timeframe:       str
    parameters:      Dict[str, Any]
    metrics:         Dict[str, Any]
    result_file_url: Optional[str]
    chart_html:      Optional[str] = None
    created_at:      datetime


class BacktestListItemDB(BaseModel):
    """
    Compact summary for the Backtest Results listing page.
    Only the fields needed to render a result card.
    """
    model_config = _orm
    id:              str
    strategy_id:     str
    symbol:          str
    timeframe:       str
    # Pulled from metrics JSONB for quick display
    total_return_pct: Optional[float] = Field(default=None)
    win_rate:         Optional[float] = Field(default=None)
    total_trades:     Optional[int]   = Field(default=None)
    created_at:       datetime

    @classmethod
    def from_orm_row(cls, row: Any) -> "BacktestListItemDB":
        """Build from a BacktestModel ORM instance, extracting metric scalars."""
        metrics = row.metrics or {}
        return cls(
            id=row.id,
            strategy_id=row.strategy_id,
            symbol=row.symbol,
            timeframe=row.timeframe,
            total_return_pct=metrics.get("total_return_pct"),
            win_rate=metrics.get("win_rate"),
            total_trades=metrics.get("total_trades"),
            created_at=row.created_at,
        )
