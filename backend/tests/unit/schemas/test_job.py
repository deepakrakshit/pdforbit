from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.job import (
    ConvertFromPdfRouteRequest,
    ConvertToPdfJobRequest,
    CropJobRequest,
    PageNumbersJobRequest,
    ProtectJobRequest,
    RedactJobRequest,
    SignJobRequest,
    SplitJobRequest,
)


def test_split_requires_ranges_for_range_mode() -> None:
    with pytest.raises(ValidationError):
        SplitJobRequest(file_id="file_123456789", mode="by_range")


def test_split_requires_every_n_pages_for_chunk_mode() -> None:
    with pytest.raises(ValidationError):
        SplitJobRequest(file_id="file_123456789", mode="every_n_pages")


def test_split_accepts_bookmark_mode_without_ranges() -> None:
    payload = SplitJobRequest(file_id="file_123456789", mode="by_bookmark")
    assert payload.mode == "by_bookmark"


def test_redact_requires_target_terms() -> None:
    with pytest.raises(ValidationError):
        RedactJobRequest(
            file_id="file_123456789",
            keywords=[],
            patterns=[],
            fill_color="#000000",
            output_filename="redacted.pdf",
        )


def test_protect_requires_one_password() -> None:
    with pytest.raises(ValidationError):
        ProtectJobRequest(
            file_id="file_123456789",
            encryption=256,
            output_filename="protected.pdf",
        )


def test_convert_from_pdf_requires_dispatch_field() -> None:
    with pytest.raises(ValidationError):
        ConvertFromPdfRouteRequest(file_id="file_123456789")


def test_convert_to_pdf_requires_exactly_one_source_mode() -> None:
    with pytest.raises(ValidationError):
        ConvertToPdfJobRequest(
            file_id="file_123456789",
            file_ids=["file_987654321"],
            output_filename="combined.pdf",
        )


def test_crop_allows_auto_crop_without_manual_coordinates() -> None:
    payload = CropJobRequest(
        file_id="file_123456789",
        auto_crop_whitespace=True,
        output_filename="cropped.pdf",
    )
    assert payload.auto_crop_whitespace is True
    assert payload.left is None


def test_page_numbers_rejects_unknown_numbering_style() -> None:
    with pytest.raises(ValidationError):
        PageNumbersJobRequest(
            file_id="file_123456789",
            position="bottom_center",
            numbering_style="greek",
            output_filename="numbered.pdf",
        )


def test_sign_rejects_unknown_border_style() -> None:
    with pytest.raises(ValidationError):
        SignJobRequest(
            file_id="file_123456789",
            x=20,
            y=30,
            width=100,
            height=40,
            border_style="double",
            output_filename="signed.pdf",
        )
