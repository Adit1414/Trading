"""Make bots.user_id non-nullable (Module 1 Auth active)

Now that Module 1 (Auth) is implemented, every bot must be linked to a
real authenticated user.  This migration removes the nullable allowance
that was added in 0004 for the pre-auth phase.

Pre-condition: any existing bots with user_id = NULL should be deleted or
reassigned before running this migration, otherwise it will fail.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-02
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("MIGRATION 0006: Making bots.user_id non-nullable")
    # Delete any orphaned bots (created during pre-auth phase) to avoid
    # a NOT NULL constraint violation on existing rows.
    op.execute("DELETE FROM bots WHERE user_id IS NULL")
    op.alter_column("bots", "user_id", nullable=False)
    print("MIGRATION 0006: Done")


def downgrade() -> None:
    op.alter_column("bots", "user_id", nullable=True)
