"""Actually drop bots.strategy_id foreign key

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-02
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("MIGRATION 0005: Dropping bots_strategy_id_fkey constraint")
    op.drop_constraint("bots_strategy_id_fkey", "bots", type_="foreignkey")
    print("MIGRATION 0005: Done")


def downgrade() -> None:
    op.create_foreign_key(
        "bots_strategy_id_fkey",
        "bots",
        "strategies",
        ["strategy_id"],
        ["id"],
        ondelete="RESTRICT",
    )
