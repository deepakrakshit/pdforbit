"""Update credit policy to daily quotas and AI task pricing.

Revision ID: 20260311_0004
Revises: 20260307_0003
Create Date: 2026-03-11 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260311_0004"
down_revision = "20260307_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("credits_remaining", server_default="30")

    op.execute(
        sa.text(
            "UPDATE users "
            "SET credits_remaining = CASE "
            "WHEN is_admin IS TRUE THEN 999999999 "
            "WHEN plan = 'pro' THEN 1000 "
            "WHEN plan = 'enterprise' THEN 10000 "
            "ELSE 30 END"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("credits_remaining", server_default="10")

    op.execute(
        sa.text(
            "UPDATE users "
            "SET credits_remaining = CASE "
            "WHEN is_admin IS TRUE THEN 999999999 "
            "WHEN plan = 'pro' THEN 200 "
            "WHEN plan = 'enterprise' THEN 10000 "
            "ELSE 10 END"
        )
    )