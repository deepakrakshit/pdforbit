from __future__ import annotations

import io
from pathlib import Path

import pikepdf
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.config import AppSettings
from app.db.repositories.job import JobRepository
from app.main import create_app
from app.models.enums import JobStatus
from app.services.queue_service import QueueService
from app.workers.rq_app import InProcessWorker, build_worker
from tests.support.integration import authenticate_user


@pytest.fixture()
def migrated_jobs_client(tmp_path: Path, backend_root: Path) -> TestClient:
    db_path = tmp_path / "jobs-phase5.sqlite3"
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    storage_root = tmp_path / "storage"

    alembic_config = Config(str(backend_root / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location",
        str(backend_root / "app" / "db" / "migrations"),
    )
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")

    settings = AppSettings(
        APP_ENV="test",
        DATABASE_URL=database_url,
        DOCS_ENABLED=False,
        FILES_ROOT=storage_root,
        JWT_ACCESS_SECRET="phase5-access-secret-with-32-plus-chars",
        JWT_REFRESH_SECRET="phase5-refresh-secret-with-32-plus-chars",
    )
    return TestClient(create_app(settings=settings))


def test_canonical_jobs_endpoint_creates_and_polls_pending_job(migrated_jobs_client: TestClient) -> None:
    headers = authenticate_user(migrated_jobs_client, email="jobs1@pdforbit.test")
    file_id = upload_pdf(migrated_jobs_client, headers=headers)

    response = migrated_jobs_client.post(
        "/api/v1/jobs",
        json={
            "tool_id": "compress",
            "payload": {
                "file_id": file_id,
                "level": "medium",
                "output_filename": "compressed.pdf",
            },
        },
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["job_id"].startswith("job_")

    poll_response = migrated_jobs_client.get(f"/api/v1/jobs/{body['job_id']}", headers=headers)
    assert poll_response.status_code == 200
    poll_body = poll_response.json()
    assert poll_body["job_id"] == body["job_id"]
    assert poll_body["status"] == "pending"
    assert poll_body["progress"] == 0
    assert poll_body["download_url"] is None

    queue_service = migrated_jobs_client.app.state.container.queue_service
    assert isinstance(queue_service, QueueService)
    queued_job = queue_service.get_job(body["job_id"])
    assert queued_job is not None
    assert queued_job.meta["tool_id"] == "compress"


def test_worker_consumes_job_and_updates_polling_status(
    migrated_jobs_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = authenticate_user(migrated_jobs_client, email="jobs2@pdforbit.test")
    file_id = upload_pdf(migrated_jobs_client, headers=headers)

    response = migrated_jobs_client.post(
        "/api/v1/jobs",
        json={
            "tool_id": "compress",
            "payload": {
                "file_id": file_id,
                "level": "medium",
                "output_filename": "compressed.pdf",
            },
        },
        headers=headers,
    )

    assert response.status_code == 201
    job_id = response.json()["job_id"]

    container = migrated_jobs_client.app.state.container
    settings = container.settings
    queue_service = container.queue_service
    queued_job = queue_service.get_job(job_id)
    assert queued_job is not None
    assert queued_job.get_status(refresh=True) == "queued"

    monkeypatch.setenv("APP_ENV", settings.app_env)
    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    monkeypatch.setenv("FILES_ROOT", str(settings.files_root))
    monkeypatch.setenv("JWT_ACCESS_SECRET", settings.jwt_access_secret)
    monkeypatch.setenv("JWT_REFRESH_SECRET", settings.jwt_refresh_secret)

    worker = build_worker(settings=settings, connection=queue_service.connection)
    assert isinstance(worker, InProcessWorker)
    worker.work(burst=True)

    queue = queue_service.get_queue("pdf-default")
    assert queue.count == 0
    assert queue_service.get_job(job_id) is None

    with container.database_manager.session_scope() as session:
        job = JobRepository(session).get_by_public_id(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.error_code is None
        assert job.error_message is None
        assert len(job.artifacts) == 1
        assert len(job.events) == 4
        assert job.events[-1].status == JobStatus.COMPLETED
        assert job.events[-1].message in {
            "Compressed PDF created successfully.",
            "File is already optimally compressed.",
        }

    poll_response = migrated_jobs_client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert poll_response.status_code == 200
    poll_body = poll_response.json()
    assert poll_body["job_id"] == job_id
    assert poll_body["status"] == "completed"
    assert poll_body["progress"] == 100
    assert poll_body["error"] is None
    assert poll_body["original_bytes"] is not None
    assert poll_body["compressed_bytes"] is not None
    assert poll_body["download_url"] is not None
    assert poll_body["download_url"].startswith(f"/api/v1/download/{job_id}?")


def test_job_polling_hides_owned_jobs_from_other_users(migrated_jobs_client: TestClient) -> None:
    owner_headers = authenticate_user(migrated_jobs_client, email="jobs-owner@pdforbit.test")
    intruder_headers = authenticate_user(migrated_jobs_client, email="jobs-intruder@pdforbit.test")
    file_id = upload_pdf(migrated_jobs_client, headers=owner_headers)

    create_response = migrated_jobs_client.post(
        "/api/v1/jobs",
        json={
            "tool_id": "compress",
            "payload": {
                "file_id": file_id,
                "level": "medium",
                "output_filename": "compressed.pdf",
            },
        },
        headers=owner_headers,
    )

    assert create_response.status_code == 201
    job_id = create_response.json()["job_id"]

    anonymous_poll = migrated_jobs_client.get(f"/api/v1/jobs/{job_id}")
    intruder_poll = migrated_jobs_client.get(f"/api/v1/jobs/{job_id}", headers=intruder_headers)
    owner_poll = migrated_jobs_client.get(f"/api/v1/jobs/{job_id}", headers=owner_headers)

    assert anonymous_poll.status_code == 404
    assert anonymous_poll.json()["detail"] == "Job not found."
    assert intruder_poll.status_code == 404
    assert intruder_poll.json()["detail"] == "Job not found."
    assert owner_poll.status_code == 200
    assert owner_poll.json()["job_id"] == job_id


def test_alias_routes_enqueue_expected_tool_jobs(migrated_jobs_client: TestClient) -> None:
    headers = authenticate_user(migrated_jobs_client, email="jobs3@pdforbit.test")
    first_pdf = upload_pdf(migrated_jobs_client, headers=headers)
    second_pdf = upload_pdf(migrated_jobs_client, headers=headers)

    merge = migrated_jobs_client.post(
        "/api/v1/organize/merge",
        json={"file_ids": [first_pdf, second_pdf], "output_filename": "merged.pdf"},
        headers=headers,
    )
    compress = migrated_jobs_client.post(
        "/api/v1/optimize/compress",
        json={"file_id": first_pdf, "level": "high", "output_filename": "compressed.pdf"},
        headers=headers,
    )
    redact = migrated_jobs_client.post(
        "/api/v1/security/redact",
        json={
            "file_id": first_pdf,
            "keywords": ["secret"],
            "patterns": [],
            "fill_color": "#000000",
            "output_filename": "redacted.pdf",
        },
        headers=headers,
    )
    translate = migrated_jobs_client.post(
        "/api/v1/intelligence/translate",
        json={
            "file_id": first_pdf,
            "target_language": "en",
            "source_language": "fr",
        },
        headers=headers,
    )
    summarize_headers = authenticate_user(migrated_jobs_client, email="jobs5@pdforbit.test")
    summarize_pdf = upload_pdf(migrated_jobs_client, headers=summarize_headers)
    summarize = migrated_jobs_client.post(
        "/api/v1/intelligence/summarize",
        json={
            "file_id": summarize_pdf,
            "output_language": "en",
            "length": "short",
        },
        headers=summarize_headers,
    )

    for response in (merge, compress, redact, translate, summarize):
        assert response.status_code == 201
        assert response.json()["job_id"].startswith("job_")

    queue_service = migrated_jobs_client.app.state.container.queue_service
    assert queue_service.get_job(merge.json()["job_id"]).meta["tool_id"] == "merge"
    assert queue_service.get_job(compress.json()["job_id"]).meta["tool_id"] == "compress"
    assert queue_service.get_job(redact.json()["job_id"]).meta["tool_id"] == "redact"
    assert queue_service.get_job(translate.json()["job_id"]).meta["tool_id"] == "translate"
    assert queue_service.get_job(summarize.json()["job_id"]).meta["tool_id"] == "summarize"


def test_convert_from_pdf_alias_dispatches_office_conversion(migrated_jobs_client: TestClient) -> None:
    headers = authenticate_user(migrated_jobs_client, email="jobs4@pdforbit.test")
    file_id = upload_pdf(migrated_jobs_client, headers=headers)

    response = migrated_jobs_client.post(
        "/api/v1/convert/from-pdf",
        json={"file_id": file_id, "format": "word"},
        headers=headers,
    )

    assert response.status_code == 201
    queued_job = migrated_jobs_client.app.state.container.queue_service.get_job(response.json()["job_id"])
    assert queued_job is not None
    assert queued_job.meta["tool_id"] == "pdf2word"


def upload_pdf(client: TestClient, headers: dict[str, str] | None = None) -> str:
    response = client.post(
        "/api/v1/upload",
        files={"file": ("document.pdf", build_pdf_bytes(), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["file_id"]


def build_pdf_bytes() -> bytes:
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    buffer = io.BytesIO()
    pdf.save(buffer)
    return buffer.getvalue()
