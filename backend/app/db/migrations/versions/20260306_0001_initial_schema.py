"""Initial relational schema for PdfORBIT backend.

Revision ID: 20260306_0001
Revises: None
Create Date: 2026-03-06 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.db.types import JSONVariant

# revision identifiers, used by Alembic.
revision = "20260306_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_plan = sa.Enum(
        "free",
        "pro",
        "enterprise",
        name="user_plan",
        native_enum=False,
        create_constraint=True,
    )
    upload_status = sa.Enum(
        "uploaded",
        "in_use",
        "expired",
        "deleted",
        "quarantined",
        name="upload_status",
        native_enum=False,
        create_constraint=True,
    )
    job_status = sa.Enum(
        "pending",
        "processing",
        "completed",
        "failed",
        "expired",
        name="job_status",
        native_enum=False,
        create_constraint=True,
    )
    artifact_kind = sa.Enum(
        "result",
        "archive",
        "preview",
        name="artifact_kind",
        native_enum=False,
        create_constraint=True,
    )
    job_event_status = sa.Enum(
        "pending",
        "processing",
        "completed",
        "failed",
        "expired",
        name="job_event_status",
        native_enum=False,
        create_constraint=True,
    )

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("plan", user_plan, nullable=False, server_default="free"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "jobs",
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("public_id", sa.String(length=64), nullable=False),
        sa.Column("tool_id", sa.String(length=64), nullable=False),
        sa.Column("queue_name", sa.String(length=64), nullable=False),
        sa.Column("status", job_status, nullable=False, server_default="pending"),
        sa.Column("progress", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("request_payload", JSONVariant, nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name=op.f("ck_jobs_progress_range")),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], name=op.f("fk_jobs_owner_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index(op.f("ix_jobs_expires_at"), "jobs", ["expires_at"], unique=False)
    op.create_index(op.f("ix_jobs_owner_user_id"), "jobs", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_jobs_public_id"), "jobs", ["public_id"], unique=True)
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)
    op.create_index(op.f("ix_jobs_tool_id"), "jobs", ["tool_id"], unique=False)

    op.create_table(
        "uploads",
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("public_id", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=32), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("is_pdf", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_encrypted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", upload_status, nullable=False, server_default="uploaded"),
        sa.Column("metadata", JSONVariant, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("page_count IS NULL OR page_count > 0", name=op.f("ck_uploads_page_count_positive")),
        sa.CheckConstraint("size_bytes >= 0", name=op.f("ck_uploads_size_bytes_non_negative")),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], name=op.f("fk_uploads_owner_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_uploads")),
        sa.UniqueConstraint("storage_path", name=op.f("uq_uploads_storage_path")),
    )
    op.create_index(op.f("ix_uploads_deleted_at"), "uploads", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_uploads_expires_at"), "uploads", ["expires_at"], unique=False)
    op.create_index(op.f("ix_uploads_owner_user_id"), "uploads", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_uploads_public_id"), "uploads", ["public_id"], unique=True)
    op.create_index(op.f("ix_uploads_sha256"), "uploads", ["sha256"], unique=False)
    op.create_index(op.f("ix_uploads_status"), "uploads", ["status"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("issued_from_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_refresh_tokens_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
    )
    op.create_index(op.f("ix_refresh_tokens_expires_at"), "refresh_tokens", ["expires_at"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "job_artifacts",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("kind", artifact_kind, nullable=False, server_default="result"),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("metadata", JSONVariant, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("size_bytes >= 0", name=op.f("ck_job_artifacts_size_bytes_non_negative")),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name=op.f("fk_job_artifacts_job_id_jobs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_artifacts")),
        sa.UniqueConstraint("storage_path", name=op.f("uq_job_artifacts_storage_path")),
    )
    op.create_index(op.f("ix_job_artifacts_deleted_at"), "job_artifacts", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_job_artifacts_expires_at"), "job_artifacts", ["expires_at"], unique=False)
    op.create_index(op.f("ix_job_artifacts_job_id"), "job_artifacts", ["job_id"], unique=False)
    op.create_index(op.f("ix_job_artifacts_sha256"), "job_artifacts", ["sha256"], unique=False)

    op.create_table(
        "job_events",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("status", job_event_status, nullable=False),
        sa.Column("progress", sa.SmallInteger(), nullable=True),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column("metadata", JSONVariant, nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "progress IS NULL OR (progress >= 0 AND progress <= 100)",
            name=op.f("ck_job_events_progress_nullable_range"),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name=op.f("fk_job_events_job_id_jobs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_events")),
    )
    op.create_index(op.f("ix_job_events_job_id"), "job_events", ["job_id"], unique=False)
    op.create_index(op.f("ix_job_events_status"), "job_events", ["status"], unique=False)

    op.create_table(
        "job_inputs",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("upload_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("position >= 0", name=op.f("ck_job_inputs_position_non_negative")),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name=op.f("fk_job_inputs_job_id_jobs"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], name=op.f("fk_job_inputs_upload_id_uploads"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_inputs")),
        sa.UniqueConstraint("job_id", "position", name="uq_job_inputs_job_position"),
    )
    op.create_index(op.f("ix_job_inputs_job_id"), "job_inputs", ["job_id"], unique=False)
    op.create_index(op.f("ix_job_inputs_upload_id"), "job_inputs", ["upload_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_job_inputs_upload_id"), table_name="job_inputs")
    op.drop_index(op.f("ix_job_inputs_job_id"), table_name="job_inputs")
    op.drop_table("job_inputs")

    op.drop_index(op.f("ix_job_events_status"), table_name="job_events")
    op.drop_index(op.f("ix_job_events_job_id"), table_name="job_events")
    op.drop_table("job_events")

    op.drop_index(op.f("ix_job_artifacts_sha256"), table_name="job_artifacts")
    op.drop_index(op.f("ix_job_artifacts_job_id"), table_name="job_artifacts")
    op.drop_index(op.f("ix_job_artifacts_expires_at"), table_name="job_artifacts")
    op.drop_index(op.f("ix_job_artifacts_deleted_at"), table_name="job_artifacts")
    op.drop_table("job_artifacts")

    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_token_hash"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_expires_at"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index(op.f("ix_uploads_status"), table_name="uploads")
    op.drop_index(op.f("ix_uploads_sha256"), table_name="uploads")
    op.drop_index(op.f("ix_uploads_public_id"), table_name="uploads")
    op.drop_index(op.f("ix_uploads_owner_user_id"), table_name="uploads")
    op.drop_index(op.f("ix_uploads_expires_at"), table_name="uploads")
    op.drop_index(op.f("ix_uploads_deleted_at"), table_name="uploads")
    op.drop_table("uploads")

    op.drop_index(op.f("ix_jobs_tool_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_public_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_owner_user_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_expires_at"), table_name="jobs")
    op.drop_table("jobs")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

