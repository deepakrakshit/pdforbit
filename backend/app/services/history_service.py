from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.repositories.job import JobRepository
from app.db.repositories.upload import UploadRepository
from app.models.enums import UploadStatus
from app.models.job import Job
from app.models.upload import Upload
from app.models.user import User
from app.schemas.history import (
    HistoryPagination,
    JobHistoryItem,
    JobHistoryListResponse,
    UploadHistoryItem,
    UploadHistoryListResponse,
)
from app.services.download_service import DownloadService
from app.services.job_service import FRONTEND_STATUS_MAP


@dataclass(frozen=True)
class PaginationParams:
    limit: int
    offset: int


class HistoryService:
    def __init__(
        self,
        *,
        session: Session,
        download_service: DownloadService,
    ) -> None:
        self._session = session
        self._downloads = download_service
        self._jobs = JobRepository(session)
        self._uploads = UploadRepository(session)

    def list_jobs(self, *, owner: User, limit: int, offset: int) -> JobHistoryListResponse:
        items = self._jobs.list_by_owner(owner_id=owner.id, limit=limit, offset=offset)
        total = self._jobs.count_by_owner(owner_id=owner.id)
        return JobHistoryListResponse(
            items=[self._serialize_job(job) for job in items],
            pagination=HistoryPagination(total=total, limit=limit, offset=offset),
        )

    def list_uploads(self, *, owner: User, limit: int, offset: int) -> UploadHistoryListResponse:
        items = self._uploads.list_by_owner(owner_id=owner.id, limit=limit, offset=offset)
        total = self._uploads.count_by_owner(owner_id=owner.id)
        return UploadHistoryListResponse(
            items=[self._serialize_upload(upload) for upload in items],
            pagination=HistoryPagination(total=total, limit=limit, offset=offset),
        )

    def _serialize_job(self, job: Job) -> JobHistoryItem:
        artifact = self._downloads.get_active_artifact(job)
        artifact_metadata = artifact.metadata_json if artifact and artifact.metadata_json else {}
        download_url = self._downloads.build_download_url(job=job, artifact=artifact)
        return JobHistoryItem(
            job_id=job.public_id,
            tool_id=job.tool_id,
            status=FRONTEND_STATUS_MAP[job.status],
            progress=job.progress,
            error=job.error_message,
            created_at=job.created_at,
            completed_at=job.completed_at,
            expires_at=artifact.expires_at if artifact is not None else job.expires_at,
            download_url=download_url,
            result_url=download_url,
            original_bytes=artifact_metadata.get("original_bytes"),
            compressed_bytes=artifact_metadata.get("compressed_bytes"),
            savings_pct=artifact_metadata.get("savings_pct"),
            pages_processed=artifact_metadata.get("pages_processed"),
            parts_count=artifact_metadata.get("parts_count"),
            redactions_applied=artifact_metadata.get("redactions_applied"),
            different_pages=artifact_metadata.get("different_pages"),
            detected_language=artifact_metadata.get("detected_language"),
            word_count=artifact_metadata.get("word_count"),
        )

    @staticmethod
    def _serialize_upload(upload: Upload) -> UploadHistoryItem:
        return UploadHistoryItem(
            file_id=upload.public_id,
            filename=upload.original_filename,
            content_type=upload.content_type,
            extension=upload.extension,
            size_bytes=upload.size_bytes,
            page_count=upload.page_count,
            is_pdf=upload.is_pdf,
            is_encrypted=upload.is_encrypted,
            status=upload.status.value,
            created_at=upload.created_at,
            expires_at=upload.expires_at,
            deleted_at=upload.deleted_at,
        )
