from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

GENERIC_DECLARED_CONTENT_TYPES = {
    "",
    "application/octet-stream",
    "binary/octet-stream",
    "application/x-download",
}

OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")


class UploadValidationError(Exception):
    def __init__(self, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class DetectedUploadFile:
    extension: str
    content_type: str
    kind: str


@dataclass(frozen=True)
class FileTypeSpec:
    content_type: str
    kind: str
    allowed_declared_content_types: set[str]


FILE_TYPE_SPECS: dict[str, FileTypeSpec] = {
    ".pdf": FileTypeSpec(
        content_type="application/pdf",
        kind="pdf",
        allowed_declared_content_types={"application/pdf"},
    ),
    ".jpg": FileTypeSpec(
        content_type="image/jpeg",
        kind="image",
        allowed_declared_content_types={"image/jpeg", "image/pjpeg"},
    ),
    ".jpeg": FileTypeSpec(
        content_type="image/jpeg",
        kind="image",
        allowed_declared_content_types={"image/jpeg", "image/pjpeg"},
    ),
    ".png": FileTypeSpec(
        content_type="image/png",
        kind="image",
        allowed_declared_content_types={"image/png"},
    ),
    ".gif": FileTypeSpec(
        content_type="image/gif",
        kind="image",
        allowed_declared_content_types={"image/gif"},
    ),
    ".bmp": FileTypeSpec(
        content_type="image/bmp",
        kind="image",
        allowed_declared_content_types={"image/bmp", "image/x-ms-bmp"},
    ),
    ".tiff": FileTypeSpec(
        content_type="image/tiff",
        kind="image",
        allowed_declared_content_types={"image/tiff"},
    ),
    ".webp": FileTypeSpec(
        content_type="image/webp",
        kind="image",
        allowed_declared_content_types={"image/webp"},
    ),
    ".doc": FileTypeSpec(
        content_type="application/msword",
        kind="office",
        allowed_declared_content_types={"application/msword"},
    ),
    ".docx": FileTypeSpec(
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        kind="office",
        allowed_declared_content_types={
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
    ),
    ".xls": FileTypeSpec(
        content_type="application/vnd.ms-excel",
        kind="office",
        allowed_declared_content_types={"application/vnd.ms-excel"},
    ),
    ".xlsx": FileTypeSpec(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        kind="office",
        allowed_declared_content_types={
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
    ),
    ".ppt": FileTypeSpec(
        content_type="application/vnd.ms-powerpoint",
        kind="office",
        allowed_declared_content_types={"application/vnd.ms-powerpoint"},
    ),
    ".pptx": FileTypeSpec(
        content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        kind="office",
        allowed_declared_content_types={
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        },
    ),
    ".html": FileTypeSpec(
        content_type="text/html",
        kind="html",
        allowed_declared_content_types={"text/html", "application/xhtml+xml"},
    ),
    ".htm": FileTypeSpec(
        content_type="text/html",
        kind="html",
        allowed_declared_content_types={"text/html", "application/xhtml+xml"},
    ),
}


def sanitize_filename(filename: str | None) -> str:
    if filename is None:
        raise UploadValidationError("Uploaded file must include a filename.")

    normalized = filename.replace("\\", "/").split("/")[-1].strip()
    normalized = re.sub(r"[\x00-\x1f\x7f]", "", normalized)
    normalized = normalized.strip(". ")

    if not normalized:
        raise UploadValidationError("Uploaded file must include a valid filename.")

    return normalized


def detect_upload_file(
    *,
    file_path: Path,
    original_filename: str,
    declared_content_type: str | None,
) -> DetectedUploadFile:
    extension = Path(original_filename).suffix.lower()
    spec = FILE_TYPE_SPECS.get(extension)
    if spec is None:
        raise UploadValidationError("Unsupported file type.", status_code=415)

    header = _read_header(file_path)
    if not header:
        raise UploadValidationError("Uploaded file is empty.")

    _validate_declared_content_type(
        extension=extension,
        declared_content_type=declared_content_type,
        allowed_content_types=spec.allowed_declared_content_types,
    )

    if extension == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise UploadValidationError("Uploaded file content does not match the .pdf extension.")
    elif extension in {".jpg", ".jpeg"}:
        if not header.startswith(b"\xff\xd8\xff"):
            raise UploadValidationError("Uploaded file content does not match the .jpg extension.")
    elif extension == ".png":
        if not header.startswith(b"\x89PNG\r\n\x1a\n"):
            raise UploadValidationError("Uploaded file content does not match the .png extension.")
    elif extension == ".gif":
        if not header.startswith((b"GIF87a", b"GIF89a")):
            raise UploadValidationError("Uploaded file content does not match the .gif extension.")
    elif extension == ".bmp":
        if not header.startswith(b"BM"):
            raise UploadValidationError("Uploaded file content does not match the .bmp extension.")
    elif extension == ".tiff":
        if not header.startswith((b"II*\x00", b"MM\x00*")):
            raise UploadValidationError("Uploaded file content does not match the .tiff extension.")
    elif extension == ".webp":
        if not (header.startswith(b"RIFF") and header[8:12] == b"WEBP"):
            raise UploadValidationError("Uploaded file content does not match the .webp extension.")
    elif extension in {".doc", ".xls", ".ppt"}:
        if not header.startswith(OLE_MAGIC):
            raise UploadValidationError(
                "Uploaded file content does not match the expected legacy Office format."
            )
    elif extension in {".docx", ".xlsx", ".pptx"}:
        _validate_openxml_package(file_path=file_path, extension=extension)
    elif extension in {".html", ".htm"}:
        _validate_html(file_path=file_path)

    return DetectedUploadFile(
        extension=extension,
        content_type=spec.content_type,
        kind=spec.kind,
    )


def _validate_declared_content_type(
    *,
    extension: str,
    declared_content_type: str | None,
    allowed_content_types: set[str],
) -> None:
    if declared_content_type is None:
        return

    normalized = declared_content_type.lower().strip()
    if normalized in GENERIC_DECLARED_CONTENT_TYPES:
        return

    if normalized not in allowed_content_types:
        raise UploadValidationError(
            f"Uploaded file content does not match the provided MIME type for {extension}.",
            status_code=415,
        )


def _validate_openxml_package(*, file_path: Path, extension: str) -> None:
    if not zipfile.is_zipfile(file_path):
        raise UploadValidationError(
            f"Uploaded file content does not match the {extension} extension.",
        )

    marker_by_extension = {
        ".docx": "word/",
        ".xlsx": "xl/",
        ".pptx": "ppt/",
    }
    marker = marker_by_extension[extension]

    try:
        with zipfile.ZipFile(file_path) as archive:
            names = archive.namelist()
    except zipfile.BadZipFile as exc:
        raise UploadValidationError(
            f"Uploaded file content does not match the {extension} extension.",
        ) from exc

    if "[Content_Types].xml" not in names or not any(name.startswith(marker) for name in names):
        raise UploadValidationError(
            f"Uploaded file content does not match the {extension} extension.",
        )


def _validate_html(*, file_path: Path) -> None:
    header = _read_header(file_path)
    if b"\x00" in header:
        raise UploadValidationError("Uploaded file content does not match the .html extension.")

    sample = header.decode("utf-8", errors="ignore").lower()
    markers = ("<!doctype html", "<html", "<head", "<body", "<title")
    if not any(marker in sample for marker in markers):
        raise UploadValidationError("Uploaded file content does not match the .html extension.")


def _read_header(file_path: Path, size: int = 8192) -> bytes:
    with file_path.open("rb") as file_handle:
        return file_handle.read(size)
