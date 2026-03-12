from __future__ import annotations

import io
import zipfile
from pathlib import Path

import fitz
import pikepdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.services.pdf.compress import CompressPdfProcessor
from tests.support.integration import (
    authenticate_user,
    build_pdf_bytes,
    create_migrated_client,
    get_primary_artifact,
    run_queued_worker,
    upload_pdf,
)


@pytest.fixture()
def pdf_core_tools_client(tmp_path: Path, backend_root: Path) -> TestClient:
    client = create_migrated_client(
        tmp_path=tmp_path,
        backend_root=backend_root,
        database_name="pdf-core-tools.sqlite3",
        storage_name="storage",
        access_secret="pdf-core-tools-access-secret-with-32-plus-chars",
        refresh_secret="pdf-core-tools-refresh-secret-with-32-plus-chars",
    )
    client.headers.update(authenticate_user(client, email="pdf-core-tools@pdforbit.test"))
    return client


def test_merge_job_creates_merged_pdf(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    first_file_id = upload_pdf(pdf_core_tools_client, pdf_bytes=build_pdf_bytes(page_sizes=[(200, 200)]))
    second_file_id = upload_pdf(pdf_core_tools_client, pdf_bytes=build_pdf_bytes(page_sizes=[(300, 300), (400, 400)]))

    job_id, poll_body = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/organize/merge",
        payload={"file_ids": [first_file_id, second_file_id], "output_filename": "merged.pdf"},
    )

    assert poll_body["pages_processed"] == 3
    assert isinstance(poll_body["processing_time_ms"], int)
    artifact, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    assert artifact.content_type == "application/pdf"

    with pikepdf.Pdf.open(artifact_path) as output_pdf:
        assert len(output_pdf.pages) == 3
        assert page_sizes(output_pdf) == [(200, 200), (300, 300), (400, 400)]


def test_merge_job_preserves_source_bookmarks(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    first_file_id = upload_pdf(
        pdf_core_tools_client,
        filename="alpha.pdf",
        pdf_bytes=build_bookmarked_pdf_bytes(["Alpha cover", "Alpha body"], [(1, "Alpha Section", 1)]),
    )
    second_file_id = upload_pdf(
        pdf_core_tools_client,
        filename="beta.pdf",
        pdf_bytes=build_bookmarked_pdf_bytes(["Beta cover", "Beta appendix"], [(1, "Beta Section", 2)]),
    )

    job_id, _ = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/organize/merge",
        payload={"file_ids": [first_file_id, second_file_id], "output_filename": "merged-bookmarks.pdf"},
    )

    _, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    with fitz.open(artifact_path) as merged_pdf:
        toc_titles = [entry[1] for entry in merged_pdf.get_toc(simple=True)]
        assert "alpha" in toc_titles
        assert "beta" in toc_titles
        assert "Alpha Section" in toc_titles
        assert "Beta Section" in toc_titles


def test_split_job_creates_zip_archive(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        pdf_bytes=build_pdf_bytes(page_sizes=[(200, 200), (300, 300), (400, 400), (500, 500)]),
    )

    job_id, poll_body = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/organize/split",
        payload={
            "file_id": file_id,
            "mode": "by_range",
            "ranges": "1-2,4",
            "output_prefix": "segments",
        },
    )

    assert poll_body["parts_count"] == 2
    artifact, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    assert artifact.content_type == "application/zip"

    with zipfile.ZipFile(artifact_path) as archive:
        names = sorted(archive.namelist())
        assert names == ["segments-part-01.pdf", "segments-part-02.pdf"]
        first_pdf = pikepdf.Pdf.open(io.BytesIO(archive.read(names[0])))
        second_pdf = pikepdf.Pdf.open(io.BytesIO(archive.read(names[1])))
        with first_pdf, second_pdf:
            assert len(first_pdf.pages) == 2
            assert len(second_pdf.pages) == 1
            assert page_sizes(first_pdf) == [(200, 200), (300, 300)]
            assert page_sizes(second_pdf) == [(500, 500)]


def test_split_job_supports_bookmark_mode_with_stored_zip(
    pdf_core_tools_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        filename="chaptered.pdf",
        pdf_bytes=build_bookmarked_pdf_bytes(
            ["Intro page", "Intro continuation", "Appendix page"],
            [(1, "Intro", 1), (1, "Appendix", 3)],
        ),
    )

    job_id, poll_body = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/organize/split",
        payload={"file_id": file_id, "mode": "by_bookmark", "output_prefix": "section"},
    )

    assert poll_body["parts_count"] == 2
    artifact, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    assert artifact.content_type == "application/zip"
    with zipfile.ZipFile(artifact_path) as archive:
        names = sorted(archive.namelist())
        assert names == ["Appendix.pdf", "Intro.pdf"]
        for info in archive.infolist():
            assert info.compress_type == zipfile.ZIP_STORED


def test_split_job_returns_direct_pdf_for_single_output(
    pdf_core_tools_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        pdf_bytes=build_pdf_bytes(page_sizes=[(200, 200), (240, 240)]),
    )

    job_id, poll_body = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/organize/split",
        payload={"file_id": file_id, "mode": "by_range", "ranges": "1-2", "output_prefix": "solo"},
    )

    assert poll_body["parts_count"] == 1
    artifact, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    assert artifact.content_type == "application/pdf"
    with pikepdf.Pdf.open(artifact_path) as output_pdf:
        assert len(output_pdf.pages) == 2


def test_extract_job_creates_selected_pages_pdf(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        pdf_bytes=build_pdf_bytes(page_sizes=[(200, 200), (300, 300), (400, 400)]),
    )

    job_id, _ = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/organize/extract",
        payload={
            "file_id": file_id,
            "pages": [3, 1],
            "output_filename": "extracted.pdf",
        },
    )

    _, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    with pikepdf.Pdf.open(artifact_path) as output_pdf:
        assert len(output_pdf.pages) == 2
        assert page_sizes(output_pdf) == [(400, 400), (200, 200)]


def test_extract_job_preserves_relevant_bookmarks(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        filename="outlined.pdf",
        pdf_bytes=build_bookmarked_pdf_bytes(
            ["Page one", "Page two", "Page three"],
            [(1, "Middle", 2), (1, "End", 3)],
        ),
    )

    job_id, _ = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/organize/extract",
        payload={"file_id": file_id, "pages": [2, 3], "output_filename": "outlined-extract.pdf"},
    )

    _, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    with fitz.open(artifact_path) as output_pdf:
        toc = output_pdf.get_toc(simple=True)
        titles = [entry[1] for entry in toc]
        assert "Middle" in titles
        assert "End" in titles


def test_remove_pages_job_creates_filtered_pdf(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        pdf_bytes=build_pdf_bytes(page_sizes=[(200, 200), (300, 300), (400, 400)]),
    )

    job_id, _ = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/organize/remove-pages",
        payload={
            "file_id": file_id,
            "pages_to_remove": [2],
            "output_filename": "removed.pdf",
        },
    )

    _, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    with pikepdf.Pdf.open(artifact_path) as output_pdf:
        assert len(output_pdf.pages) == 2
        assert page_sizes(output_pdf) == [(200, 200), (400, 400)]


def test_reorder_job_creates_pdf_in_requested_order(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        pdf_bytes=build_pdf_bytes(page_sizes=[(200, 200), (300, 300), (400, 400)]),
    )

    job_id, _ = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/organize/reorder",
        payload={
            "file_id": file_id,
            "page_order": [3, 1, 2],
            "output_filename": "reordered.pdf",
        },
    )

    _, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    with pikepdf.Pdf.open(artifact_path) as output_pdf:
        assert len(output_pdf.pages) == 3
        assert page_sizes(output_pdf) == [(400, 400), (200, 200), (300, 300)]


def test_reorder_job_rejects_duplicate_page_order(
    pdf_core_tools_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        pdf_bytes=build_pdf_bytes(page_sizes=[(200, 200), (300, 300), (400, 400)]),
    )

    _, poll_body = submit_and_fail_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/organize/reorder",
        payload={"file_id": file_id, "page_order": [1, 1, 2], "output_filename": "invalid.pdf"},
    )

    assert "duplicate" in poll_body["error"]


def test_compress_job_reduces_file_size_and_reports_metrics(
    pdf_core_tools_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        pdf_bytes=build_pdf_bytes(
            page_sizes=[(200, 200)],
            compress_streams=False,
            repetitive_stream_blocks=5000,
        ),
    )

    job_id, poll_body = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/optimize/compress",
        payload={
            "file_id": file_id,
            "level": "high",
            "output_filename": "compressed.pdf",
        },
    )

    _, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    assert poll_body["original_bytes"] > poll_body["compressed_bytes"]
    assert poll_body["compressed_bytes"] == artifact_path.stat().st_size
    assert poll_body["savings_pct"] > 0


def test_compress_profiles_are_ordered_for_expected_quality() -> None:
    low = CompressPdfProcessor._compression_profile("low")
    medium = CompressPdfProcessor._compression_profile("medium")
    high = CompressPdfProcessor._compression_profile("high")

    assert low.color_resolution < medium.color_resolution < high.color_resolution
    assert low.gray_resolution < medium.gray_resolution < high.gray_resolution
    assert low.jpeg_quality < medium.jpeg_quality < high.jpeg_quality


def test_compress_levels_produce_distinct_sizes(
    pdf_core_tools_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_pdf = build_raster_pdf_bytes()
    level_sizes: dict[str, int] = {}

    for level in ("low", "medium", "high"):
        file_id = upload_pdf(pdf_core_tools_client, filename=f"{level}.pdf", pdf_bytes=source_pdf)
        job_id, poll_body = submit_and_run_job(
            pdf_core_tools_client,
            monkeypatch,
            endpoint="/api/v1/optimize/compress",
            payload={
                "file_id": file_id,
                "level": level,
                "output_filename": f"{level}-compressed.pdf",
            },
        )

        _, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
        level_sizes[level] = artifact_path.stat().st_size
        assert poll_body["compressed_bytes"] == level_sizes[level]

    assert level_sizes["low"] < level_sizes["medium"]
    assert level_sizes["medium"] < level_sizes["high"]


def test_compress_job_returns_original_when_output_is_larger(
    pdf_core_tools_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_pdf = build_pdf_bytes(page_sizes=[(200, 200)], compress_streams=True)
    file_id = upload_pdf(pdf_core_tools_client, filename="small.pdf", pdf_bytes=source_pdf)

    job_id, poll_body = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/optimize/compress",
        payload={"file_id": file_id, "level": "high", "output_filename": "small-compressed.pdf"},
    )

    artifact, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    assert poll_body["compressed_bytes"] == poll_body["original_bytes"]
    assert poll_body["savings_pct"] == 0
    assert artifact.metadata_json["already_optimized"] is True
    assert artifact_path.stat().st_size == len(source_pdf)


def test_repair_job_rewrites_pdf_successfully(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        pdf_bytes=build_pdf_bytes(page_sizes=[(200, 200), (300, 300)], compress_streams=False),
    )

    job_id, poll_body = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/optimize/repair",
        payload={"file_id": file_id, "output_filename": "repaired.pdf"},
    )

    assert poll_body["pages_processed"] == 2
    _, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    with pikepdf.Pdf.open(artifact_path) as output_pdf:
        assert len(output_pdf.pages) == 2


def test_rotate_job_updates_selected_page_rotation(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        pdf_bytes=build_pdf_bytes(page_sizes=[(200, 200), (300, 300)]),
    )

    job_id, poll_body = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/edit/rotate",
        payload={
            "file_id": file_id,
            "angle": 90,
            "pages": [2],
            "output_filename": "rotated.pdf",
        },
    )

    assert poll_body["pages_processed"] == 1
    _, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    with pikepdf.Pdf.open(artifact_path) as output_pdf:
        assert output_pdf.pages[0].obj.get("/Rotate") is None
        assert int(output_pdf.pages[1].obj.get("/Rotate")) == 90


def test_rotate_job_supports_absolute_mode(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(200, 200)).obj["/Rotate"] = 180
    source_buffer = io.BytesIO()
    pdf.save(source_buffer)
    file_id = upload_pdf(pdf_core_tools_client, pdf_bytes=source_buffer.getvalue())

    job_id, poll_body = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/edit/rotate",
        payload={
            "file_id": file_id,
            "angle": 90,
            "pages": [1],
            "relative": False,
            "output_filename": "rotated-absolute.pdf",
        },
    )

    assert poll_body["pages_processed"] == 1
    artifact, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    assert artifact.metadata_json["rotation_mode"] == "absolute"
    with pikepdf.Pdf.open(artifact_path) as output_pdf:
        assert int(output_pdf.pages[0].obj.get("/Rotate")) == 90


def test_protect_job_creates_encrypted_pdf(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(pdf_core_tools_client, pdf_bytes=build_pdf_bytes())

    job_id, poll_body = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/security/protect",
        payload={
            "file_id": file_id,
            "user_password": "user-secret",
            "owner_password": "owner-secret",
            "encryption": 256,
            "output_filename": "protected.pdf",
        },
    )

    assert poll_body["pages_processed"] == 1
    _, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    with pytest.raises(pikepdf.PasswordError):
        pikepdf.Pdf.open(artifact_path)
    with pikepdf.Pdf.open(artifact_path, password="user-secret") as output_pdf:
        assert len(output_pdf.pages) == 1


def test_protect_job_records_permission_metadata(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(pdf_core_tools_client, pdf_bytes=build_pdf_bytes())

    job_id, _ = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/security/protect",
        payload={
            "file_id": file_id,
            "user_password": "user-secret",
            "encryption": 256,
            "allow_printing": False,
            "allow_copying": False,
            "allow_annotations": True,
            "allow_form_filling": False,
            "output_filename": "restricted.pdf",
        },
    )

    artifact, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    permissions = artifact.metadata_json["permissions"]
    assert permissions["allow_printing"] is False
    assert permissions["allow_copying"] is False
    assert permissions["allow_annotations"] is True
    assert permissions["allow_form_filling"] is False
    with pikepdf.Pdf.open(artifact_path, password="user-secret") as output_pdf:
        assert len(output_pdf.pages) == 1


def test_unlock_job_removes_pdf_encryption(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        pdf_bytes=build_pdf_bytes(password="open-sesame"),
    )

    job_id, poll_body = submit_and_run_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/security/unlock",
        payload={
            "file_id": file_id,
            "password": "open-sesame",
            "output_filename": "unlocked.pdf",
        },
    )

    assert poll_body["pages_processed"] == 1
    _, artifact_path = get_primary_artifact(pdf_core_tools_client, job_id=job_id)
    with pikepdf.Pdf.open(artifact_path) as output_pdf:
        assert len(output_pdf.pages) == 1


def test_sign_job_rejects_out_of_bounds_signature(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        pdf_bytes=build_pdf_bytes(page_sizes=[(200, 200)]),
    )

    job_id, poll_body = submit_and_fail_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/security/sign",
        payload={
            "file_id": file_id,
            "signature_text": "Signed",
            "page": 1,
            "x": 170,
            "y": 170,
            "width": 80,
            "height": 40,
            "output_filename": "signed.pdf",
        },
    )

    assert poll_body["job_id"] == job_id
    assert poll_body["error"] == "Signature placement must be within the page boundaries."


def test_redact_job_rejects_unsafe_regex(pdf_core_tools_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = upload_pdf(
        pdf_core_tools_client,
        pdf_bytes=build_pdf_bytes(page_sizes=[(200, 200)]),
    )

    _, poll_body = submit_and_fail_job(
        pdf_core_tools_client,
        monkeypatch,
        endpoint="/api/v1/security/redact",
        payload={
            "file_id": file_id,
            "patterns": ["(a+)+$"],
            "output_filename": "redacted.pdf",
        },
    )

    assert poll_body["error"] == "Nested quantifiers that could cause catastrophic backtracking are not supported."


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
    assert poll_body["job_id"] == job_id
    assert poll_body["status"] == "completed"
    assert poll_body["progress"] == 100
    assert poll_body["error"] is None
    return job_id, poll_body


def submit_and_fail_job(
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
    assert poll_body["job_id"] == job_id
    assert poll_body["status"] == "failed"
    assert poll_body["progress"] == 0
    assert poll_body["error"]
    return job_id, poll_body


def page_sizes(pdf: pikepdf.Pdf) -> list[tuple[int, int]]:
    return [(int(page.mediabox[2]), int(page.mediabox[3])) for page in pdf.pages]


def build_raster_pdf_bytes() -> bytes:
    image = Image.new("RGB", (1800, 1800), "white")
    draw = ImageDraw.Draw(image)
    for index in range(60):
        x = (index * 47) % 1500
        y = (index * 61) % 1500
        draw.rectangle((x, y, x + 180, y + 120), outline="black", width=3)
        draw.text((x + 16, y + 18), f"Panel {index}", fill="black")

    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")
    png_bytes = image_buffer.getvalue()

    document = fitz.open()
    for page_number in range(4):
        page = document.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Compression sample {page_number + 1}", fontsize=26)
        page.insert_text((72, 118), "Raster-heavy content for compression tier verification.", fontsize=12)
        page.insert_image(fitz.Rect(72, 180, 523, 631), stream=png_bytes)
    return document.tobytes(garbage=0, deflate=False)


def build_bookmarked_pdf_bytes(texts: list[str], toc_entries: list[tuple[int, str, int]]) -> bytes:
    document = fitz.open()
    for text in texts:
        page = document.new_page(width=595, height=842)
        page.insert_text((72, 120), text, fontsize=24)
    document.set_toc([[level, title, page] for level, title, page in toc_entries])
    return document.tobytes()