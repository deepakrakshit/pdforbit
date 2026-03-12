from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from tests.support.integration import (
    authenticate_user,
    build_pdf_bytes,
    create_migrated_client,
    get_primary_artifact,
    run_queued_worker,
    upload_pdf,
)


@pytest.fixture()
def editor_jobs_client(tmp_path: Path, backend_root: Path) -> TestClient:
    client = create_migrated_client(
        tmp_path=tmp_path,
        backend_root=backend_root,
        database_name="editor-jobs.sqlite3",
        storage_name="storage",
        access_secret="editor-jobs-access-secret-with-32-plus-chars",
        refresh_secret="editor-jobs-refresh-secret-with-32-plus-chars",
    )
    client.headers.update(authenticate_user(client, email="editor-jobs@pdforbit.test"))
    return client


def test_editor_apply_job_runs_end_to_end(editor_jobs_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(
        editor_jobs_client,
        filename="editor-source.pdf",
        pdf_bytes=build_pdf_bytes(page_sizes=[(595, 842), (595, 842)]),
    )

    response = editor_jobs_client.post(
        "/api/v1/jobs",
        json={
            "tool_id": "editor_apply",
            "payload": {
                "file_id": file_id,
                "output_filename": "editor-output.pdf",
                "canvas_width": 800,
                "operations": [
                    {
                        "type": "text_insert",
                        "page": 1,
                        "x": 72,
                        "y": 96,
                        "width": 260,
                        "height": 48,
                        "text": "Editor integration check",
                        "font_size": 18,
                        "font_name": "helv",
                        "color": "#111111",
                        "opacity": 1,
                        "align": "left",
                        "rotation": 0,
                        "line_height": 1.2,
                    },
                    {
                        "type": "page_rotate",
                        "page": 2,
                        "angle": 90,
                    },
                ],
            },
        },
    )
    assert response.status_code == 201
    job_id = response.json()["job_id"]

    run_queued_worker(editor_jobs_client, monkeypatch)

    poll_response = editor_jobs_client.get(f"/api/v1/jobs/{job_id}")
    assert poll_response.status_code == 200
    poll_body = poll_response.json()
    assert poll_body["status"] == "completed"
    assert poll_body["progress"] == 100
    assert poll_body["download_url"]

    download_response = editor_jobs_client.get(poll_body["download_url"])
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"

    artifact, artifact_path = get_primary_artifact(editor_jobs_client, job_id=job_id)
    assert artifact.filename == "editor-output.pdf"
    assert artifact.metadata_json["operations_applied"] == 2
    assert artifact_path.exists()

    with fitz.open(artifact_path) as output_pdf:
        assert output_pdf.page_count == 2
        assert "Editor integration check" in output_pdf[0].get_text("text")
        assert output_pdf[1].rotation == 90
