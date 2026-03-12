from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import AppSettings
from app.db.repositories.job import JobRepository
from app.db.repositories.upload import UploadRepository
from app.db.session import DatabaseManager
from app.models.artifact import JobArtifact
from app.models.enums import JobStatus, UploadStatus
from app.models.job import Job
from app.models.job_event import JobEvent
from app.services.queue_service import QueueService
from app.services.storage_service import StorageService
from app.workers.progress import JobProgressReporter


@dataclass(frozen=True)
class CleanupSummary:
    expired_uploads: int = 0
    expired_artifacts: int = 0
    expired_jobs: int = 0
    requeued_jobs: int = 0
    failed_jobs: int = 0
    pruned_temp_paths: int = 0


class CleanupService:
    def __init__(
        self,
        *,
        settings: AppSettings,
        database_manager: DatabaseManager,
        queue_service: QueueService,
        storage_service: StorageService,
    ) -> None:
        self._settings = settings
        self._database_manager = database_manager
        self._queue = queue_service
        self._storage = storage_service
        self._logger = logging.getLogger("app.cleanup")

    def run_cycle(self) -> CleanupSummary:
        now = datetime.now(timezone.utc)
        with self._database_manager.session_scope() as session:
            uploads = UploadRepository(session)
            jobs = JobRepository(session)
            reporter = JobProgressReporter(session=session, settings=self._settings)

            expired_uploads = self._expire_uploads(uploads=uploads, now=now)
            expired_artifacts, expired_jobs = self._expire_artifacts(session=session, now=now)
            requeued_jobs = self._requeue_stale_pending_jobs(jobs=jobs, now=now)
            failed_jobs = self._fail_stale_processing_jobs(jobs=jobs, reporter=reporter, now=now)

        pruned_temp_paths = self._prune_temp_paths(now=now)

        summary = CleanupSummary(
            expired_uploads=expired_uploads,
            expired_artifacts=expired_artifacts,
            expired_jobs=expired_jobs,
            requeued_jobs=requeued_jobs,
            failed_jobs=failed_jobs,
            pruned_temp_paths=pruned_temp_paths,
        )
        self._logger.info("cleanup.completed", extra=summary.__dict__)
        return summary

    def _expire_uploads(self, *, uploads: UploadRepository, now: datetime) -> int:
        expired = uploads.list_expired_active(before=now)
        for upload in expired:
            self._storage.delete(relative_path=upload.storage_path)
            upload.status = UploadStatus.EXPIRED
            upload.deleted_at = now
            uploads.add(upload)
        return len(expired)

    def _expire_artifacts(self, *, session, now: datetime) -> tuple[int, int]:
        statement = (
            select(JobArtifact)
            .where(JobArtifact.deleted_at.is_(None), JobArtifact.expires_at <= now)
            .options(selectinload(JobArtifact.job).selectinload(Job.events))
            .order_by(JobArtifact.expires_at.asc())
        )
        artifacts = list(session.scalars(statement))
        expired_jobs: set[str] = set()

        for artifact in artifacts:
            self._storage.delete(relative_path=artifact.storage_path)
            artifact.deleted_at = now
            session.add(artifact)

            job = artifact.job
            if job is None or job.public_id in expired_jobs:
                continue

            job.status = JobStatus.EXPIRED
            job.error_code = "result_expired"
            job.error_message = "Result has expired."
            job.expires_at = now
            session.add(job)
            session.add(
                JobEvent(
                    job_id=job.id,
                    status=JobStatus.EXPIRED,
                    progress=job.progress,
                    message="Result expired and was removed by cleanup.",
                    metadata_json={"artifact_id": str(artifact.id)},
                )
            )
            expired_jobs.add(job.public_id)

        return len(artifacts), len(expired_jobs)

    def _requeue_stale_pending_jobs(self, *, jobs: JobRepository, now: datetime) -> int:
        threshold = now - timedelta(seconds=self._settings.stale_job_threshold_seconds)
        stale_jobs = jobs.list_stale_pending(before=threshold)
        requeued = 0

        for job in stale_jobs:
            rq_job = self._queue.get_job(job.public_id)
            status = rq_job.get_status(refresh=True) if rq_job is not None else None
            if status in {"queued", "started", "deferred", "scheduled"}:
                continue

            if rq_job is not None:
                self._queue.delete_job(job.public_id)

            self._queue.enqueue_job(job_id=job.public_id, queue_name=job.queue_name, tool_id=job.tool_id)
            job.events.append(
                JobEvent(
                    status=JobStatus.PENDING,
                    progress=job.progress,
                    message="Pending job was requeued during cleanup reconciliation.",
                    metadata_json={"reconciled": True},
                )
            )
            jobs.add(job)
            requeued += 1

        return requeued

    def _fail_stale_processing_jobs(
        self,
        *,
        jobs: JobRepository,
        reporter: JobProgressReporter,
        now: datetime,
    ) -> int:
        threshold = now - timedelta(seconds=self._settings.stale_job_threshold_seconds)
        stale_jobs = jobs.list_stale_processing(before=threshold)
        failed = 0

        for job in stale_jobs:
            rq_job = self._queue.get_job(job.public_id)
            status = rq_job.get_status(refresh=True) if rq_job is not None else None
            if status in {"queued", "started", "deferred", "scheduled"}:
                continue

            reporter.mark_failed(
                job,
                error_code="stale_job_recovered",
                error_message="Job processing was interrupted and has been marked as failed.",
                message="Cleanup reconciliation marked the stale processing job as failed.",
                progress=job.progress,
                metadata={"reconciled": True, "rq_status": status},
            )
            failed += 1

        return failed

    def _prune_temp_paths(self, *, now: datetime) -> int:
        tmp_root = self._storage.root / "tmp"
        if not tmp_root.exists():
            return 0

        threshold = now - timedelta(seconds=self._settings.stale_job_threshold_seconds)
        pruned = 0

        for path in sorted(tmp_root.rglob("*"), reverse=True):
            try:
                modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            except FileNotFoundError:
                continue

            if modified_at > threshold:
                continue

            if path.is_file():
                path.unlink(missing_ok=True)
                pruned += 1
            elif path.is_dir():
                try:
                    path.rmdir()
                    pruned += 1
                except OSError:
                    continue

        return pruned