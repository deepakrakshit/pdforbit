"""Add billing subscriptions and payment audit records.

Revision ID: 20260311_0005
Revises: 20260311_0004
Create Date: 2026-03-11 18:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260311_0005"
down_revision = "20260311_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    subscription_status = sa.Enum(
        "inactive",
        "active",
        "cancelled",
        "expired",
        name="subscription_status",
        native_enum=False,
        create_constraint=True,
    )
    subscription_interval = sa.Enum(
        "monthly",
        "yearly",
        name="subscription_interval",
        native_enum=False,
        create_constraint=True,
    )
    payment_provider = sa.Enum(
        "razorpay",
        name="payment_provider",
        native_enum=False,
        create_constraint=True,
    )
    payment_status = sa.Enum(
        "created",
        "authorized",
        "captured",
        "cancelled",
        "failed",
        "refunded",
        name="payment_status",
        native_enum=False,
        create_constraint=True,
    )
    billing_plan_code = sa.Enum(
        "PRO_MONTHLY",
        "PRO_YEARLY",
        name="billing_plan_code",
        native_enum=False,
        create_constraint=True,
    )
    billing_subscription_interval = sa.Enum(
        "monthly",
        "yearly",
        name="billing_subscription_interval",
        native_enum=False,
        create_constraint=True,
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "subscription_status",
                subscription_status,
                nullable=False,
                server_default="inactive",
            )
        )
        batch_op.add_column(sa.Column("subscription_interval", subscription_interval, nullable=True))
        batch_op.add_column(sa.Column("subscription_started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "billing_payments",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", payment_provider, nullable=False, server_default="razorpay"),
        sa.Column("plan_code", billing_plan_code, nullable=False),
        sa.Column("subscription_interval", billing_subscription_interval, nullable=False),
        sa.Column("status", payment_status, nullable=False, server_default="created"),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="INR"),
        sa.Column("provider_order_id", sa.String(length=64), nullable=True),
        sa.Column("provider_payment_id", sa.String(length=64), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=64), nullable=True),
        sa.Column("receipt", sa.String(length=128), nullable=True),
        sa.Column("signature_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_paise >= 0", name=op.f("ck_billing_payments_billing_payment_amount_non_negative")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_billing_payments_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_payments")),
        sa.UniqueConstraint("provider_order_id", name=op.f("uq_billing_payments_provider_order_id")),
        sa.UniqueConstraint("provider_payment_id", name=op.f("uq_billing_payments_provider_payment_id")),
        sa.UniqueConstraint("receipt", name=op.f("uq_billing_payments_receipt")),
    )
    op.create_index(op.f("ix_billing_payments_user_id"), "billing_payments", ["user_id"], unique=False)
    op.create_index(op.f("ix_billing_payments_provider_order_id"), "billing_payments", ["provider_order_id"], unique=False)
    op.create_index(op.f("ix_billing_payments_provider_payment_id"), "billing_payments", ["provider_payment_id"], unique=False)
    op.create_index(op.f("ix_billing_payments_provider_subscription_id"), "billing_payments", ["provider_subscription_id"], unique=False)
    op.create_index(op.f("ix_billing_payments_receipt"), "billing_payments", ["receipt"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_billing_payments_receipt"), table_name="billing_payments")
    op.drop_index(op.f("ix_billing_payments_provider_subscription_id"), table_name="billing_payments")
    op.drop_index(op.f("ix_billing_payments_provider_payment_id"), table_name="billing_payments")
    op.drop_index(op.f("ix_billing_payments_provider_order_id"), table_name="billing_payments")
    op.drop_index(op.f("ix_billing_payments_user_id"), table_name="billing_payments")
    op.drop_table("billing_payments")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("subscription_expires_at")
        batch_op.drop_column("subscription_started_at")
        batch_op.drop_column("subscription_interval")
        batch_op.drop_column("subscription_status")