"""Relax bots constraints for pre-auth phase

  - Make bots.user_id nullable (no auth yet)
  - Add 'PAUSED' to the status CHECK constraint
  - Drop FK constraint on bots.strategy_id to allow any UUID (strategy seeding may vary)

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-02
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("MIGRATION 0004: Relaxing bots constraints")

    # 1. Make user_id nullable (pre-auth phase — no logged-in user yet)
    op.alter_column("bots", "user_id", nullable=True)

    # 2. Drop old status CHECK and add a new one that also permits 'PAUSED'
    op.drop_constraint("ck_bots_status", "bots", type_="check")
    op.create_check_constraint(
        "ck_bots_status",
        "bots",
        "status IN ('RUNNING', 'STOPPED', 'PAUSED_LIMIT_REACHED', 'PAUSED')",
    )

    print("MIGRATION 0004: Done")


def downgrade() -> None:
    op.drop_constraint("ck_bots_status", "bots", type_="check")
    op.create_check_constraint(
        "ck_bots_status",
        "bots",
        "status IN ('RUNNING', 'STOPPED', 'PAUSED_LIMIT_REACHED')",
    )
    op.alter_column("bots", "user_id", nullable=False)
