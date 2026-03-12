from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.db.types import JSONVariant, enum_type
from app.models.enums import JobStatus

if TYPE_CHECKING:
    from app.models.job import Job


class JobEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "job_events"
    __table_args__ = (
        CheckConstraint(
            "progress IS NULL OR (progress >= 0 AND progress <= 100)",
            name="progress_nullable_range",
        ),
    )

    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[JobStatus] = mapped_column(
        enum_type(JobStatus, "job_event_status"),
        nullable=False,
        index=True,
    )
    progress: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job: Mapped["Job"] = relationship(back_populates="events")
