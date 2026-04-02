"""Add symbol column to bots table

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-02
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("MIGRATION 0003: Adding symbol column to bots")
    op.add_column(
        "bots",
        sa.Column(
            "symbol",
            sa.String(20),
            nullable=True,       # nullable during migration; existing rows get NULL
            comment="Trading pair, e.g. BTCUSDT",
        ),
    )
    # Back-fill existing rows with a placeholder so we can enforce NOT NULL later
    op.execute("UPDATE bots SET symbol = 'UNKNOWN' WHERE symbol IS NULL")
    op.alter_column("bots", "symbol", nullable=False)
    print("MIGRATION 0003: Done")


def downgrade() -> None:
    op.drop_column("bots", "symbol")
