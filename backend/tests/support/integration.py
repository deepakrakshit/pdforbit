from __future__ import annotations

import io
from pathlib import Path
from typing import Sequence

import pikepdf
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.core.config import AppSettings
from app.db.repositories.job import JobRepository
from app.main import create_app
from app.models.artifact import JobArtifact
from app.models.job import Job
from app.workers.rq_app import InProcessWorker, build_worker


def create_migrated_client(
    *,
    tmp_path: Path,
    backend_root: Path,
    database_name: str,
    storage_name: str,
    access_secret: str,
    refresh_secret: str,
    settings_overrides: dict[str, object] | None = None,
) -> TestClient:
    db_path = tmp_path / database_name
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    storage_root = tmp_path / storage_name

    alembic_config = Config(str(backend_root / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location",
        str(backend_root / "app" / "db" / "migrations"),
    )
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")

    settings_kwargs: dict[str, object] = {
        "APP_ENV": "test",
        "DATABASE_URL": database_url,
        "DOCS_ENABLED": False,
        "FILES_ROOT": storage_root,
        "JWT_ACCESS_SECRET": access_secret,
        "JWT_REFRESH_SECRET": refresh_secret,
    }
    if settings_overrides:
        settings_kwargs.update(settings_overrides)

    settings = AppSettings(**settings_kwargs)
    return TestClient(create_app(settings=settings))


def build_pdf_bytes(
    *,
    page_sizes: Sequence[tuple[int, int]] | None = None,
    compress_streams: bool = True,
    repetitive_stream_blocks: int = 0,
    password: str | None = None,
) -> bytes:
    pdf = pikepdf.Pdf.new()
    sizes = list(page_sizes) if page_sizes else [(200, 200)]

    for width, height in sizes:
        page = pdf.add_blank_page(page_size=(width, height))
        if repetitive_stream_blocks > 0:
            stream = (f"0 0 {width} {height} re\nf\n" * repetitive_stream_blocks).encode("ascii")
            page.obj.Contents = pdf.make_stream(stream)

    buffer = io.BytesIO()
    save_options: dict[str, object] = {"compress_streams": compress_streams}
    if password:
        save_options["encryption"] = pikepdf.Encryption(owner=password, user=password, R=6)
    pdf.save(buffer, **save_options)
    return buffer.getvalue()


def upload_pdf(
    client: TestClient,
    *,
    filename: str = "document.pdf",
    pdf_bytes: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> str:
    response = client.post(
        "/api/v1/upload",
        files={"file": (filename, pdf_bytes or build_pdf_bytes(), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["file_id"]


def authenticate_user(
    client: TestClient,
    *,
    email: str = "owner@pdforbit.test",
    password: str = "StrongPassword123",
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def run_queued_worker(client: TestClient, monkeypatch: MonkeyPatch) -> None:
    container = client.app.state.container
    settings = container.settings
    queue_service = container.queue_service

    monkeypatch.setenv("APP_ENV", settings.app_env)
    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    monkeypatch.setenv("FILES_ROOT", str(settings.files_root))
    monkeypatch.setenv("JWT_ACCESS_SECRET", settings.jwt_access_secret)
    monkeypatch.setenv("JWT_REFRESH_SECRET", settings.jwt_refresh_secret)
    monkeypatch.setenv("TESSERACT_BIN", settings.tesseract_bin)
    monkeypatch.setenv("OCR_TIMEOUT_SECONDS", str(settings.ocr_timeout_seconds))
    monkeypatch.setenv("PDF_RENDER_DPI", str(settings.pdf_render_dpi))
    monkeypatch.setenv("TRANSLATION_PROVIDER", settings.translation_provider)
    monkeypatch.setenv("TRANSLATION_API_KEY", settings.translation_api_key or "")
    monkeypatch.setenv("GROQ_API_KEY", settings.groq_api_key or "")
    monkeypatch.setenv("GROQ_API_BASE", settings.groq_api_base)
    monkeypatch.setenv("GROQ_TRANSLATE_MODEL", settings.groq_translate_model)
    monkeypatch.setenv("GROQ_SUMMARY_MODEL", settings.groq_summary_model)
    monkeypatch.setenv("GROQ_TIMEOUT_SECONDS", str(settings.groq_timeout_seconds))
    monkeypatch.setenv("INTELLIGENCE_CHUNK_CHARS", str(settings.intelligence_chunk_chars))
    monkeypatch.setenv("INTELLIGENCE_SUMMARY_CHUNK_CHARS", str(settings.intelligence_summary_chunk_chars))
    monkeypatch.setenv("INTELLIGENCE_OCR_DPI", str(settings.intelligence_ocr_dpi))

    worker = build_worker(settings=settings, connection=queue_service.connection)
    assert isinstance(worker, InProcessWorker)
    worker.work(burst=True)


def get_job_record(client: TestClient, *, job_id: str) -> Job:
    container = client.app.state.container
    with container.database_manager.session_scope() as session:
        job = JobRepository(session).get_by_public_id(job_id)
        assert job is not None
        return job


def get_primary_artifact(client: TestClient, *, job_id: str) -> tuple[JobArtifact, Path]:
    container = client.app.state.container
    with container.database_manager.session_scope() as session:
        job = JobRepository(session).get_by_public_id(job_id)
        assert job is not None
        artifact = next(artifact for artifact in job.artifacts if artifact.deleted_at is None)
        path = container.storage_service.resolve_path(relative_path=artifact.storage_path)
        return artifact, path
