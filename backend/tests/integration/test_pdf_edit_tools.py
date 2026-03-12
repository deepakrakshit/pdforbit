from __future__ import annotations

from pathlib import Path
import io

import fitz
import pikepdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from tests.support.integration import (
    authenticate_user,
    create_migrated_client,
    get_primary_artifact,
    run_queued_worker,
    upload_pdf,
)


@pytest.fixture()
def pdf_edit_tools_client(tmp_path: Path, backend_root: Path) -> TestClient:
    client = create_migrated_client(
        tmp_path=tmp_path,
        backend_root=backend_root,
        database_name="pdf-edit-tools.sqlite3",
        storage_name="storage",
        access_secret="pdf-edit-tools-access-secret-with-32-plus-chars",
        refresh_secret="pdf-edit-tools-refresh-secret-with-32-plus-chars",
        settings_overrides={"TRANSLATION_PROVIDER": "mock"},
    )
    client.headers.update(authenticate_user(client, email="pdf-edit-tools@pdforbit.test"))
    return client


def test_watermark_job_generates_pdf_artifact(pdf_edit_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(pdf_edit_tools_client, pdf_bytes=build_text_pdf_bytes(["Watermark me"]))

    job_id, _ = submit_and_run_job(
        pdf_edit_tools_client,
        monkeypatch,
        endpoint="/api/v1/edit/watermark",
        payload={
            "file_id": file_id,
            "text": "CONFIDENTIAL",
            "position": "diagonal",
            "opacity": 0.3,
            "font_size": 48,
            "rotation": 45,
            "output_filename": "watermarked.pdf",
        },
    )

    _, artifact_path = get_primary_artifact(pdf_edit_tools_client, job_id=job_id)
    assert artifact_path.exists()
    with fitz.open(artifact_path) as output_pdf:
        assert output_pdf.page_count == 1


def test_watermark_job_respects_skip_pages(pdf_edit_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(pdf_edit_tools_client, pdf_bytes=build_text_pdf_bytes(["First page", "Second page"]))

    job_id, _ = submit_and_run_job(
        pdf_edit_tools_client,
        monkeypatch,
        endpoint="/api/v1/edit/watermark",
        payload={
            "file_id": file_id,
            "text": "TOP SECRET",
            "position": "center",
            "opacity": 0.3,
            "font_size": 36,
            "rotation": 0,
            "skip_pages": [1],
            "output_filename": "watermark-skip.pdf",
        },
    )

    _, artifact_path = get_primary_artifact(pdf_edit_tools_client, job_id=job_id)
    with fitz.open(artifact_path) as output_pdf:
        first_text = output_pdf[0].get_text("text")
        second_text = output_pdf[1].get_text("text")
        assert "TOP SECRET" not in first_text
        assert "TOP SECRET" in second_text


def test_page_numbers_job_generates_numbered_pdf(pdf_edit_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(pdf_edit_tools_client, pdf_bytes=build_text_pdf_bytes(["Page one", "Page two"]))

    job_id, _ = submit_and_run_job(
        pdf_edit_tools_client,
        monkeypatch,
        endpoint="/api/v1/edit/page-numbers",
        payload={
            "file_id": file_id,
            "position": "bottom_center",
            "start_number": 1,
            "font_size": 12,
            "color": "#000000",
            "prefix": "Page ",
            "suffix": "",
            "output_filename": "numbered.pdf",
        },
    )

    _, artifact_path = get_primary_artifact(pdf_edit_tools_client, job_id=job_id)
    with fitz.open(artifact_path) as output_pdf:
        text = "\n".join(page.get_text("text") for page in output_pdf)
        assert output_pdf.page_count == 2
        assert "Page1" in text
        assert "Page2" in text


def test_page_numbers_job_supports_roman_style_and_skips(pdf_edit_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(pdf_edit_tools_client, pdf_bytes=build_text_pdf_bytes(["One", "Two", "Three"]))

    job_id, _ = submit_and_run_job(
        pdf_edit_tools_client,
        monkeypatch,
        endpoint="/api/v1/edit/page-numbers",
        payload={
            "file_id": file_id,
            "position": "bottom_center",
            "start_number": 1,
            "font_size": 12,
            "color": "#000000",
            "numbering_style": "roman_upper",
            "skip_first_n_pages": 1,
            "prefix": "",
            "suffix": "",
            "background_box": True,
            "output_filename": "roman-numbered.pdf",
        },
    )

    _, artifact_path = get_primary_artifact(pdf_edit_tools_client, job_id=job_id)
    with fitz.open(artifact_path) as output_pdf:
        page_texts = [page.get_text("text") for page in output_pdf]
        assert "I" not in page_texts[0]
        assert "II" in page_texts[1]
        assert "III" in page_texts[2]


def test_crop_job_updates_crop_box(pdf_edit_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(pdf_edit_tools_client, pdf_bytes=build_text_pdf_bytes(["Crop me"], page_size=(200, 200)))

    job_id, _ = submit_and_run_job(
        pdf_edit_tools_client,
        monkeypatch,
        endpoint="/api/v1/edit/crop",
        payload={
            "file_id": file_id,
            "left": 20,
            "bottom": 30,
            "right": 180,
            "top": 170,
            "pages": [1],
            "output_filename": "cropped.pdf",
        },
    )

    _, artifact_path = get_primary_artifact(pdf_edit_tools_client, job_id=job_id)
    with pikepdf.Pdf.open(artifact_path) as output_pdf:
        assert list(output_pdf.pages[0].cropbox) == [20, 30, 180, 170]


def test_crop_job_supports_auto_crop_whitespace(pdf_edit_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(pdf_edit_tools_client, pdf_bytes=build_sparse_text_pdf_bytes())

    job_id, _ = submit_and_run_job(
        pdf_edit_tools_client,
        monkeypatch,
        endpoint="/api/v1/edit/crop",
        payload={
            "file_id": file_id,
            "auto_crop_whitespace": True,
            "output_filename": "auto-cropped.pdf",
        },
    )

    artifact, artifact_path = get_primary_artifact(pdf_edit_tools_client, job_id=job_id)
    assert artifact.metadata_json["auto_crop_whitespace"] is True
    with pikepdf.Pdf.open(artifact_path) as output_pdf:
        cropbox = list(output_pdf.pages[0].cropbox)
        assert cropbox[0] > 0
        assert cropbox[2] < 595


def test_sign_job_adds_visible_signature_text(pdf_edit_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(pdf_edit_tools_client, pdf_bytes=build_text_pdf_bytes(["Please sign"]))

    job_id, _ = submit_and_run_job(
        pdf_edit_tools_client,
        monkeypatch,
        endpoint="/api/v1/security/sign",
        payload={
            "file_id": file_id,
            "signature_text": "Jane Doe",
            "page": 1,
            "x": 60,
            "y": 700,
            "width": 200,
            "height": 80,
            "output_filename": "signed.pdf",
        },
    )

    _, artifact_path = get_primary_artifact(pdf_edit_tools_client, job_id=job_id)
    with fitz.open(artifact_path) as output_pdf:
        assert "Jane Doe" in output_pdf[0].get_text("text")


def test_sign_job_supports_signature_image_attachment(pdf_edit_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(pdf_edit_tools_client, pdf_bytes=build_text_pdf_bytes(["Sign with image"]))
    image_file_id = upload_file(
        pdf_edit_tools_client,
        filename="signature.png",
        content=signature_png_bytes(),
        content_type="image/png",
    )

    job_id, _ = submit_and_run_job(
        pdf_edit_tools_client,
        monkeypatch,
        endpoint="/api/v1/security/sign",
        payload={
            "file_id": file_id,
            "signature_text": "Jane Doe",
            "page": 1,
            "x": 60,
            "y": 700,
            "width": 200,
            "height": 80,
            "signature_image_upload_id": image_file_id,
            "border_style": "underline",
            "include_timestamp": False,
            "output_filename": "signed-image.pdf",
        },
    )

    artifact, artifact_path = get_primary_artifact(pdf_edit_tools_client, job_id=job_id)
    assert artifact.metadata_json["has_image"] is True
    with fitz.open(artifact_path) as output_pdf:
        assert output_pdf.page_count == 1


def test_redact_job_removes_sensitive_text(pdf_edit_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(pdf_edit_tools_client, pdf_bytes=build_text_pdf_bytes(["SECRET 123-45-6789"]))

    job_id, poll_body = submit_and_run_job(
        pdf_edit_tools_client,
        monkeypatch,
        endpoint="/api/v1/security/redact",
        payload={
            "file_id": file_id,
            "keywords": ["SECRET"],
            "patterns": [r"\d{3}-\d{2}-\d{4}"],
            "fill_color": "#000000",
            "output_filename": "redacted.pdf",
        },
    )

    assert poll_body["redactions_applied"] >= 1
    _, artifact_path = get_primary_artifact(pdf_edit_tools_client, job_id=job_id)
    with fitz.open(artifact_path) as output_pdf:
        text = output_pdf[0].get_text("text")
        assert "SECRET" not in text
        assert "123-45-6789" not in text


def test_redact_job_supports_preview_mode(pdf_edit_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(pdf_edit_tools_client, pdf_bytes=build_text_pdf_bytes(["SECRET SECRETLY"] ))

    job_id, _ = submit_and_run_job(
        pdf_edit_tools_client,
        monkeypatch,
        endpoint="/api/v1/security/redact",
        payload={
            "file_id": file_id,
            "keywords": ["SECRET"],
            "fill_color": "#000000",
            "preview_mode": True,
            "whole_word": True,
            "output_filename": "redaction-preview.pdf",
        },
    )

    artifact, artifact_path = get_primary_artifact(pdf_edit_tools_client, job_id=job_id)
    assert artifact.metadata_json["preview_mode"] is True
    with fitz.open(artifact_path) as output_pdf:
        assert "SECRET SECRETLY" in output_pdf[0].get_text("text")
        assert output_pdf[0].first_annot is not None


def submit_and_run_job(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    endpoint: str,
    payload: dict[str, object],
) -> tuple[str, dict[str, object]]:
    response = client.post(endpoint, json=payload)
    assert response.status_code == 201
    job_id = response.json()["job_id"]
    run_queued_worker(client, monkeypatch)

    poll_response = client.get(f"/api/v1/jobs/{job_id}")
    assert poll_response.status_code == 200
    poll_body = poll_response.json()
    assert poll_body["status"] == "completed"
    assert poll_body["progress"] == 100
    assert poll_body["error"] is None
    return job_id, poll_body


def build_text_pdf_bytes(texts: list[str], *, page_size: tuple[int, int] = (595, 842)) -> bytes:
    document = fitz.open()
    for text in texts:
        page = document.new_page(width=page_size[0], height=page_size[1])
        page.insert_text((72, 120), text, fontsize=24)
    return document.tobytes()


def build_sparse_text_pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((180, 420), "Centered content", fontsize=24)
    return document.tobytes()


def upload_file(client: TestClient, *, filename: str, content: bytes, content_type: str) -> str:
    response = client.post("/api/v1/upload", files={"file": (filename, content, content_type)})
    assert response.status_code == 201
    return response.json()["file_id"]


def signature_png_bytes() -> bytes:
    image = Image.new("RGBA", (320, 120), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.line((20, 80, 120, 30, 220, 85, 300, 40), fill=(20, 50, 140, 255), width=6)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()