from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import build_settings
from app.services.pdf import (
    PdfProcessingError,
    chunk_page_numbers,
    ensure_pdf_output_filename,
    ensure_zip_output_filename,
    normalize_page_numbers,
    parse_split_ranges,
)
from app.services.pdf.common import JobInputFile, ProcessorContext
from app.services.pdf.policy import validate_processing_context


def test_parse_split_ranges_returns_non_overlapping_groups() -> None:
    groups = parse_split_ranges("1-2,4,6-7", page_count=7)

    assert groups == [[1, 2], [4], [6, 7]]


def test_parse_split_ranges_rejects_overlap() -> None:
    with pytest.raises(PdfProcessingError) as exc_info:
        parse_split_ranges("1-3,3-4", page_count=5)

    assert exc_info.value.code == "invalid_page_range"


def test_chunk_page_numbers_builds_even_groups() -> None:
    assert chunk_page_numbers(5, 2) == [[1, 2], [3, 4], [5]]


def test_normalize_page_numbers_rejects_duplicates() -> None:
    with pytest.raises(PdfProcessingError) as exc_info:
        normalize_page_numbers([1, 1], page_count=3)

    assert exc_info.value.code == "invalid_pages"


def test_output_filename_helpers_normalize_extensions() -> None:
    assert ensure_pdf_output_filename("report") == "report.pdf"
    assert ensure_pdf_output_filename("report.txt") == "report.pdf"
    assert ensure_zip_output_filename("split") == "split.zip"


def test_processing_policy_rejects_encrypted_inputs_for_non_unlock_tools(tmp_path: Path) -> None:
    settings = build_settings(env_file=None, app_env="test")
    context = ProcessorContext(
        job_id="job_demo12345",
        tool_id="merge",
        payload={"output_filename": "merged.pdf"},
        inputs=[
            JobInputFile(
                public_id="file_demo12345",
                original_filename="secret.pdf",
                storage_path=tmp_path / "secret.pdf",
                page_count=None,
                is_encrypted=True,
                size_bytes=1024,
            )
        ],
        workspace=tmp_path,
    )

    with pytest.raises(PdfProcessingError) as exc_info:
        validate_processing_context(context, settings=settings)

    assert exc_info.value.code == "encrypted_pdf_unsupported"


def test_processing_policy_rejects_split_jobs_with_too_many_outputs(tmp_path: Path) -> None:
    settings = build_settings(env_file=None, app_env="test")
    source_path = tmp_path / "large.pdf"
    source_path.write_bytes(b"%PDF-1.7\n")
    context = ProcessorContext(
        job_id="job_demo12345",
        tool_id="split",
        payload={
            "file_id": "file_demo12345",
            "mode": "every_n_pages",
            "every_n_pages": 1,
            "output_prefix": "part",
        },
        inputs=[
            JobInputFile(
                public_id="file_demo12345",
                original_filename="large.pdf",
                storage_path=source_path,
                page_count=600,
                is_encrypted=False,
                size_bytes=1024,
            )
        ],
        workspace=tmp_path,
    )

    with pytest.raises(PdfProcessingError) as exc_info:
        validate_processing_context(context, settings=settings)

    assert exc_info.value.code == "output_limit_exceeded"
