"""Add chart_html column to backtests table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-02
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("MIGRATION 0002: Adding chart_html column to backtests")
    op.add_column(
        "backtests",
        sa.Column(
            "chart_html",
            sa.Text,
            nullable=True,
            comment="Self-contained Plotly HTML chart for this backtest run",
        ),
    )
    print("MIGRATION 0002: Done")


def downgrade() -> None:
    op.drop_column("backtests", "chart_html")
