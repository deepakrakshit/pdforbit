from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
import zipfile
from typing import Any

import pikepdf

from app.models.enums import ArtifactKind
from app.utils.files import sanitize_filename
from app.utils.pdf_validation import extract_pdf_metadata

PDF_CONTENT_TYPE = "application/pdf"
ZIP_CONTENT_TYPE = "application/zip"


class PdfProcessingError(Exception):
    def __init__(self, *, code: str, user_message: str) -> None:
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message


@dataclass(frozen=True)
class JobInputFile:
    public_id: str
    original_filename: str
    storage_path: Path
    page_count: int | None
    is_encrypted: bool
    size_bytes: int
    role: str = "source"


@dataclass(frozen=True)
class ProcessorContext:
    job_id: str
    tool_id: str
    payload: dict[str, Any]
    inputs: list[JobInputFile]
    workspace: Path
    policy: Any | None = None

    def require_single_input(self) -> JobInputFile:
        source_inputs = [item for item in self.inputs if item.role == "source"]
        if len(source_inputs) == 1:
            return source_inputs[0]
        if len(self.inputs) != 1:
            raise PdfProcessingError(
                code="invalid_job_inputs",
                user_message="This tool requires exactly one uploaded PDF.",
            )
        return self.inputs[0]


@dataclass(frozen=True)
class GeneratedArtifact:
    local_path: Path
    filename: str
    content_type: str
    kind: ArtifactKind
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProcessingResult:
    artifact: GeneratedArtifact
    completion_message: str


class BaseToolProcessor:
    tool_id: str = ""

    def supports(self, tool_id: str) -> bool:
        return tool_id == self.tool_id


def ensure_pdf_output_filename(filename: str) -> str:
    path = Path(filename)
    stem = path.stem or path.name
    if path.suffix.lower() == ".pdf":
        return path.name
    return f"{stem}.pdf"


def ensure_zip_output_filename(filename: str) -> str:
    path = Path(filename)
    stem = path.stem or path.name
    if path.suffix.lower() == ".zip":
        return path.name
    return f"{stem}.zip"


def normalize_page_numbers(
    page_numbers: list[int],
    *,
    page_count: int,
    allow_duplicates: bool = False,
    field_name: str = "pages",
) -> list[int]:
    if not page_numbers:
        raise PdfProcessingError(code="invalid_pages", user_message=f"{field_name} must not be empty.")

    normalized: list[int] = []
    seen: set[int] = set()
    for page_number in page_numbers:
        if page_number < 1 or page_number > page_count:
            raise PdfProcessingError(
                code="invalid_pages",
                user_message=f"{field_name} must reference pages between 1 and {page_count}.",
            )
        if not allow_duplicates and page_number in seen:
            raise PdfProcessingError(
                code="invalid_pages",
                user_message=f"{field_name} must not contain duplicate page numbers.",
            )
        seen.add(page_number)
        normalized.append(page_number)
    return normalized


def parse_split_ranges(range_spec: str, *, page_count: int) -> list[list[int]]:
    groups: list[list[int]] = []
    seen: set[int] = set()

    for raw_segment in range_spec.split(","):
        segment = raw_segment.strip()
        if not segment:
            continue

        if "-" in segment:
            start_raw, end_raw = segment.split("-", 1)
            try:
                start = int(start_raw.strip())
                end = int(end_raw.strip())
            except ValueError as exc:
                raise PdfProcessingError(
                    code="invalid_page_range",
                    user_message="Split ranges must use integers like 1-3,5,7-9.",
                ) from exc
            if start > end:
                raise PdfProcessingError(
                    code="invalid_page_range",
                    user_message="Split ranges must be defined in ascending page order.",
                )
            pages = list(range(start, end + 1))
        else:
            try:
                pages = [int(segment)]
            except ValueError as exc:
                raise PdfProcessingError(
                    code="invalid_page_range",
                    user_message="Split ranges must use integers like 1-3,5,7-9.",
                ) from exc

        for page_number in pages:
            if page_number < 1 or page_number > page_count:
                raise PdfProcessingError(
                    code="invalid_page_range",
                    user_message=f"Split ranges must reference pages between 1 and {page_count}.",
                )
            if page_number in seen:
                raise PdfProcessingError(
                    code="invalid_page_range",
                    user_message="Split ranges must not overlap.",
                )
            seen.add(page_number)

        groups.append(pages)

    if not groups:
        raise PdfProcessingError(
            code="invalid_page_range",
            user_message="Split ranges must contain at least one page segment.",
        )

    return groups


def chunk_page_numbers(page_count: int, chunk_size: int) -> list[list[int]]:
    if chunk_size <= 0:
        raise PdfProcessingError(
            code="invalid_chunk_size",
            user_message="Split size must be a positive number of pages.",
        )

    return [
        list(range(start, min(start + chunk_size, page_count + 1)))
        for start in range(1, page_count + 1, chunk_size)
    ]


def open_pdf(
    file_path: Path,
    *,
    password: str = "",
    attempt_recovery: bool = False,
) -> pikepdf.Pdf:
    try:
        return pikepdf.Pdf.open(
            file_path,
            password=password,
            attempt_recovery=attempt_recovery,
            suppress_warnings=not attempt_recovery,
        )
    except pikepdf.PasswordError as exc:
        message = "The PDF password is invalid or missing."
        if not password:
            message = "This PDF is encrypted and requires a password."
        raise PdfProcessingError(code="pdf_password_required", user_message=message) from exc
    except pikepdf.PdfError as exc:
        raise PdfProcessingError(
            code="invalid_pdf",
            user_message="Unable to read the uploaded PDF.",
        ) from exc


def validate_generated_artifact(artifact: GeneratedArtifact, *, workspace: Path) -> None:
    try:
        artifact.local_path.relative_to(workspace)
    except ValueError as exc:
        raise PdfProcessingError(
            code="invalid_artifact_path",
            user_message="Processing produced an invalid output location.",
        ) from exc

    if not artifact.local_path.exists() or not artifact.local_path.is_file():
        raise PdfProcessingError(
            code="missing_artifact",
            user_message="Processing did not produce a downloadable result file.",
        )

    if artifact.local_path.stat().st_size <= 0:
        raise PdfProcessingError(
            code="empty_artifact",
            user_message="Processing produced an empty result file.",
        )

    sanitized_filename = sanitize_filename(artifact.filename)
    if sanitized_filename != artifact.filename:
        raise PdfProcessingError(
            code="invalid_output_filename",
            user_message="Processing produced an invalid output filename.",
        )

    if artifact.content_type == PDF_CONTENT_TYPE:
        extract_pdf_metadata(artifact.local_path)
    elif artifact.content_type == ZIP_CONTENT_TYPE:
        try:
            with zipfile.ZipFile(artifact.local_path) as archive:
                names = archive.namelist()
                if not names:
                    raise PdfProcessingError(
                        code="empty_archive",
                        user_message="Processing produced an empty archive.",
                    )
                corrupt_member = archive.testzip()
                if corrupt_member is not None:
                    raise PdfProcessingError(
                        code="invalid_archive",
                        user_message="Processing produced a corrupted archive.",
                    )
        except zipfile.BadZipFile as exc:
            raise PdfProcessingError(
                code="invalid_archive",
                user_message="Processing produced a corrupted archive.",
            ) from exc


def enrich_processing_result(
    result: ProcessingResult,
    *,
    context: ProcessorContext,
    processing_time_ms: int,
) -> ProcessingResult:
    validate_generated_artifact(result.artifact, workspace=context.workspace)

    source_total_bytes = sum(max(item.size_bytes, 0) for item in context.inputs)
    source_total_pages = sum(page_count or 0 for page_count in (item.page_count for item in context.inputs))
    metadata = {
        **result.artifact.metadata,
        "job_id": context.job_id,
        "tool_id": context.tool_id,
        "input_file_count": len(context.inputs),
        "input_size_bytes": source_total_bytes,
        "input_page_count": source_total_pages,
        "processing_time_ms": processing_time_ms,
        "success_message": result.completion_message,
    }
    metadata.setdefault("pages_processed", result.artifact.metadata.get("pages_processed", source_total_pages or None))

    return replace(
        result,
        artifact=replace(result.artifact, metadata=metadata),
    )
