from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.support.integration import create_migrated_client, run_queued_worker, upload_pdf


@pytest.fixture()
def history_client(tmp_path: Path, backend_root: Path) -> TestClient:
    return create_migrated_client(
        tmp_path=tmp_path,
        backend_root=backend_root,
        database_name="history-phase8.sqlite3",
        storage_name="storage",
        access_secret="history-phase8-access-secret-with-32-plus-chars",
        refresh_secret="history-phase8-refresh-secret-with-32-plus-chars",
    )


def test_history_endpoints_require_authentication(history_client: TestClient) -> None:
    jobs_response = history_client.get("/api/v1/history/jobs")
    uploads_response = history_client.get("/api/v1/history/uploads")

    assert jobs_response.status_code == 401
    assert uploads_response.status_code == 401


def test_history_endpoints_return_owned_jobs_and_uploads(
    history_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = register_user(history_client, email="history@pdforbit.test")
    headers = {"Authorization": f"Bearer {token}"}

    file_id = upload_pdf(history_client, pdf_bytes=None, filename="history.pdf", headers=headers)
    create_response = history_client.post(
        "/api/v1/optimize/compress",
        json={"file_id": file_id, "level": "high", "output_filename": "history-compressed.pdf"},
        headers=headers,
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["job_id"]

    run_queued_worker(history_client, monkeypatch)

    jobs_response = history_client.get("/api/v1/history/jobs?limit=10&offset=0", headers=headers)
    assert jobs_response.status_code == 200
    jobs_body = jobs_response.json()
    assert jobs_body["pagination"] == {"total": 1, "limit": 10, "offset": 0}
    assert jobs_body["items"][0]["job_id"] == job_id
    assert jobs_body["items"][0]["tool_id"] == "compress"
    assert jobs_body["items"][0]["status"] == "completed"
    assert jobs_body["items"][0]["download_url"].startswith(f"/api/v1/download/{job_id}?")

    uploads_response = history_client.get("/api/v1/history/uploads", headers=headers)
    assert uploads_response.status_code == 200
    uploads_body = uploads_response.json()
    assert uploads_body["pagination"]["total"] == 1
    assert uploads_body["items"][0]["file_id"] == file_id
    assert uploads_body["items"][0]["filename"] == "history.pdf"
    assert uploads_body["items"][0]["status"] == "in_use"


def register_user(client: TestClient, *, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPassword123"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]
