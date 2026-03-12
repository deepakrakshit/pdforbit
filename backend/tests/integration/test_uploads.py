from __future__ import annotations

import io
from pathlib import Path

import pikepdf
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.config import AppSettings
from app.main import create_app


@pytest.fixture()
def migrated_upload_client(tmp_path: Path, backend_root: Path) -> TestClient:
    db_path = tmp_path / "upload-phase4.sqlite3"
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
        JWT_ACCESS_SECRET="phase4-access-secret-with-32-plus-chars",
        JWT_REFRESH_SECRET="phase4-refresh-secret-with-32-plus-chars",
    )
    return TestClient(create_app(settings=settings))


def test_upload_pdf_returns_frontend_contract(
    migrated_upload_client: TestClient,
    tmp_path: Path,
) -> None:
    response = migrated_upload_client.post(
        "/api/v1/upload",
        files={
            "file": (
                "report.pdf",
                build_pdf_bytes(),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["file_id"].startswith("file_")
    assert body["filename"] == "report.pdf"
    assert body["size_bytes"] > 0
    assert body["page_count"] == 1
    assert body["is_encrypted"] is False
    assert body["expires_at"]


def test_upload_rejects_unsupported_file_type(migrated_upload_client: TestClient) -> None:
    response = migrated_upload_client.post(
        "/api/v1/upload",
        files={"file": ("payload.exe", b"MZ", "application/octet-stream")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "Unsupported file type."


def test_upload_rejects_mime_mismatch(migrated_upload_client: TestClient) -> None:
    response = migrated_upload_client.post(
        "/api/v1/upload",
        files={
            "file": (
                "report.pdf",
                build_pdf_bytes(),
                "image/png",
            )
        },
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "Uploaded file content does not match the provided MIME type for .pdf."


def test_upload_persists_file_to_storage(migrated_upload_client: TestClient, tmp_path: Path) -> None:
    migrated_upload_client.post(
        "/api/v1/upload",
        files={
            "file": (
                "report.pdf",
                build_pdf_bytes(),
                "application/pdf",
            )
        },
    )

    stored_files = list((tmp_path / "storage" / "uploads").rglob("*.pdf"))
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes().startswith(b"%PDF-")


def build_pdf_bytes() -> bytes:
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    buffer = io.BytesIO()
    pdf.save(buffer)
    return buffer.getvalue()
