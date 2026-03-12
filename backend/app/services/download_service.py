from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import AppSettings
from app.db.repositories.job import JobRepository
from app.models.artifact import JobArtifact
from app.models.enums import JobStatus
from app.models.job import Job
from app.services.storage_service import StorageService


@dataclass(frozen=True)
class ResolvedDownload:
    job: Job
    artifact: JobArtifact
    file_path: Path


def ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class DownloadService:
    def __init__(self, *, settings: AppSettings, storage_service: StorageService) -> None:
        self._settings = settings
        self._storage = storage_service

    def build_download_url(self, *, job: Job, artifact: JobArtifact | None = None) -> str | None:
        active_artifact = artifact or self.get_active_artifact(job)
        if active_artifact is None:
            return None
        if job.status != JobStatus.COMPLETED:
            return None

        now = datetime.now(timezone.utc)
        artifact_expires_at = ensure_utc_datetime(active_artifact.expires_at)
        if artifact_expires_at <= now:
            return None

        expiration = min(
            int(artifact_expires_at.timestamp()),
            int(now.timestamp()) + self._settings.download_url_ttl_seconds,
        )
        signature = self._sign(
            job_id=job.public_id,
            artifact_sha256=active_artifact.sha256,
            expiration=expiration,
        )
        return f"{self._settings.api_v1_prefix}/download/{job.public_id}?exp={expiration}&sig={signature}"

    def resolve_download(
        self,
        *,
        session: Session,
        job_id: str,
        expiration: int,
        signature: str,
    ) -> ResolvedDownload:
        now_timestamp = int(datetime.now(timezone.utc).timestamp())
        if expiration < now_timestamp:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Download link has expired.",
            )

        jobs = JobRepository(session)
        job = jobs.get_by_public_id(job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Result is not ready for download.",
            )

        artifact = self.get_active_artifact(job)
        if artifact is None:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Result is no longer available.",
            )

        expected_signature = self._sign(
            job_id=job.public_id,
            artifact_sha256=artifact.sha256,
            expiration=expiration,
        )
        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Download signature is invalid.",
            )

        artifact_expires_at = ensure_utc_datetime(artifact.expires_at)
        if artifact_expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Result is no longer available.",
            )

        file_path = self._storage.resolve_path(relative_path=artifact.storage_path)
        if not file_path.exists() or artifact.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Result is no longer available.",
            )

        return ResolvedDownload(job=job, artifact=artifact, file_path=file_path)

    @staticmethod
    def get_active_artifact(job: Job) -> JobArtifact | None:
        for artifact in job.artifacts:
            if artifact.deleted_at is None:
                return artifact
        return None

    def _sign(self, *, job_id: str, artifact_sha256: str, expiration: int) -> str:
        payload = f"{job_id}:{artifact_sha256}:{expiration}".encode("utf-8")
        return hmac.new(
            self._settings.download_signing_secret.encode("utf-8"),
            payload,
            digestmod=hashlib.sha256,
        ).hexdigest()
