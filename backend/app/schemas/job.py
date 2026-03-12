from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.editor_operations_schema import EditorApplyJobRequest
from app.utils.files import sanitize_filename

FILE_ID_PATTERN = r"^file_[A-Za-z0-9_-]{8,}$"
JOB_ID_PATTERN = r"^job_[A-Za-z0-9_-]{8,}$"
HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"
IMAGE_OUTPUT_FORMATS = {"jpg", "jpeg", "png", "webp"}
PAGE_POSITIONS = {
    "top_left",
    "top_center",
    "top_right",
    "center",
    "bottom_left",
    "bottom_center",
    "bottom_right",
}
WATERMARK_POSITIONS = PAGE_POSITIONS | {"diagonal"}
HTML_PAGE_SIZE_VALUES = {"A4", "A3", "Letter", "Legal"}
CONVERT_TO_PDF_PAGE_SIZE_VALUES = HTML_PAGE_SIZE_VALUES | {"original", "fit"}
PDFA_LEVEL_VALUES = {"1b", "2b", "3b"}
PAGE_NUMBERING_STYLES = {"arabic", "roman", "roman_lower", "roman_upper", "alpha_lower", "alpha_upper"}
SIGN_BORDER_STYLES = {"box", "underline", "none"}


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CanonicalJobCreateRequest(StrictSchema):
    tool_id: str = Field(min_length=2, max_length=64)
    payload: dict[str, Any]


class JobCreateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(pattern=JOB_ID_PATTERN)


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(pattern=JOB_ID_PATTERN)
    status: Literal["pending", "processing", "completed", "failed"]
    progress: int = Field(ge=0, le=100)
    error: str | None = None
    result_url: str | None = None
    download_url: str | None = None
    original_bytes: int | None = None
    compressed_bytes: int | None = None
    savings_pct: float | None = None
    pages_processed: int | None = None
    parts_count: int | None = None
    redactions_applied: int | None = None
    different_pages: int | None = None
    detected_language: str | None = None
    word_count: int | None = None
    processing_time_ms: int | None = None
    ocr_pages: int | None = None


class SingleFileJobRequest(StrictSchema):
    file_id: str = Field(pattern=FILE_ID_PATTERN)


class OutputFilenameMixin(StrictSchema):
    output_filename: str = Field(min_length=1, max_length=255)

    @field_validator("output_filename")
    @classmethod
    def validate_output_filename(cls, value: str) -> str:
        return sanitize_filename(value)


class MergeJobRequest(OutputFilenameMixin):
    file_ids: list[str] = Field(min_length=2, max_length=50)

    @field_validator("file_ids")
    @classmethod
    def validate_file_ids(cls, value: list[str]) -> list[str]:
        cls._validate_file_id_list(value)
        return value

    @staticmethod
    def _validate_file_id_list(value: list[str]) -> None:
        for file_id in value:
            if not file_id.startswith("file_"):
                raise ValueError("Each file_id must be a valid upload identifier.")


class SplitJobRequest(SingleFileJobRequest):
    mode: Literal["by_range", "every_n_pages", "by_bookmark"] = "by_range"
    ranges: str | None = Field(default=None, min_length=1, max_length=1000)
    every_n_pages: int | None = Field(default=None, ge=1, le=500)
    output_prefix: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("output_prefix")
    @classmethod
    def validate_output_prefix(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return sanitize_filename(value)

    @model_validator(mode="after")
    def validate_split_strategy(self) -> "SplitJobRequest":
        if self.mode == "by_range" and not self.ranges:
            raise ValueError("ranges is required when mode is 'by_range'.")
        if self.mode == "every_n_pages" and self.every_n_pages is None:
            raise ValueError("every_n_pages is required when mode is 'every_n_pages'.")
        return self


class PageListJobRequest(SingleFileJobRequest):
    pages: list[int] | None = None

    @field_validator("pages")
    @classmethod
    def validate_pages(cls, value: list[int] | None) -> list[int] | None:
        return validate_page_numbers(value)


class ExtractJobRequest(PageListJobRequest, OutputFilenameMixin):
    @model_validator(mode="after")
    def require_pages(self) -> "ExtractJobRequest":
        if not self.pages:
            raise ValueError("pages is required.")
        return self


class RemovePagesJobRequest(OutputFilenameMixin, StrictSchema):
    file_id: str = Field(pattern=FILE_ID_PATTERN)
    pages_to_remove: list[int] | None = None

    @field_validator("pages_to_remove")
    @classmethod
    def validate_pages_to_remove(cls, value: list[int] | None) -> list[int] | None:
        return validate_page_numbers(value)

    @model_validator(mode="after")
    def require_pages_to_remove(self) -> "RemovePagesJobRequest":
        if not self.pages_to_remove:
            raise ValueError("pages_to_remove is required.")
        return self


class ReorderJobRequest(OutputFilenameMixin, StrictSchema):
    file_id: str = Field(pattern=FILE_ID_PATTERN)
    page_order: list[int] | None = None

    @field_validator("page_order")
    @classmethod
    def validate_page_order(cls, value: list[int] | None) -> list[int] | None:
        return validate_page_numbers(value)

    @model_validator(mode="after")
    def require_page_order(self) -> "ReorderJobRequest":
        if not self.page_order:
            raise ValueError("page_order is required.")
        return self


class CompressJobRequest(SingleFileJobRequest, OutputFilenameMixin):
    level: Literal["low", "medium", "high"] = "medium"


class RepairJobRequest(SingleFileJobRequest, OutputFilenameMixin):
    pass


class OcrJobRequest(SingleFileJobRequest, OutputFilenameMixin):
    language: str = Field(min_length=2, max_length=32)
    dpi: int = Field(default=300, ge=72, le=600)


class ConvertToPdfJobRequest(OutputFilenameMixin, StrictSchema):
    file_id: str | None = Field(default=None, pattern=FILE_ID_PATTERN)
    file_ids: list[str] | None = Field(default=None, min_length=1, max_length=50)
    dpi: int | None = Field(default=None, ge=72, le=600)
    page_size: str | None = Field(default=None, min_length=2, max_length=32)
    include_speaker_notes: bool = False

    @field_validator("file_ids")
    @classmethod
    def validate_file_ids(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        MergeJobRequest._validate_file_id_list(value)
        return value

    @field_validator("page_size")
    @classmethod
    def validate_convert_to_pdf_page_size(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in CONVERT_TO_PDF_PAGE_SIZE_VALUES:
            raise ValueError("page_size must be one of original, fit, A4, A3, Letter, or Legal.")
        return value

    @model_validator(mode="after")
    def validate_source_fields(self) -> "ConvertToPdfJobRequest":
        if bool(self.file_id) == bool(self.file_ids):
            raise ValueError("Provide exactly one source mode: file_id or file_ids.")
        return self


class HtmlToPdfJobRequest(OutputFilenameMixin, StrictSchema):
    file_id: str | None = Field(default=None, pattern=FILE_ID_PATTERN)
    url: str | None = Field(default=None, min_length=8, max_length=2048)
    page_size: str = Field(default="A4", min_length=2, max_length=32)

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, value: str) -> str:
        if value not in HTML_PAGE_SIZE_VALUES:
            raise ValueError("page_size must be one of A4, A3, Letter, or Legal.")
        return value

    @model_validator(mode="after")
    def validate_html_source(self) -> "HtmlToPdfJobRequest":
        if bool(self.file_id) == bool(self.url):
            raise ValueError("Provide exactly one HTML source: file_id or url.")
        return self


class PdfToImageJobRequest(SingleFileJobRequest):
    format: Literal["jpg", "jpeg", "png", "webp"] = "jpg"
    dpi: int = Field(default=150, ge=72, le=600)
    quality: int = Field(default=85, ge=1, le=100)
    single_page: int | None = Field(default=None, ge=1, le=1000000)
    thumbnail: bool = False
    thumbnail_max_px: int = Field(default=512, ge=32, le=4096)


class PdfToOfficeJobRequest(SingleFileJobRequest):
    format: Literal["word", "excel", "ppt"]
    output_filename: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("output_filename")
    @classmethod
    def validate_pdf_to_office_output_filename(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return sanitize_filename(value)


class PdfToPdfAJobRequest(SingleFileJobRequest, OutputFilenameMixin):
    pdfa_level: str = Field(default="1b", min_length=2, max_length=16)

    @field_validator("pdfa_level")
    @classmethod
    def validate_pdfa_level(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in PDFA_LEVEL_VALUES:
            raise ValueError("pdfa_level must be one of 1b, 2b, or 3b.")
        return normalized


class RotateJobRequest(PageListJobRequest, OutputFilenameMixin):
    angle: int = Field(default=90, ge=-360, le=360)
    relative: bool = True


class WatermarkJobRequest(SingleFileJobRequest, OutputFilenameMixin):
    text: str = Field(min_length=1, max_length=500)
    position: str = Field(min_length=2, max_length=64)
    opacity: float = Field(default=0.3, ge=0.0, le=1.0)
    font_size: int = Field(default=72, ge=1, le=500)
    rotation: int = Field(default=45, ge=-360, le=360)
    color: str = Field(default="#000000", pattern=HEX_COLOR_PATTERN)
    font_family: str | None = Field(default=None, min_length=2, max_length=64)
    skip_pages: list[int] | None = None
    first_page_only: bool = False
    image_upload_id: str | None = Field(default=None, pattern=FILE_ID_PATTERN)

    @field_validator("position")
    @classmethod
    def validate_watermark_position(cls, value: str) -> str:
        if value not in WATERMARK_POSITIONS:
            raise ValueError("position is not supported for watermark placement.")
        return value

    @field_validator("skip_pages")
    @classmethod
    def validate_skip_pages(cls, value: list[int] | None) -> list[int] | None:
        return validate_page_numbers(value)


class PageNumbersJobRequest(SingleFileJobRequest, OutputFilenameMixin):
    position: str = Field(min_length=2, max_length=64)
    start_number: int = Field(default=1, ge=1, le=1000000)
    font_size: int = Field(default=12, ge=1, le=500)
    color: str = Field(default="#000000", pattern=HEX_COLOR_PATTERN)
    prefix: str | None = Field(default=None, max_length=64)
    suffix: str | None = Field(default=None, max_length=64)
    font_family: str | None = Field(default=None, min_length=2, max_length=64)
    numbering_style: str = Field(default="arabic", min_length=2, max_length=32)
    skip_first_n_pages: int = Field(default=0, ge=0, le=1000000)
    skip_last_n_pages: int = Field(default=0, ge=0, le=1000000)
    background_box: bool = False

    @field_validator("position")
    @classmethod
    def validate_page_number_position(cls, value: str) -> str:
        if value not in PAGE_POSITIONS:
            raise ValueError("position is not supported for page numbering.")
        return value

    @field_validator("numbering_style")
    @classmethod
    def validate_numbering_style(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in PAGE_NUMBERING_STYLES:
            raise ValueError("numbering_style is not supported for page numbering.")
        return normalized


class CropJobRequest(PageListJobRequest, OutputFilenameMixin):
    left: float | None = None
    bottom: float | None = None
    right: float | None = None
    top: float | None = None
    permanent_crop: bool = False
    auto_crop_whitespace: bool = False

    @model_validator(mode="after")
    def validate_crop_box(self) -> "CropJobRequest":
        coordinates = (self.left, self.bottom, self.right, self.top)
        has_any_coordinate = any(value is not None for value in coordinates)
        has_all_coordinates = all(value is not None for value in coordinates)

        if self.auto_crop_whitespace:
            if has_any_coordinate and not has_all_coordinates:
                raise ValueError("Provide either all crop coordinates or none when auto_crop_whitespace is enabled.")
            if not has_all_coordinates:
                return self
        elif not has_all_coordinates:
            raise ValueError("left, bottom, right, and top are required unless auto_crop_whitespace is enabled.")

        if self.right is None or self.left is None or self.top is None or self.bottom is None:
            return self
        if self.right <= self.left:
            raise ValueError("right must be greater than left.")
        if self.top <= self.bottom:
            raise ValueError("top must be greater than bottom.")
        return self


class UnlockJobRequest(SingleFileJobRequest, OutputFilenameMixin):
    password: str | None = Field(default=None, max_length=255)


class ProtectJobRequest(SingleFileJobRequest, OutputFilenameMixin):
    user_password: str | None = Field(default=None, min_length=1, max_length=255)
    owner_password: str | None = Field(default=None, min_length=1, max_length=255)
    encryption: Literal[128, 256] = 256
    allow_printing: bool = True
    allow_copying: bool = True
    allow_annotations: bool = True
    allow_form_filling: bool = True

    @model_validator(mode="after")
    def require_password(self) -> "ProtectJobRequest":
        if not self.user_password and not self.owner_password:
            raise ValueError("At least one password must be provided.")
        return self


class SignJobRequest(SingleFileJobRequest, OutputFilenameMixin):
    signature_text: str | None = Field(default=None, max_length=500)
    page: int = Field(default=1, ge=1, le=1000000)
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    use_digital_signature: bool = False
    cert_password: str | None = Field(default=None, max_length=255)
    cert_file_id: str | None = Field(default=None, pattern=FILE_ID_PATTERN)
    border_style: str = Field(default="box", min_length=2, max_length=32)
    include_timestamp: bool = True
    signature_image_upload_id: str | None = Field(default=None, pattern=FILE_ID_PATTERN)

    @field_validator("border_style")
    @classmethod
    def validate_border_style(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in SIGN_BORDER_STYLES:
            raise ValueError("border_style must be one of box, underline, or none.")
        return normalized


class RedactJobRequest(SingleFileJobRequest, OutputFilenameMixin):
    keywords: list[str] = Field(default_factory=list, max_length=100)
    patterns: list[str] = Field(default_factory=list, max_length=100)
    fill_color: str = Field(default="#000000", pattern=HEX_COLOR_PATTERN)
    preview_mode: bool = False
    whole_word: bool = False

    @field_validator("keywords", "patterns")
    @classmethod
    def normalize_string_list(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]

    @field_validator("patterns")
    @classmethod
    def validate_pattern_lengths(cls, value: list[str]) -> list[str]:
        for pattern in value:
            if len(pattern) > 180:
                raise ValueError("Regex patterns must be 180 characters or fewer.")
        return value

    @model_validator(mode="after")
    def require_redaction_targets(self) -> "RedactJobRequest":
        if not self.keywords and not self.patterns:
            raise ValueError("At least one keyword or regex pattern must be provided.")
        return self


class CompareJobRequest(OutputFilenameMixin):
    file_id_a: str = Field(pattern=FILE_ID_PATTERN)
    file_id_b: str = Field(pattern=FILE_ID_PATTERN)
    diff_mode: Literal["text", "visual", "combined"] = "combined"


class TranslateJobRequest(SingleFileJobRequest):
    target_language: str = Field(min_length=2, max_length=16)
    source_language: str | None = Field(default=None, min_length=2, max_length=16)
    output_filename: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("output_filename")
    @classmethod
    def validate_optional_output_filename(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return sanitize_filename(value)


class SummarizeJobRequest(SingleFileJobRequest):
    output_language: str = Field(default="en", min_length=2, max_length=16)
    length: Literal["short", "medium", "long"] = "medium"
    focus: str | None = Field(default=None, max_length=200)
    output_filename: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("output_filename")
    @classmethod
    def validate_summary_output_filename(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return sanitize_filename(value)


class ConvertFromPdfRouteRequest(StrictSchema):
    file_id: str = Field(pattern=FILE_ID_PATTERN)
    format: str | None = Field(default=None, min_length=2, max_length=16)
    dpi: int | None = Field(default=None, ge=72, le=600)
    quality: int | None = Field(default=None, ge=1, le=100)
    single_page: int | None = Field(default=None, ge=1, le=1000000)
    thumbnail: bool = False
    thumbnail_max_px: int | None = Field(default=None, ge=32, le=4096)
    pdfa_level: str | None = Field(default=None, min_length=2, max_length=16)
    output_filename: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("output_filename")
    @classmethod
    def validate_optional_output_filename(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return sanitize_filename(value)

    @model_validator(mode="after")
    def validate_dispatch_fields(self) -> "ConvertFromPdfRouteRequest":
        if self.pdfa_level:
            return self
        if not self.format:
            raise ValueError("format or pdfa_level is required.")
        return self


TOOL_PAYLOAD_MODELS: dict[str, type[StrictSchema]] = {
    "merge": MergeJobRequest,
    "split": SplitJobRequest,
    "extract": ExtractJobRequest,
    "remove": RemovePagesJobRequest,
    "reorder": ReorderJobRequest,
    "compress": CompressJobRequest,
    "repair": RepairJobRequest,
    "ocr": OcrJobRequest,
    "img2pdf": ConvertToPdfJobRequest,
    "word2pdf": ConvertToPdfJobRequest,
    "excel2pdf": ConvertToPdfJobRequest,
    "ppt2pdf": ConvertToPdfJobRequest,
    "html2pdf": HtmlToPdfJobRequest,
    "pdf2img": PdfToImageJobRequest,
    "pdf2word": PdfToOfficeJobRequest,
    "pdf2excel": PdfToOfficeJobRequest,
    "pdf2ppt": PdfToOfficeJobRequest,
    "pdf2pdfa": PdfToPdfAJobRequest,
    "rotate": RotateJobRequest,
    "editor_apply": EditorApplyJobRequest,
    "watermark": WatermarkJobRequest,
    "pagenums": PageNumbersJobRequest,
    "crop": CropJobRequest,
    "unlock": UnlockJobRequest,
    "protect": ProtectJobRequest,
    "sign": SignJobRequest,
    "redact": RedactJobRequest,
    "compare": CompareJobRequest,
    "translate": TranslateJobRequest,
    "summarize": SummarizeJobRequest,
}


def validate_page_numbers(value: list[int] | None) -> list[int] | None:
    if value is None:
        return None
    if not value:
        return None
    for page in value:
        if page < 1:
            raise ValueError("Page numbers must be positive integers.")
    return value
