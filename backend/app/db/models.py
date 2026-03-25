"""
app/db/models.py
─────────────────
SQLAlchemy ORM models — mirrors the database schema exactly.

Tables (per DatabaseSchema.svg):
  USERS            – platform users (managed by Supabase Auth)
  API_CREDENTIALS  – encrypted Binance keys stored in Supabase Vault
  STRATEGIES       – strategy catalogue (seeded rows, one per strategy type)
  BOTS             – user-created trading bots
  BOT_STATE        – live runtime state for each bot (1-to-1 with BOTS)
  TRADE_LOGS       – every executed order (bot-generated or manual)
  BACKTESTS        – backtest run records

Relationships (per SVG):
  USERS       ||--o{ API_CREDENTIALS  : "secures keys via"
  USERS       ||--o{ BOTS             : "owns"
  USERS       ||--o{ TRADE_LOGS       : (via user_id FK)
  USERS       ||--o{ BACKTESTS        : "runs"
  STRATEGIES  ||--o{ BOTS             : "provides template for"
  STRATEGIES  ||--o{ BACKTESTS        : "provides template for"
  BOTS        ||--|| BOT_STATE        : "maintains 1-to-1"
  BOTS        ||--o{ TRADE_LOGS       : "generates (if not manual)"
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ─── USERS ────────────────────────────────────────────────────────────────────

class UserModel(Base):
    """
    Platform users.  Managed by Supabase Auth — this table mirrors the
    auth.users table so we can use standard FK constraints inside the
    public schema.  Rows are created by a Supabase trigger or explicitly
    when a user first signs in.
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=_uuid,
        comment="Matches Supabase auth.users.id",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    api_credentials: Mapped[list["ApiCredentialModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    bots: Mapped[list["BotModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    trade_logs: Mapped[list["TradeLogModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    backtests: Mapped[list["BacktestModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


# ─── API_CREDENTIALS ──────────────────────────────────────────────────────────

class ApiCredentialModel(Base):
    """
    Binance API key references.  The actual keys are stored in Supabase
    Vault; this table holds only the vault_secret_id pointer so keys
    are never exposed in the application database.

    Constraints:
      - One credential set per (user_id, environment) pair.
      - environment must be 'MAINNET' or 'TESTNET'.
    """
    __tablename__ = "api_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "environment", name="uq_api_creds_user_env"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    environment: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="MAINNET or TESTNET",
    )
    vault_secret_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
        comment="Pointer to Supabase Vault decrypted_secrets view",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["UserModel"] = relationship(back_populates="api_credentials")

    def __repr__(self) -> str:
        return f"<ApiCredential user={self.user_id} env={self.environment}>"


# ─── STRATEGIES ───────────────────────────────────────────────────────────────

class StrategyModel(Base):
    """
    Strategy catalogue — seeded at application startup.
    Each row represents one strategy type (EMA CrossOver, RSI Divergence, etc.).

    parameter_schema (JSONB):
        Stores the JSON Schema for this strategy's config parameters,
        including defaults and min/max ranges.  Used by the frontend to
        dynamically build configuration forms without hardcoding field
        definitions.

    Relationships:
      STRATEGIES ||--o{ BOTS      : "provides template for"
      STRATEGIES ||--o{ BACKTESTS : "provides template for"
    """
    __tablename__ = "strategies"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="e.g. RSI Divergence",
    )
    type_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="e.g. RSI_DIVERGENCE — matches StrategyName enum",
    )
    parameter_schema: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="UI constraints: defaults, min/max ranges from xlsx",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    bots: Mapped[list["BotModel"]] = relationship(back_populates="strategy")
    backtests: Mapped[list["BacktestModel"]] = relationship(back_populates="strategy")

    def __repr__(self) -> str:
        return f"<Strategy type_code={self.type_code} name={self.name}>"


# ─── BOTS ─────────────────────────────────────────────────────────────────────

class BotModel(Base):
    """
    User-created trading bots.

    status values: RUNNING | STOPPED | PAUSED_LIMIT_REACHED
    environment  : MAINNET | TESTNET

    parameters (JSONB):
        User's chosen strategy values, e.g. {"rsi_period": 14, "overbought": 70}.
        Must conform to the corresponding strategy's parameter_schema.

    Circuit breakers:
        daily_pnl_upper_limit — take-profit: bot pauses when daily PnL exceeds this.
        daily_pnl_lower_limit — stop-loss:   bot pauses when daily PnL drops below this.

    Relationships:
      BOTS ||--|| BOT_STATE   : "maintains 1-to-1"
      BOTS ||--o{ TRADE_LOGS  : "generates (if not manual)"
    """
    __tablename__ = "bots"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strategy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("strategies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="User-defined bot name",
    )
    environment: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="MAINNET or TESTNET",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="STOPPED",
        comment="RUNNING, STOPPED, or PAUSED_LIMIT_REACHED",
    )
    trade_quantity: Mapped[float | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
        comment="Asset allocation per trade (USDT)",
    )
    daily_pnl_upper_limit: Mapped[float | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
        comment="Take-profit circuit breaker (USDT)",
    )
    daily_pnl_lower_limit: Mapped[float | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
        comment="Stop-loss circuit breaker (USDT)",
    )
    parameters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="User's chosen strategy parameter values",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["UserModel"] = relationship(back_populates="bots")
    strategy: Mapped["StrategyModel"] = relationship(back_populates="bots")
    state: Mapped["BotStateModel"] = relationship(
        back_populates="bot",
        uselist=False,
        cascade="all, delete-orphan",
    )
    trade_logs: Mapped[list["TradeLogModel"]] = relationship(
        back_populates="bot", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Bot id={self.id} name={self.name} status={self.status}>"


# ─── BOT_STATE ────────────────────────────────────────────────────────────────

class BotStateModel(Base):
    """
    Live runtime state for a bot — 1-to-1 with BOTS.

    bot_id is both the primary key and a FK to BOTS, enforcing the
    strict 1-to-1 relationship per the schema diagram.

    current_position : LONG | SHORT | FLAT
    last_pnl_reset_timestamp : used to reset daily PnL at 00:00 UTC
    """
    __tablename__ = "bot_state"

    bot_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("bots.id", ondelete="CASCADE"),
        primary_key=True,
        comment="PK and FK to bots.id — enforces 1-to-1",
    )
    current_position: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="FLAT",
        server_default="FLAT",
        comment="LONG, SHORT, or FLAT",
    )
    active_quantity: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        default=0,
        comment="Current open position size",
    )
    average_entry_price: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        default=0,
        comment="Average price of the current open position",
    )
    daily_realized_pnl: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        default=0,
        comment="Today's closed profit/loss in USDT",
    )
    daily_unrealized_pnl: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        default=0,
        comment="Current open position mark-to-market PnL",
    )
    last_pnl_reset_timestamp: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Used to reset daily PnL at 00:00 UTC",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    bot: Mapped["BotModel"] = relationship(back_populates="state")

    def __repr__(self) -> str:
        return f"<BotState bot={self.bot_id} pos={self.current_position}>"


# ─── TRADE_LOGS ───────────────────────────────────────────────────────────────

class TradeLogModel(Base):
    """
    Every executed order — both bot-generated and manual.

    bot_id is nullable:  NULL means this was a manual trade
    (is_manual_trade should be True in that case).

    side        : BUY | SELL
    environment : MAINNET | TESTNET
    """
    __tablename__ = "trade_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bot_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("bots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="NULL means this was a manual trade",
    )
    is_manual_trade: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Default: false",
    )
    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="e.g. BTCUSDT",
    )
    side: Mapped[str] = mapped_column(
        String(4),
        nullable=False,
        comment="BUY or SELL",
    )
    quantity: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )
    execution_price: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )
    environment: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="MAINNET or TESTNET",
    )
    executed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["UserModel"] = relationship(back_populates="trade_logs")
    bot: Mapped["BotModel | None"] = relationship(back_populates="trade_logs")

    def __repr__(self) -> str:
        return f"<TradeLog id={self.id} {self.side} {self.symbol} @ {self.execution_price}>"


# ─── BACKTESTS ────────────────────────────────────────────────────────────────

class BacktestModel(Base):
    """
    Backtest run records.

    parameters (JSONB):
        Full execution configuration — the BacktestParameters Pydantic model
        serialised to dict.  Includes symbol, timeframe, initial_cash,
        commission, slippage, order sizing, strategy_config, etc.

    metrics (JSONB):
        Scalar performance values as per the SVG comment:
        "Scalar values: win_rate, max_drawdown, total_trades"
        In practice we store the full BacktestStatistics dict here so
        the listing page can display rich stats without a separate query.

    result_file_url (varchar):
        Pointer to the heavy equity_curve JSON array stored in
        Supabase Storage (bucket: backtest-results/<id>.json).
        NULL when storage upload is disabled / not configured.

    Relationships:
      BACKTESTS }o--|| USERS      (user_id FK)
      BACKTESTS }o--|| STRATEGIES (strategy_id FK)
    """
    __tablename__ = "backtests"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,           # nullable until Module 1 auth is wired
        index=True,
    )
    strategy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("strategies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    timeframe: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        comment="e.g. 1h, 15m, 1d",
    )
    parameters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full execution configuration (BacktestParameters)",
    )
    metrics: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Scalar performance values: win_rate, max_drawdown, total_trades, etc.",
    )
    result_file_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="Pointer to equity_curve JSON in Supabase Storage",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["UserModel | None"] = relationship(back_populates="backtests")
    strategy: Mapped["StrategyModel"] = relationship(back_populates="backtests")

    def __repr__(self) -> str:
        return f"<Backtest id={self.id} symbol={self.symbol} timeframe={self.timeframe}>"
