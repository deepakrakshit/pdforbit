from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from app.utils.files import (
    UploadValidationError,
    detect_upload_file,
    sanitize_filename,
)


def test_sanitize_filename_strips_path_segments() -> None:
    assert sanitize_filename(r"C:\temp\..\report.pdf") == "report.pdf"


def test_sanitize_filename_rejects_missing_value() -> None:
    with pytest.raises(UploadValidationError):
        sanitize_filename(None)


def test_detect_upload_file_accepts_docx_package(tmp_path: Path) -> None:
    file_path = tmp_path / "document.docx"
    with zipfile.ZipFile(file_path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<w:document />")

    detected = detect_upload_file(
        file_path=file_path,
        original_filename="document.docx",
        declared_content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )

    assert detected.extension == ".docx"
    assert detected.kind == "office"


def test_detect_upload_file_rejects_declared_content_type_mismatch(tmp_path: Path) -> None:
    file_path = tmp_path / "report.pdf"
    file_path.write_bytes(b"%PDF-1.7\n")

    with pytest.raises(UploadValidationError):
        detect_upload_file(
            file_path=file_path,
            original_filename="report.pdf",
            declared_content_type="image/png",
        )
