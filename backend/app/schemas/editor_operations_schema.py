"""
editor_operations.py — Pydantic schemas for the PDF Editor JSON operation protocol
===================================================================================
Defines the complete contract between the frontend editor and the backend processor.

Coordinate system convention:
  All coordinates are in PDF points (1 pt = 1/72 inch).
  Origin (0, 0) is the TOP-LEFT corner of the page (matching fitz / HTML canvas).
  x increases rightward, y increases downward.
  The frontend EditorStateManager must convert canvas-pixel coords to PDF points
  by dividing by the render scale factor (canvas_width_px / page_width_pts).

Operation ordering contract:
  1. Overlay operations (text, highlight, draw, image, signature, shape)
     are applied first, in their listed order, to the page content stream.
  2. Structural operations (page_rotate, page_delete, page_reorder) are applied
     after all overlays.  Only one page_reorder per job is honoured (the last).
"""
from __future__ import annotations

import base64
import re
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ─── Constants ────────────────────────────────────────────────────────────────

HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"
FILE_ID_PATTERN = r"^file_[A-Za-z0-9_-]{8,}$"
PAGE_RANGE = Field(ge=1, le=10_000)

# Hard limits
MAX_OPERATIONS_PER_JOB: int = 2_000
MAX_OVERLAY_OPS_PER_PAGE: int = 500
MAX_IMAGE_BASE64_BYTES: int = 4 * 1024 * 1024  # 4 MB base64 ≈ 3 MB decoded
MAX_TEXT_LENGTH: int = 8_000
MAX_PATH_DATA_CHARS: int = 100_000     # SVG path string length
MAX_HIGHLIGHT_RECTS: int = 200
MAX_SHAPE_STROKE_WIDTH: float = 100.0
MAX_FONT_SIZE: float = 288.0
MAX_REORDER_PAGES: int = 1_000

# Allowed font names (fitz built-in PDF base-14 fonts)
ALLOWED_FONT_NAMES: frozenset[str] = frozenset({
    "helv",          # Helvetica
    "helv-bold",     # Helvetica-Bold
    "helv-italic",   # Helvetica-Oblique
    "helv-bold-italic",  # Helvetica-BoldOblique
    "timr",          # Times-Roman
    "timb",          # Times-Bold
    "timi",          # Times-Italic
    "timbi",         # Times-BoldItalic
    "cour",          # Courier
    "courb",         # Courier-Bold
    "couri",         # Courier-Oblique
    "courbi",        # Courier-BoldOblique
    "symb",          # Symbol
    "zadb",          # ZapfDingbats
})

# Reverse mapping for bold/italic combos sent from the frontend
_FONT_ALIAS_MAP: dict[str, str] = {
    "helv-bold-italic": "helv-bold-italic",
    "helvetica-bolditalic": "helv-bold-italic",
    "helvetica": "helv",
    "times": "timr",
    "courier": "cour",
    "symbol": "symb",
    "zapfdingbats": "zadb",
}


# ─── Base ─────────────────────────────────────────────────────────────────────

class EditorOperationBase(BaseModel):
    """
    Base class for all editor operations.
    All concrete operation classes inherit this and add a ``type`` literal field.
    ``model_config`` uses ``extra="forbid"`` to reject unknown JSON fields.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = PAGE_RANGE
    """1-indexed page number this operation targets."""


# ─── Overlay operations ───────────────────────────────────────────────────────

class TextInsertOperation(EditorOperationBase):
    """
    Inserts a text box permanently into the PDF content stream.
    Supports bold, italic, color, opacity, alignment, and rotation.
    """
    type: Literal["text_insert"]
    x: float = Field(ge=0.0, le=15_000.0)
    y: float = Field(ge=0.0, le=20_000.0)
    width: float = Field(ge=1.0, le=15_000.0)
    height: float = Field(ge=1.0, le=20_000.0)
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    font_size: float = Field(ge=2.0, le=MAX_FONT_SIZE, default=12.0)
    font_name: str = Field(default="helv", max_length=32)
    color: str = Field(default="#000000", pattern=HEX_COLOR_PATTERN)
    opacity: float = Field(ge=0.0, le=1.0, default=1.0)
    align: Literal["left", "center", "right"] = "left"
    rotation: float = Field(ge=-360.0, le=360.0, default=0.0)
    line_height: float = Field(ge=0.5, le=5.0, default=1.2)
    """Line height multiplier relative to font_size."""

    @field_validator("font_name")
    @classmethod
    def validate_font(cls, value: str) -> str:
        normalized = value.lower().strip()
        resolved = _FONT_ALIAS_MAP.get(normalized, normalized)
        if resolved not in ALLOWED_FONT_NAMES:
            # Silently fall back to Helvetica rather than rejecting — UX choice
            return "helv"
        return resolved

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        # Strip null bytes and other control chars except tab/newline/CR
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)


class TextReplaceOperation(EditorOperationBase):
    """
    Replaces existing PDF text by covering the original text bounds and writing
    replacement text using the resolved font and box metrics.
    """
    type: Literal["text_replace"]
    original_text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    replacement_text: str = Field(min_length=0, max_length=MAX_TEXT_LENGTH, default="")
    original_x: float = Field(ge=0.0, le=15_000.0)
    original_y: float = Field(ge=0.0, le=20_000.0)
    original_width: float = Field(ge=1.0, le=15_000.0)
    original_height: float = Field(ge=1.0, le=20_000.0)
    x: float = Field(ge=0.0, le=15_000.0)
    y: float = Field(ge=0.0, le=20_000.0)
    width: float = Field(ge=1.0, le=15_000.0)
    height: float = Field(ge=1.0, le=20_000.0)
    font_size: float = Field(ge=2.0, le=MAX_FONT_SIZE, default=12.0)
    font_name: str = Field(default="helv", max_length=32)
    color: str = Field(default="#000000", pattern=HEX_COLOR_PATTERN)
    opacity: float = Field(ge=0.0, le=1.0, default=1.0)
    align: Literal["left", "center", "right"] = "left"
    rotation: float = Field(ge=-360.0, le=360.0, default=0.0)
    line_height: float = Field(ge=0.5, le=5.0, default=1.2)

    @field_validator("font_name")
    @classmethod
    def validate_font(cls, value: str) -> str:
        normalized = value.lower().strip()
        resolved = _FONT_ALIAS_MAP.get(normalized, normalized)
        if resolved not in ALLOWED_FONT_NAMES:
            return "helv"
        return resolved

    @field_validator("original_text", "replacement_text")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)


class HighlightOperation(EditorOperationBase):
    """
    Adds a translucent color highlight rectangle over the specified area.
    Multiple rects can be provided to highlight a text selection spanning lines.
    """
    type: Literal["highlight"]
    rects: list[tuple[float, float, float, float]] = Field(
        min_length=1,
        max_length=MAX_HIGHLIGHT_RECTS,
    )
    """
    Each rect is (x0, y0, x1, y1) in PDF points (top-left origin).
    x0 < x1 and y0 < y1 are enforced.
    """
    color: str = Field(default="#FFFF00", pattern=HEX_COLOR_PATTERN)
    opacity: float = Field(ge=0.0, le=1.0, default=0.4)

    @field_validator("rects")
    @classmethod
    def validate_rects(
        cls, rects: list[tuple[float, float, float, float]]
    ) -> list[tuple[float, float, float, float]]:
        for i, rect in enumerate(rects):
            if len(rect) != 4:
                raise ValueError(f"rect[{i}] must be a 4-element tuple (x0, y0, x1, y1).")
            x0, y0, x1, y1 = rect
            if x0 >= x1 or y0 >= y1:
                raise ValueError(f"rect[{i}] must have x0 < x1 and y0 < y1.")
            for v in rect:
                if not (-1.0 <= v <= 20_000.0):
                    raise ValueError(f"rect[{i}] coordinate {v} is out of range.")
        return rects


class DrawOperation(EditorOperationBase):
    """
    Renders a freehand pen stroke or polyline path permanently into the page.
    ``path_data`` is a compact SVG-compatible path string with absolute coordinates
    in PDF points (top-left origin).  Supported commands: M, L, C, Q, H, V, Z.
    """
    type: Literal["draw"]
    path_data: str = Field(min_length=3, max_length=MAX_PATH_DATA_CHARS)
    color: str = Field(default="#000000", pattern=HEX_COLOR_PATTERN)
    width: float = Field(ge=0.1, le=MAX_SHAPE_STROKE_WIDTH, default=2.0)
    opacity: float = Field(ge=0.0, le=1.0, default=1.0)
    cap_style: Literal["round", "square", "butt"] = "round"
    join_style: Literal["round", "miter", "bevel"] = "round"

    @field_validator("path_data")
    @classmethod
    def validate_path_data(cls, value: str) -> str:
        # Reject clearly invalid or potentially malicious path data
        stripped = value.strip()
        if not stripped:
            raise ValueError("path_data must not be empty.")
        # Must start with an 'M' or 'm' command
        if not re.match(r"^[Mm]", stripped):
            raise ValueError("path_data must start with a moveto (M/m) command.")
        # Reject characters not valid in SVG path data
        if re.search(r"[^0-9MmLlCcQqHhVvZzSsTt.,\s\-+eE]", stripped):
            raise ValueError("path_data contains invalid characters.")
        return stripped


class ImageInsertOperation(EditorOperationBase):
    """
    Inserts a raster image into the PDF at the specified position and size.
    ``image_data`` must be a valid base64-encoded JPEG or PNG payload
    (the data-URI prefix ``data:image/...;base64,`` is stripped automatically).
    """
    type: Literal["image_insert"]
    x: float = Field(ge=0.0, le=15_000.0)
    y: float = Field(ge=0.0, le=20_000.0)
    width: float = Field(ge=1.0, le=15_000.0)
    height: float = Field(ge=1.0, le=20_000.0)
    image_data: str = Field(min_length=4, max_length=MAX_IMAGE_BASE64_BYTES)
    """Base64-encoded image (JPEG or PNG). Data-URI prefix is accepted."""
    opacity: float = Field(ge=0.0, le=1.0, default=1.0)
    rotation: float = Field(ge=-360.0, le=360.0, default=0.0)

    @field_validator("image_data")
    @classmethod
    def validate_image_data(cls, value: str) -> str:
        # Strip data-URI prefix if present
        if value.startswith("data:"):
            if ";base64," not in value:
                raise ValueError("Image data-URI must use base64 encoding.")
            value = value.split(";base64,", 1)[1]
        # Fast-path length check before decoding
        if len(value) > MAX_IMAGE_BASE64_BYTES:
            raise ValueError(
                f"Inline image data must not exceed {MAX_IMAGE_BASE64_BYTES // 1024} KB."
            )
        # Validate base64 alphabet
        try:
            raw = base64.b64decode(value, validate=True)
        except Exception as exc:
            raise ValueError("image_data is not valid base64.") from exc
        # Validate image header
        if not (raw[:2] == b"\xff\xd8" or raw[:8] == b"\x89PNG\r\n\x1a\n"):
            raise ValueError("image_data must be a JPEG or PNG image.")
        return value


class SignatureInsertOperation(EditorOperationBase):
    """
    Inserts a handwritten-signature image (typically a transparent PNG drawn
    on a canvas with a signature pad library) into the PDF.
    Semantically identical to ImageInsertOperation but tagged distinctly for
    audit trail purposes.
    """
    type: Literal["signature_insert"]
    x: float = Field(ge=0.0, le=15_000.0)
    y: float = Field(ge=0.0, le=20_000.0)
    width: float = Field(ge=1.0, le=15_000.0)
    height: float = Field(ge=1.0, le=20_000.0)
    image_data: str = Field(min_length=4, max_length=MAX_IMAGE_BASE64_BYTES)
    opacity: float = Field(ge=0.0, le=1.0, default=1.0)

    @field_validator("image_data")
    @classmethod
    def validate_signature_data(cls, value: str) -> str:
        if value.startswith("data:"):
            if ";base64," not in value:
                raise ValueError("Signature data-URI must use base64 encoding.")
            value = value.split(";base64,", 1)[1]
        if len(value) > MAX_IMAGE_BASE64_BYTES:
            raise ValueError(
                f"Signature image must not exceed {MAX_IMAGE_BASE64_BYTES // 1024} KB."
            )
        try:
            raw = base64.b64decode(value, validate=True)
        except Exception as exc:
            raise ValueError("image_data is not valid base64.") from exc
        # Signatures are almost always PNG (transparent background)
        if not (raw[:2] == b"\xff\xd8" or raw[:8] == b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Signature data must be a JPEG or PNG image.")
        return value


class ShapeInsertOperation(EditorOperationBase):
    """
    Draws a geometric shape (rectangle, circle/ellipse) permanently into the page.
    Both fill and stroke are optional; stroke_width=0 means no border.
    """
    type: Literal["shape_insert"]
    x: float = Field(ge=0.0, le=15_000.0)
    y: float = Field(ge=0.0, le=20_000.0)
    width: float = Field(ge=0.5, le=15_000.0)
    height: float = Field(ge=0.5, le=20_000.0)
    shape_type: Literal["rect", "circle", "line"]
    fill_color: str = Field(default="#FFFFFF", pattern=HEX_COLOR_PATTERN)
    stroke_color: str = Field(default="#000000", pattern=HEX_COLOR_PATTERN)
    stroke_width: float = Field(ge=0.0, le=MAX_SHAPE_STROKE_WIDTH, default=1.0)
    fill_opacity: float = Field(ge=0.0, le=1.0, default=0.0)
    stroke_opacity: float = Field(ge=0.0, le=1.0, default=1.0)
    rotation: float = Field(ge=-360.0, le=360.0, default=0.0)


# ─── Structural operations ────────────────────────────────────────────────────

class PageRotateOperation(EditorOperationBase):
    """
    Rotates a single page.  ``angle`` is added to the page's current
    rotation (relative rotation).  Normalised to 0, 90, 180, or 270.
    """
    type: Literal["page_rotate"]
    angle: Literal[90, 180, 270, -90, -180, -270]


class PageDeleteOperation(EditorOperationBase):
    """
    Marks a single page for deletion.
    Multiple PageDeleteOperations are collected and executed together.
    The ``page`` field identifies the page to delete (1-indexed, in original numbering).
    """
    type: Literal["page_delete"]
    # page is inherited from EditorOperationBase


class PageReorderOperation(EditorOperationBase):
    """
    Reorders all pages.  ``new_order`` is a complete list of 1-indexed
    original page numbers specifying the desired output order.
    Example: [3, 1, 2] moves original page 3 to position 1.
    Only the final PageReorderOperation in the operations list is applied.
    """
    type: Literal["page_reorder"]
    new_order: list[int] = Field(min_length=1, max_length=MAX_REORDER_PAGES)

    @field_validator("new_order")
    @classmethod
    def validate_new_order(cls, value: list[int]) -> list[int]:
        for p in value:
            if p < 1:
                raise ValueError("new_order page numbers must be ≥ 1.")
        return value

    @model_validator(mode="after")
    def validate_complete_permutation(self) -> "PageReorderOperation":
        pages = self.new_order
        # Guard: no duplicates
        if len(pages) != len(set(pages)):
            raise ValueError("new_order must not contain duplicate page numbers.")
        # Guard: all values must form a contiguous 1-based range [1..N]
        # (the exact page count N is not yet known at schema-validation time,
        # so we verify the sequence is contiguous and starts at 1 — the backend
        # validator in editor_validation.py checks the match against page_count)
        min_page = min(pages)
        max_page = max(pages)
        if min_page != 1:
            raise ValueError(
                f"new_order must start at page 1, but the smallest value is {min_page}."
            )
        if max_page != len(pages):
            raise ValueError(
                f"new_order appears non-contiguous: {len(pages)} pages supplied "
                f"but highest page number is {max_page}. "
                "new_order must be a complete permutation of 1..N."
            )
        return self


# ─── Discriminated union ──────────────────────────────────────────────────────

# Annotated discriminated union — Pydantic uses the ``type`` field for dispatch
AnyEditorOperation = Annotated[
    Union[
        TextInsertOperation,
        TextReplaceOperation,
        HighlightOperation,
        DrawOperation,
        ImageInsertOperation,
        SignatureInsertOperation,
        ShapeInsertOperation,
        PageRotateOperation,
        PageDeleteOperation,
        PageReorderOperation,
    ],
    Field(discriminator="type"),
]

# Names of operations that modify the page content stream (overlay operations)
OVERLAY_OPERATION_TYPES: frozenset[str] = frozenset({
    "text_insert",
    "text_replace",
    "highlight",
    "draw",
    "image_insert",
    "signature_insert",
    "shape_insert",
})

# Names of operations that modify the document structure
STRUCTURAL_OPERATION_TYPES: frozenset[str] = frozenset({
    "page_rotate",
    "page_delete",
    "page_reorder",
})


# ─── Top-level job request schema ─────────────────────────────────────────────

class EditorApplyJobRequest(BaseModel):
    """
    The complete job request payload for the PDF editor apply processor.
    Accepted as ``payload`` in the canonical job-create request with
    ``tool_id = "editor_apply"``.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    file_id: str = Field(pattern=FILE_ID_PATTERN)
    output_filename: str = Field(min_length=1, max_length=255)
    operations: list[AnyEditorOperation] = Field(
        min_length=1,
        max_length=MAX_OPERATIONS_PER_JOB,
    )
    canvas_width: float | None = Field(
        default=None, ge=100.0, le=10_000.0,
        description="Width in pixels of the editor canvas used for this document. "
                    "Stored in metadata for audit purposes.",
    )
    canvas_height: float | None = Field(
        default=None, ge=100.0, le=100_000.0,
    )

    @field_validator("output_filename")
    @classmethod
    def sanitize_output_filename(cls, value: str) -> str:
        from app.utils.files import sanitize_filename
        return sanitize_filename(value)

    @model_validator(mode="after")
    def validate_operation_counts(self) -> "EditorApplyJobRequest":
        per_page: dict[int, int] = {}
        for op in self.operations:
            if op.type in OVERLAY_OPERATION_TYPES:
                per_page[op.page] = per_page.get(op.page, 0) + 1
                if per_page[op.page] > MAX_OVERLAY_OPS_PER_PAGE:
                    raise ValueError(
                        f"Page {op.page} has more than {MAX_OVERLAY_OPS_PER_PAGE} "
                        "overlay operations, which exceeds the per-page limit."
                    )
        return self


def parse_editor_operations(raw: list[dict[str, Any]]) -> list[AnyEditorOperation]:
    """
    Parse a list of raw dicts into a typed ``AnyEditorOperation`` list.
    Raises ``ValueError`` with a detailed message on schema violations.
    Used by ``EditorApplyJobRequest`` and tests.
    """
    from pydantic import TypeAdapter
    adapter: TypeAdapter[AnyEditorOperation] = TypeAdapter(AnyEditorOperation)
    results: list[AnyEditorOperation] = []
    for idx, item in enumerate(raw):
        try:
            results.append(adapter.validate_python(item))
        except Exception as exc:
            raise ValueError(f"operations[{idx}]: {exc}") from exc
    return results
