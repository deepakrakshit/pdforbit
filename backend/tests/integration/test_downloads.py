from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.db.repositories.job import JobRepository
from tests.support.integration import authenticate_user, create_migrated_client, run_queued_worker, upload_pdf


@pytest.fixture()
def download_client(tmp_path: Path, backend_root: Path) -> TestClient:
    client = create_migrated_client(
        tmp_path=tmp_path,
        backend_root=backend_root,
        database_name="download-phase8.sqlite3",
        storage_name="storage",
        access_secret="phase8-access-secret-with-32-plus-chars",
        refresh_secret="phase8-refresh-secret-with-32-plus-chars",
    )
    client.headers.update(authenticate_user(client, email="downloads@pdforbit.test"))
    return client


def test_polling_returns_signed_download_url_and_download_serves_artifact(
    download_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_id = upload_pdf(download_client)

    create_response = download_client.post(
        "/api/v1/optimize/compress",
        json={"file_id": file_id, "level": "high", "output_filename": "compressed.pdf"},
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["job_id"]

    run_queued_worker(download_client, monkeypatch)

    poll_response = download_client.get(f"/api/v1/jobs/{job_id}")
    assert poll_response.status_code == 200
    poll_body = poll_response.json()
    assert poll_body["status"] == "completed"
    assert poll_body["download_url"] is not None
    assert poll_body["result_url"] == poll_body["download_url"]
    assert poll_body["download_url"].startswith(f"/api/v1/download/{job_id}?")

    download_response = download_client.get(poll_body["download_url"])
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("application/pdf")
    assert b"%PDF-" in download_response.content[:20]


def test_download_rejects_invalid_signature(download_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(download_client)

    create_response = download_client.post(
        "/api/v1/optimize/compress",
        json={"file_id": file_id, "level": "high", "output_filename": "compressed.pdf"},
    )
    job_id = create_response.json()["job_id"]
    run_queued_worker(download_client, monkeypatch)

    poll_body = download_client.get(f"/api/v1/jobs/{job_id}").json()
    parsed = urlparse(poll_body["download_url"])
    params = parse_qs(parsed.query)
    invalid_url = f"{parsed.path}?exp={params['exp'][0]}&sig={'0' * 64}"

    response = download_client.get(invalid_url)
    assert response.status_code == 403
    assert response.json()["detail"] == "Download signature is invalid."


def test_download_returns_gone_for_expired_artifact(download_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(download_client)

    create_response = download_client.post(
        "/api/v1/optimize/compress",
        json={"file_id": file_id, "level": "high", "output_filename": "compressed.pdf"},
    )
    job_id = create_response.json()["job_id"]
    run_queued_worker(download_client, monkeypatch)

    poll_body = download_client.get(f"/api/v1/jobs/{job_id}").json()

    container = download_client.app.state.container
    with container.database_manager.session_scope() as session:
        job = JobRepository(session).get_by_public_id(job_id)
        assert job is not None
        artifact = next(artifact for artifact in job.artifacts if artifact.deleted_at is None)
        artifact.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.add(artifact)

    response = download_client.get(poll_body["download_url"])
    assert response.status_code == 410
    assert response.json()["detail"] == "Result is no longer available."
