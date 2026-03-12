from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

from sqlalchemy.orm import Session

from app.core.config import AppSettings
from app.db.repositories.job import JobRepository
from app.models.artifact import JobArtifact
from app.models.job import Job
from app.models.job_input import JobInput
from app.services.pdf import GeneratedArtifact, JobInputFile, PdfJobProcessor, PdfProcessingError, ProcessorContext
from app.services.pdf.common import enrich_processing_result
from app.services.pdf.policy import validate_processing_context
from app.services.storage_service import StorageService
from app.workers.progress import JobProgressReporter


@dataclass(frozen=True)
class PersistedArtifact:
    record: JobArtifact
    relative_path: str


class JobExecutionService:
    def __init__(
        self,
        *,
        session: Session,
        settings: AppSettings,
        storage_service: StorageService,
    ) -> None:
        self._session = session
        self._settings = settings
        self._storage = storage_service
        self._jobs = JobRepository(session)
        self._reporter = JobProgressReporter(session=session, settings=settings)
        self._processor = PdfJobProcessor(settings)
        self._logger = logging.getLogger("app.worker")

    def execute(self, *, job_id: str, tool_id: str) -> None:
        job = self._jobs.get_by_public_id(job_id)
        if job is None:
            self._logger.warning("worker.job_missing", extra={"job_id": job_id, "tool_id": tool_id})
            return

        workspace = self._storage.create_job_workspace(job_public_id=job.public_id)
        persisted_artifact: PersistedArtifact | None = None

        try:
            self._reporter.mark_processing(
                job,
                progress=10,
                message="Worker started processing the PDF job.",
                metadata={"tool_id": tool_id},
            )

            context = self._build_context(job=job, workspace=workspace)
            started_at = perf_counter()
            result = self._processor.process(context)
            result = enrich_processing_result(
                result,
                context=context,
                processing_time_ms=max(int((perf_counter() - started_at) * 1000), 0),
            )

            self._reporter.mark_progress(
                job,
                progress=85,
                message="Processing complete, persisting artifact.",
                metadata={"filename": result.artifact.filename},
            )
            persisted_artifact = self._persist_artifact(job=job, artifact=result.artifact)
            self._reporter.mark_completed(
                job,
                progress=100,
                message=result.completion_message,
                metadata={
                    "filename": persisted_artifact.record.filename,
                },
            )
        except PdfProcessingError as exc:
            self._logger.info(
                "worker.job_failed",
                extra={"job_id": job_id, "tool_id": tool_id, "error_code": exc.code},
            )
            if persisted_artifact is not None:
                self._storage.delete(relative_path=persisted_artifact.relative_path)
            self._session.rollback()
            self._reporter.mark_failed(
                job,
                error_code=exc.code,
                error_message=exc.user_message,
                message="PDF processing failed.",
                metadata={"tool_id": tool_id},
            )
        except Exception:
            self._logger.exception(
                "worker.job_crashed",
                extra={"job_id": job_id, "tool_id": tool_id},
            )
            if persisted_artifact is not None:
                self._storage.delete(relative_path=persisted_artifact.relative_path)
            self._session.rollback()
            self._reporter.mark_failed(
                job,
                error_code="processing_failed",
                error_message="Unable to process the PDF job.",
                message="PDF processing crashed unexpectedly.",
                metadata={"tool_id": tool_id},
            )
            raise
        finally:
            self._storage.delete_tree(target=workspace)

    def _build_context(self, *, job: Job, workspace: Path) -> ProcessorContext:
        ordered_inputs = sorted(job.inputs, key=lambda item: item.position)
        context = ProcessorContext(
            job_id=job.public_id,
            tool_id=job.tool_id,
            payload=job.request_payload,
            inputs=[self._map_job_input(job_input) for job_input in ordered_inputs],
            workspace=workspace,
        )
        policy = validate_processing_context(context, settings=self._settings)
        return replace(context, policy=policy)

    def _map_job_input(self, job_input: JobInput) -> JobInputFile:
        upload = job_input.upload
        if upload is None:
            raise PdfProcessingError(
                code="missing_job_input",
                user_message="One of the uploaded source files is no longer available.",
            )

        storage_path = self._storage.resolve_path(relative_path=upload.storage_path)
        if not storage_path.exists():
            raise PdfProcessingError(
                code="missing_source_file",
                user_message="One of the uploaded source files is no longer available.",
            )

        return JobInputFile(
            public_id=upload.public_id,
            role=job_input.role,
            original_filename=upload.original_filename,
            storage_path=storage_path,
            page_count=upload.page_count,
            is_encrypted=upload.is_encrypted,
            size_bytes=upload.size_bytes,
        )

    def _persist_artifact(self, *, job: Job, artifact: GeneratedArtifact) -> PersistedArtifact:
        created_at = datetime.now(timezone.utc)
        relative_path = self._storage.build_artifact_relative_path(
            job_public_id=job.public_id,
            filename=artifact.filename,
            created_at=created_at,
        )
        final_path = self._storage.commit_temp_file(temp_path=artifact.local_path, relative_path=relative_path)
        sha256 = self._hash_file(final_path)
        size_bytes = final_path.stat().st_size
        expires_at = created_at + timedelta(minutes=self._settings.retention_minutes)

        record = JobArtifact(
            job_id=job.id,
            kind=artifact.kind,
            filename=artifact.filename,
            storage_path=relative_path,
            content_type=artifact.content_type,
            size_bytes=size_bytes,
            sha256=sha256,
            metadata_json=artifact.metadata,
            expires_at=expires_at,
        )
        self._session.add(record)
        return PersistedArtifact(record=record, relative_path=relative_path)

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
