from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import AppSettings
from app.models.enums import JobStatus
from app.models.job import Job
from app.models.job_event import JobEvent


class JobProgressReporter:
    def __init__(self, session: Session, settings: AppSettings) -> None:
        self._session = session
        self._settings = settings

    def mark_processing(
        self,
        job: Job,
        *,
        progress: int,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        job.status = JobStatus.PROCESSING
        job.progress = progress
        job.started_at = job.started_at or now
        job.error_code = None
        job.error_message = None
        self._add_event(job=job, status=JobStatus.PROCESSING, progress=progress, message=message, metadata=metadata)
        self._session.add(job)
        self._session.commit()

    def mark_progress(
        self,
        job: Job,
        *,
        progress: int,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        job.status = JobStatus.PROCESSING
        job.progress = progress
        self._add_event(job=job, status=JobStatus.PROCESSING, progress=progress, message=message, metadata=metadata)
        self._session.add(job)
        self._session.commit()

    def mark_completed(
        self,
        job: Job,
        *,
        progress: int,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        completed_at = datetime.now(timezone.utc)
        job.status = JobStatus.COMPLETED
        job.progress = progress
        job.completed_at = completed_at
        job.expires_at = completed_at + timedelta(minutes=self._settings.retention_minutes)
        self._add_event(job=job, status=JobStatus.COMPLETED, progress=progress, message=message, metadata=metadata)
        self._session.add(job)
        self._session.commit()

    def mark_failed(
        self,
        job: Job,
        *,
        error_code: str,
        error_message: str,
        message: str,
        progress: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        completed_at = datetime.now(timezone.utc)
        job.status = JobStatus.FAILED
        job.progress = progress
        job.started_at = job.started_at or completed_at
        job.completed_at = completed_at
        job.error_code = error_code
        job.error_message = error_message
        self._add_event(job=job, status=JobStatus.FAILED, progress=progress, message=message, metadata=metadata)
        self._session.add(job)
        self._session.commit()

    def _add_event(
        self,
        *,
        job: Job,
        status: JobStatus,
        progress: int,
        message: str,
        metadata: dict[str, Any] | None,
    ) -> None:
        self._session.add(
            JobEvent(
                job_id=job.id,
                status=status,
                progress=progress,
                message=message,
                metadata_json=metadata,
            )
        )
