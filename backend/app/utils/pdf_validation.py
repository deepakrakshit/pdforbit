from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pikepdf

from app.utils.files import UploadValidationError


@dataclass(frozen=True)
class PdfMetadata:
    page_count: int | None
    is_encrypted: bool


def extract_pdf_metadata(file_path: Path) -> PdfMetadata:
    try:
        with pikepdf.Pdf.open(file_path) as pdf:
            return PdfMetadata(page_count=len(pdf.pages), is_encrypted=False)
    except pikepdf.PasswordError:
        return PdfMetadata(page_count=None, is_encrypted=True)
    except (pikepdf.PdfError, OSError) as exc:
        raise UploadValidationError("Uploaded PDF is invalid or corrupted.") from exc
