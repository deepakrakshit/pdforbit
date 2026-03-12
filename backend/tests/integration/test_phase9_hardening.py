from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.repositories.job import JobRepository
from app.models.enums import JobStatus, UploadStatus
from app.models.upload import Upload
from app.services.cleanup_service import CleanupService
from tests.support.integration import authenticate_user, build_pdf_bytes, create_migrated_client, run_queued_worker, upload_pdf


@pytest.fixture()
def hardening_client(tmp_path: Path, backend_root: Path) -> TestClient:
    return create_migrated_client(
        tmp_path=tmp_path,
        backend_root=backend_root,
        database_name="phase9-hardening.sqlite3",
        storage_name="storage",
        access_secret="phase9-access-secret-with-32-plus-chars",
        refresh_secret="phase9-refresh-secret-with-32-plus-chars",
    )


def test_upload_rate_limit_rejects_second_guest_upload(tmp_path: Path, backend_root: Path) -> None:
    client = create_migrated_client(
        tmp_path=tmp_path,
        backend_root=backend_root,
        database_name="phase9-upload-rate-limit.sqlite3",
        storage_name="storage",
        access_secret="phase9-rate-limit-access-secret-with-32-plus-chars",
        refresh_secret="phase9-rate-limit-refresh-secret-with-32-plus-chars",
        settings_overrides={"RATE_LIMIT_UPLOADS_PER_HOUR": 1},
    )

    first = client.post(
        "/api/v1/upload",
        files={"file": ("first.pdf", build_pdf_bytes(), "application/pdf")},
    )
    second = client.post(
        "/api/v1/upload",
        files={"file": ("second.pdf", build_pdf_bytes(), "application/pdf")},
    )

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.json()["detail"] == "Rate limit exceeded for uploads. Try again later."
    assert second.headers["Retry-After"]


def test_job_rate_limit_rejects_second_authenticated_job(tmp_path: Path, backend_root: Path) -> None:
    client = create_migrated_client(
        tmp_path=tmp_path,
        backend_root=backend_root,
        database_name="phase9-job-rate-limit.sqlite3",
        storage_name="storage",
        access_secret="phase9-job-limit-access-secret-with-32-plus-chars",
        refresh_secret="phase9-job-limit-refresh-secret-with-32-plus-chars",
        settings_overrides={"RATE_LIMIT_JOBS_PER_HOUR": 1, "RATE_LIMIT_AUTHENTICATED_MULTIPLIER": 1},
    )

    headers = authenticate_user(client, email="limits@pdforbit.test")
    file_id = upload_pdf(client, headers=headers)

    first = client.post(
        "/api/v1/optimize/compress",
        json={"file_id": file_id, "level": "medium", "output_filename": "compressed.pdf"},
        headers=headers,
    )
    second = client.post(
        "/api/v1/optimize/compress",
        json={"file_id": file_id, "level": "high", "output_filename": "compressed-again.pdf"},
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.json()["detail"] == "Rate limit exceeded for jobs. Try again later."


def test_cleanup_expires_uploads_and_artifacts(hardening_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = authenticate_user(hardening_client, email="cleanup1@pdforbit.test")
    file_id = upload_pdf(hardening_client, headers=headers)
    create_response = hardening_client.post(
        "/api/v1/optimize/compress",
        json={"file_id": file_id, "level": "high", "output_filename": "compressed.pdf"},
        headers=headers,
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["job_id"]

    run_queued_worker(hardening_client, monkeypatch)

    container = hardening_client.app.state.container
    with container.database_manager.session_scope() as session:
        upload = session.scalars(select(Upload)).first()
        job = JobRepository(session).get_by_public_id(job_id)
        assert job is not None
        assert upload is not None
        artifact = next(artifact for artifact in job.artifacts if artifact.deleted_at is None)
        expired_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        upload.expires_at = expired_at
        artifact.expires_at = expired_at
        session.add(upload)
        session.add(artifact)
        artifact_path = container.storage_service.resolve_path(relative_path=artifact.storage_path)
        upload_path = container.storage_service.resolve_path(relative_path=upload.storage_path)

    cleanup = CleanupService(
        settings=container.settings,
        database_manager=container.database_manager,
        queue_service=container.queue_service,
        storage_service=container.storage_service,
    )
    summary = cleanup.run_cycle()

    assert summary.expired_uploads == 1
    assert summary.expired_artifacts == 1
    assert summary.expired_jobs == 1
    assert not artifact_path.exists()
    assert not upload_path.exists()

    with container.database_manager.session_scope() as session:
        upload = session.scalars(select(Upload)).first()
        job = JobRepository(session).get_by_public_id(job_id)
        assert job is not None
        assert upload is not None
        artifact = next(iter(job.artifacts))
        assert upload.status == UploadStatus.EXPIRED
        assert upload.deleted_at is not None
        assert artifact.deleted_at is not None
        assert job.status == JobStatus.EXPIRED
        assert job.error_code == "result_expired"


def test_cleanup_requeues_pending_jobs_and_fails_stale_processing(hardening_client: TestClient) -> None:
    headers = authenticate_user(hardening_client, email="cleanup2@pdforbit.test")
    file_id = upload_pdf(hardening_client, headers=headers)

    pending_response = hardening_client.post(
        "/api/v1/optimize/compress",
        json={"file_id": file_id, "level": "medium", "output_filename": "pending.pdf"},
        headers=headers,
    )
    processing_response = hardening_client.post(
        "/api/v1/optimize/repair",
        json={"file_id": file_id, "output_filename": "repair.pdf"},
        headers=headers,
    )
    pending_job_id = pending_response.json()["job_id"]
    processing_job_id = processing_response.json()["job_id"]

    container = hardening_client.app.state.container
    container.queue_service.delete_job(pending_job_id)
    container.queue_service.delete_job(processing_job_id)

    with container.database_manager.session_scope() as session:
        jobs = JobRepository(session)
        pending_job = jobs.get_by_public_id(pending_job_id)
        processing_job = jobs.get_by_public_id(processing_job_id)
        assert pending_job is not None
        assert processing_job is not None
        stale_at = datetime.now(timezone.utc) - timedelta(seconds=container.settings.stale_job_threshold_seconds + 60)
        pending_job.created_at = stale_at
        processing_job.status = JobStatus.PROCESSING
        processing_job.started_at = stale_at
        processing_job.progress = 55
        session.add(pending_job)
        session.add(processing_job)

    cleanup = CleanupService(
        settings=container.settings,
        database_manager=container.database_manager,
        queue_service=container.queue_service,
        storage_service=container.storage_service,
    )
    summary = cleanup.run_cycle()

    assert summary.requeued_jobs == 1
    assert summary.failed_jobs == 1
    assert container.queue_service.get_job(pending_job_id) is not None

    with container.database_manager.session_scope() as session:
        jobs = JobRepository(session)
        processing_job = jobs.get_by_public_id(processing_job_id)
        assert processing_job is not None
        assert processing_job.status == JobStatus.FAILED
        assert processing_job.error_code == "stale_job_recovered"