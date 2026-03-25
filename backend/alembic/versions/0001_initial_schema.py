"""Initial schema — all tables per DatabaseSchema.svg

Revision ID: 0001
Revises: 
Create Date: 2026-03-24
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("MIGRATION: Creating users table")
    # ── USERS ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",         UUID(as_uuid=False), primary_key=True),
        sa.Column("email",      sa.String(255),      nullable=False, unique=True),
        sa.Column("created_at", TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"])

    print("MIGRATION: Creating api_credentials table")
    # ── API_CREDENTIALS ───────────────────────────────────────────────────────
    # environment CHECK: MAINNET or TESTNET
    op.create_table(
        "api_credentials",
        sa.Column("id",              UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id",         UUID(as_uuid=False),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("environment",     sa.String(16),  nullable=False),
        sa.Column("vault_secret_id", UUID(as_uuid=False), nullable=False),
        sa.Column("created_at",      TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "environment", name="uq_api_creds_user_env"),
        sa.CheckConstraint(
            "environment IN ('MAINNET', 'TESTNET')",
            name="ck_api_creds_environment",
        ),
    )
    op.create_index("ix_api_credentials_user_id", "api_credentials", ["user_id"])

    print("MIGRATION: Creating strategies table")
    # ── STRATEGIES ────────────────────────────────────────────────────────────
    op.create_table(
        "strategies",
        sa.Column("id",               UUID(as_uuid=False), primary_key=True),
        sa.Column("name",             sa.String(120),  nullable=False),
        sa.Column("type_code",        sa.String(64),   nullable=False, unique=True),
        sa.Column("parameter_schema", JSONB,           nullable=False),
        sa.Column("description",      sa.Text,         nullable=True),
    )
    op.create_index("ix_strategies_type_code", "strategies", ["type_code"])

    print("MIGRATION: Creating bots table")
    # ── BOTS ──────────────────────────────────────────────────────────────────
    # status CHECK: RUNNING | STOPPED | PAUSED_LIMIT_REACHED
    # environment CHECK: MAINNET | TESTNET
    op.create_table(
        "bots",
        sa.Column("id",                    UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id",               UUID(as_uuid=False),
                  sa.ForeignKey("users.id",      ondelete="CASCADE"),  nullable=False),
        sa.Column("strategy_id",           UUID(as_uuid=False),
                  sa.ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name",                  sa.String(120), nullable=False),
        sa.Column("environment",           sa.String(16),  nullable=False),
        sa.Column("status",                sa.String(32),  nullable=False,
                  server_default="STOPPED"),
        sa.Column("trade_quantity",        sa.Numeric(20, 8), nullable=True),
        sa.Column("daily_pnl_upper_limit", sa.Numeric(20, 8), nullable=True),
        sa.Column("daily_pnl_lower_limit", sa.Numeric(20, 8), nullable=True),
        sa.Column("parameters",            JSONB, nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at",            TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",            TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "environment IN ('MAINNET', 'TESTNET')",
            name="ck_bots_environment",
        ),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'STOPPED', 'PAUSED_LIMIT_REACHED')",
            name="ck_bots_status",
        ),
    )
    op.create_index("ix_bots_user_id",     "bots", ["user_id"])
    op.create_index("ix_bots_strategy_id", "bots", ["strategy_id"])

    print("MIGRATION: Creating bot_state table")
    # ── BOT_STATE ─────────────────────────────────────────────────────────────
    # bot_id is both PK and FK → enforces strict 1-to-1 with BOTS
    # current_position CHECK: LONG | SHORT | FLAT
    op.create_table(
        "bot_state",
        sa.Column("bot_id",                   UUID(as_uuid=False),
                  sa.ForeignKey("bots.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("current_position",         sa.String(8), nullable=False,
                  server_default="FLAT"),
        sa.Column("active_quantity",          sa.Numeric(20, 8), nullable=False,
                  server_default="0"),
        sa.Column("average_entry_price",      sa.Numeric(20, 8), nullable=False,
                  server_default="0"),
        sa.Column("daily_realized_pnl",       sa.Numeric(20, 8), nullable=False,
                  server_default="0"),
        sa.Column("daily_unrealized_pnl",     sa.Numeric(20, 8), nullable=False,
                  server_default="0"),
        sa.Column("last_pnl_reset_timestamp", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updated_at",               TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "current_position IN ('LONG', 'SHORT', 'FLAT')",
            name="ck_bot_state_position",
        ),
    )

    print("MIGRATION: Creating trade_logs table")
    # ── TRADE_LOGS ────────────────────────────────────────────────────────────
    # bot_id nullable → NULL means manual trade
    # side CHECK: BUY | SELL
    # environment CHECK: MAINNET | TESTNET
    op.create_table(
        "trade_logs",
        sa.Column("id",              UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id",         UUID(as_uuid=False),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bot_id",          UUID(as_uuid=False),
                  sa.ForeignKey("bots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_manual_trade", sa.Boolean, nullable=False,
                  server_default=sa.text("false")),
        sa.Column("symbol",          sa.String(20), nullable=False),
        sa.Column("side",            sa.String(4),  nullable=False),
        sa.Column("quantity",        sa.Numeric(20, 8), nullable=False),
        sa.Column("execution_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("environment",     sa.String(16), nullable=False),
        sa.Column("executed_at",     TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "side IN ('BUY', 'SELL')",
            name="ck_trade_logs_side",
        ),
        sa.CheckConstraint(
            "environment IN ('MAINNET', 'TESTNET')",
            name="ck_trade_logs_environment",
        ),
        sa.CheckConstraint(
            "(bot_id IS NULL AND is_manual_trade = true) OR "
            "(bot_id IS NOT NULL AND is_manual_trade = false) OR "
            "(bot_id IS NULL AND is_manual_trade = false)",
            name="ck_trade_logs_manual_consistency",
        ),
    )
    op.create_index("ix_trade_logs_user_id",    "trade_logs", ["user_id"])
    op.create_index("ix_trade_logs_bot_id",     "trade_logs", ["bot_id"])
    op.create_index("ix_trade_logs_executed_at","trade_logs", ["executed_at"])

    print("MIGRATION: Creating backtests table")
    # ── BACKTESTS ─────────────────────────────────────────────────────────────
    # user_id nullable → pre-auth phase; set NULL on user delete (preserve history)
    op.create_table(
        "backtests",
        sa.Column("id",              UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id",         UUID(as_uuid=False),
                  sa.ForeignKey("users.id",      ondelete="SET NULL"), nullable=True),
        sa.Column("strategy_id",     UUID(as_uuid=False),
                  sa.ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("symbol",          sa.String(20), nullable=False),
        sa.Column("timeframe",       sa.String(8),  nullable=False),
        sa.Column("parameters",      JSONB, nullable=False),
        sa.Column("metrics",         JSONB, nullable=False),
        sa.Column("result_file_url", sa.String(512), nullable=True),
        sa.Column("created_at",      TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_backtests_user_id",     "backtests", ["user_id"])
    op.create_index("ix_backtests_strategy_id", "backtests", ["strategy_id"])
    op.create_index("ix_backtests_symbol",      "backtests", ["symbol"])
    op.create_index("ix_backtests_created_at",  "backtests", ["created_at"])
    print("MIGRATION: Finished all tables")


def downgrade() -> None:
    op.drop_table("backtests")
    op.drop_table("trade_logs")
    op.drop_table("bot_state")
    op.drop_table("bots")
    op.drop_table("strategies")
    op.drop_table("api_credentials")
    op.drop_table("users")
