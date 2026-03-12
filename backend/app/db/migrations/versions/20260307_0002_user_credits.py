"""Add persistent user credits and refresh timestamp.

Revision ID: 20260307_0002
Revises: 20260306_0001
Create Date: 2026-03-07 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260307_0002"
down_revision = "20260306_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("credits_remaining", sa.Integer(), nullable=False, server_default="10"),
    )
    op.add_column(
        "users",
        sa.Column(
            "last_credit_refresh",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.execute(
        sa.text(
            "UPDATE users "
            "SET credits_remaining = CASE WHEN plan = 'pro' THEN 200 WHEN plan = 'enterprise' THEN 10000 ELSE 10 END"
        )
    )
def downgrade() -> None:
    op.drop_column("users", "last_credit_refresh")
    op.drop_column("users", "credits_remaining")