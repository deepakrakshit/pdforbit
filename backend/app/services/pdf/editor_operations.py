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
MAX_OPERATIONS_PER_JOB: int = 5_000
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
        if len(pages) != len(set(pages)):
            raise ValueError("new_order must not contain duplicate page numbers.")
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


import base64 as _base64
import re as _re

import fitz

from app.services.pdf.advanced_utils import hex_to_rgb
from app.services.pdf.common import PdfProcessingError

_REDACT_IMAGE_NONE: int = getattr(fitz, "PDF_REDACT_IMAGE_NONE", 0)
_REDACT_GRAPHICS_NONE: int = getattr(fitz, "PDF_REDACT_LINE_ART_NONE", 0)
_REDACT_TEXT_CHAR: int = getattr(
    fitz,
    "PDF_REDACT_TEXT_REMOVE",
    getattr(fitz, "PDF_REDACT_TEXT_CHAR", 0),
)


def apply_overlay_operations(doc: fitz.Document, operations: list[AnyEditorOperation]) -> int:
    applied = 0
    for index, operation in enumerate(operations):
        try:
            page = doc[operation.page - 1]
        except Exception as exc:
            raise PdfProcessingError(
                code="editor_invalid_page",
                user_message=f"operations[{index}] ({operation.type}) references a missing page.",
            ) from exc

        try:
            if operation.type == "text_insert":
                _apply_text_insert(page, operation)
            elif operation.type == "text_replace":
                _apply_text_replace(page, operation)
            elif operation.type == "highlight":
                _apply_highlight(page, operation)
            elif operation.type == "draw":
                _apply_draw(page, operation)
            elif operation.type == "image_insert":
                _apply_image(page, operation)
            elif operation.type == "signature_insert":
                _apply_signature(page, operation)
            elif operation.type == "shape_insert":
                _apply_shape(page, operation)
            else:
                raise PdfProcessingError(
                    code="editor_invalid_operation",
                    user_message=f"Unsupported editor operation type: {operation.type}.",
                )
        except PdfProcessingError:
            raise
        except Exception as exc:
            raise PdfProcessingError(
                code="editor_apply_failed",
                user_message=f"operations[{index}] ({operation.type}) could not be applied.",
            ) from exc

        applied += 1

    return applied


def apply_structural_operations(
    *,
    source_path: Path,
    output_path: Path,
    operations: list[AnyEditorOperation],
) -> None:
    rotations: dict[int, int] = {}
    pages_to_delete: set[int] = set()
    reorder: list[int] | None = None

    for operation in operations:
        if operation.type == "page_rotate":
            rotations[operation.page] = (rotations.get(operation.page, 0) + int(operation.angle)) % 360
        elif operation.type == "page_delete":
            pages_to_delete.add(operation.page)
        elif operation.type == "page_reorder":
            reorder = list(operation.new_order)

    try:
        with fitz.open(str(source_path)) as document:
            for page_number, rotation in rotations.items():
                if 1 <= page_number <= document.page_count:
                    page = document[page_number - 1]
                    page.set_rotation((page.rotation + rotation) % 360)

            surviving_indices = [
                page_index
                for page_index in range(document.page_count)
                if (page_index + 1) not in pages_to_delete
            ]

            if not surviving_indices:
                raise PdfProcessingError(
                    code="editor_cannot_delete_all_pages",
                    user_message="The editor operations would delete all pages from the document.",
                )

            if reorder is not None:
                try:
                    ordered_indices = [surviving_indices[position - 1] for position in reorder]
                except IndexError as exc:
                    raise PdfProcessingError(
                        code="editor_invalid_reorder",
                        user_message="page_reorder references a page position that does not exist after deletions.",
                    ) from exc
            else:
                ordered_indices = surviving_indices

            result = fitz.open()
            try:
                for page_index in ordered_indices:
                    result.insert_pdf(document, from_page=page_index, to_page=page_index)
                result.save(str(output_path), garbage=3, deflate=True)
            finally:
                result.close()
    except PdfProcessingError:
        raise
    except Exception as exc:
        raise PdfProcessingError(
            code="editor_structure_failed",
            user_message="Unable to apply the requested page changes.",
        ) from exc


def _apply_text_insert(page: fitz.Page, operation: TextInsertOperation) -> None:
    rect = fitz.Rect(operation.x, operation.y, operation.x + operation.width, operation.y + operation.height)
    _insert_textbox_with_fit(
        page=page,
        rect=rect,
        text=operation.text,
        font_size=operation.font_size,
        font_name=operation.font_name,
        color=hex_to_rgb(operation.color),
        align=operation.align,
        rotation=operation.rotation,
        error_code="editor_text_overflow",
        error_message="Inserted text does not fit inside the requested text box.",
    )


def _apply_text_replace(page: fitz.Page, operation: TextReplaceOperation) -> None:
    source_rect = fitz.Rect(
        operation.original_x,
        operation.original_y,
        operation.original_x + operation.original_width,
        operation.original_y + operation.original_height,
    )
    replacement_rect = fitz.Rect(
        operation.x,
        operation.y,
        operation.x + operation.width,
        operation.y + operation.height,
    )

    matched_style = _resolve_text_replace_style(page, operation, source_rect)
    padding = max(0.75, min((matched_style["font_size"] or operation.font_size) * 0.12, 2.0))
    cover_rect = fitz.Rect(
        source_rect.x0 - padding,
        source_rect.y0 - padding,
        source_rect.x1 + padding,
        source_rect.y1 + padding,
    )

    _remove_text_region(page, cover_rect)

    if not operation.replacement_text.strip():
        return

    _insert_textbox_with_fit(
        page=page,
        rect=replacement_rect,
        text=operation.replacement_text,
        font_size=matched_style["font_size"],
        font_name=matched_style["font_name"],
        color=matched_style["color"],
        align=matched_style["align"],
        rotation=matched_style["rotation"],
        error_code="editor_text_replace_overflow",
        error_message="Replacement text does not fit inside the original text region.",
    )


def _apply_highlight(page: fitz.Page, operation: HighlightOperation) -> None:
    fill = hex_to_rgb(operation.color)
    for x0, y0, x1, y1 in operation.rects:
        page.draw_rect(
            fitz.Rect(x0, y0, x1, y1),
            color=None,
            fill=fill,
            fill_opacity=operation.opacity,
            overlay=True,
        )


def _apply_draw(page: fitz.Page, operation: DrawOperation) -> None:
    segments = _path_segments(operation.path_data)
    color = hex_to_rgb(operation.color)
    if not segments:
        raise PdfProcessingError(
            code="editor_invalid_draw_path",
            user_message="The drawing path did not contain any drawable segments.",
        )

    for x0, y0, x1, y1 in segments:
        page.draw_line(
            fitz.Point(x0, y0),
            fitz.Point(x1, y1),
            color=color,
            width=operation.width,
            overlay=True,
        )


def _apply_image(page: fitz.Page, operation: ImageInsertOperation) -> None:
    rect = fitz.Rect(operation.x, operation.y, operation.x + operation.width, operation.y + operation.height)
    page.insert_image(rect, stream=_decode_image_data(operation.image_data), overlay=True)


def _apply_signature(page: fitz.Page, operation: SignatureInsertOperation) -> None:
    rect = fitz.Rect(operation.x, operation.y, operation.x + operation.width, operation.y + operation.height)
    page.insert_image(rect, stream=_decode_image_data(operation.image_data), overlay=True)


def _apply_shape(page: fitz.Page, operation: ShapeInsertOperation) -> None:
    rect = fitz.Rect(operation.x, operation.y, operation.x + operation.width, operation.y + operation.height)
    stroke = hex_to_rgb(operation.stroke_color) if operation.stroke_width > 0 else None
    fill = hex_to_rgb(operation.fill_color) if operation.fill_opacity > 0 else None

    if operation.shape_type == "line":
        page.draw_line(
            fitz.Point(rect.x0, rect.y0),
            fitz.Point(rect.x1, rect.y1),
            color=stroke or hex_to_rgb(operation.stroke_color),
            width=max(operation.stroke_width, 1.0),
            overlay=True,
        )
        return

    if operation.shape_type == "circle":
        page.draw_oval(
            rect,
            color=stroke,
            fill=fill,
            width=operation.stroke_width,
            fill_opacity=operation.fill_opacity,
            stroke_opacity=operation.stroke_opacity,
            overlay=True,
        )
        return

    page.draw_rect(
        rect,
        color=stroke,
        fill=fill,
        width=operation.stroke_width,
        fill_opacity=operation.fill_opacity,
        stroke_opacity=operation.stroke_opacity,
        overlay=True,
    )


def _alignment_value(value: Literal["left", "center", "right"]) -> int:
    if value == "center":
        return 1
    if value == "right":
        return 2
    return 0


def _insert_textbox_with_fit(
    *,
    page: fitz.Page,
    rect: fitz.Rect,
    text: str,
    font_size: float,
    font_name: str,
    color: tuple[float, float, float],
    align: Literal["left", "center", "right"],
    rotation: float,
    error_code: str,
    error_message: str,
) -> None:
    next_font_size = max(2.0, font_size)
    rotate = _normalize_text_rotation(rotation)

    for _ in range(8):
        kwargs = {
            "fontsize": next_font_size,
            "fontname": font_name,
            "color": color,
            "align": _alignment_value(align),
            "overlay": True,
        }
        if rotate is not None:
            kwargs["rotate"] = rotate

        overflow = page.insert_textbox(rect, text, **kwargs)
        if overflow >= -1:
            return
        next_font_size = max(2.0, next_font_size * 0.92)

    raise PdfProcessingError(code=error_code, user_message=error_message)


def _remove_text_region(page: fitz.Page, rect: fitz.Rect) -> None:
    fill = _sample_fill_color(page, rect)
    try:
        page.add_redact_annot(rect, fill=fill, cross_out=False)
        page.apply_redactions(
            images=_REDACT_IMAGE_NONE,
            graphics=_REDACT_GRAPHICS_NONE,
            text=_REDACT_TEXT_CHAR,
        )
    except Exception as exc:
        raise PdfProcessingError(
            code="editor_text_replace_redaction_failed",
            user_message="Existing page text could not be safely removed before replacement.",
        ) from exc


def _sample_fill_color(page: fitz.Page, rect: fitz.Rect) -> tuple[float, float, float]:
    try:
        clip = fitz.Rect(rect)
        clip.intersect(page.rect)
        if clip.is_empty:
            return (1.0, 1.0, 1.0)

        pix = page.get_pixmap(clip=clip, colorspace=fitz.csRGB, alpha=False)
        samples = pix.samples
        if not samples:
            return (1.0, 1.0, 1.0)

        pixel_count = max(1, len(samples) // 3)
        stride = max(1, pixel_count // 2500)
        red = 0
        green = 0
        blue = 0
        counted = 0

        for index in range(0, len(samples), 3 * stride):
          red += samples[index]
          green += samples[index + 1]
          blue += samples[index + 2]
          counted += 1

        if counted == 0:
            return (1.0, 1.0, 1.0)

        return (red / counted / 255.0, green / counted / 255.0, blue / counted / 255.0)
    except Exception:
        return (1.0, 1.0, 1.0)


def _normalize_text_rotation(rotation: float) -> int | None:
    normalized = int(round(rotation)) % 360
    if normalized in {0, 90, 180, 270}:
        return normalized
    return None


def _resolve_text_replace_style(
    page: fitz.Page,
    operation: TextReplaceOperation,
    source_rect: fitz.Rect,
) -> dict[str, object]:
    matched_span = _find_matching_text_span(page, operation.original_text, source_rect)

    font_name = operation.font_name
    font_size = operation.font_size
    color = hex_to_rgb(operation.color)

    if matched_span is not None:
        raw_font_name = str(matched_span.get("font") or matched_span.get("fontname") or "")
        if raw_font_name:
            font_name = _normalize_pdf_font_name(raw_font_name, fallback=operation.font_name)
        span_size = matched_span.get("size")
        if isinstance(span_size, (int, float)) and span_size > 0:
            font_size = float(span_size)
        span_color = matched_span.get("color")
        if isinstance(span_color, int):
            color = _pdf_color_to_rgb(span_color)

    return {
        "font_name": font_name,
        "font_size": font_size,
        "color": color,
        "align": operation.align,
        "rotation": operation.rotation,
    }


def _find_matching_text_span(
    page: fitz.Page,
    original_text: str,
    source_rect: fitz.Rect,
) -> dict[str, object] | None:
    wanted = " ".join(original_text.split())
    best_span: dict[str, object] | None = None
    best_score = 0.0

    raw = page.get_text("dict")
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = str(span.get("text") or "")
                normalized = " ".join(text.split())
                if not normalized:
                    continue
                span_rect = fitz.Rect(span.get("bbox", (0, 0, 0, 0)))
                overlap = source_rect & span_rect
                if overlap.is_empty:
                    continue
                overlap_area = overlap.get_area()
                text_bonus = 5.0 if normalized == wanted else 1.0 if wanted and wanted in normalized else 0.0
                score = overlap_area + text_bonus
                if score > best_score:
                    best_score = score
                    best_span = span

    return best_span


def _normalize_pdf_font_name(value: str, fallback: str = "helv") -> str:
    normalized = value.lower().replace("+", "-").replace("_", "-")
    compact = re.sub(r"[^a-z-]", "", normalized)
    if "cour" in compact:
        if "bold" in compact and ("italic" in compact or "oblique" in compact):
            return "courbi"
        if "bold" in compact:
            return "courb"
        if "italic" in compact or "oblique" in compact:
            return "couri"
        return "cour"
    if "tim" in compact or "times" in compact:
        if "bold" in compact and ("italic" in compact or "oblique" in compact):
            return "timbi"
        if "bold" in compact:
            return "timb"
        if "italic" in compact or "oblique" in compact:
            return "timi"
        return "timr"
    if "symb" in compact or "symbol" in compact:
        return "symb"
    if "zadb" in compact or "zapf" in compact:
        return "zadb"
    if "bold" in compact and ("italic" in compact or "oblique" in compact):
        return "helv-bold-italic"
    if "bold" in compact:
        return "helv-bold"
    if "italic" in compact or "oblique" in compact:
        return "helv-italic"
    return fallback if fallback in ALLOWED_FONT_NAMES else "helv"


def _pdf_color_to_rgb(value: int) -> tuple[float, float, float]:
    red = ((value >> 16) & 255) / 255.0
    green = ((value >> 8) & 255) / 255.0
    blue = (value & 255) / 255.0
    return (red, green, blue)


def _decode_image_data(image_data: str) -> bytes:
    raw_value = image_data.split(";base64,", 1)[1] if image_data.startswith("data:") else image_data
    try:
        return _base64.b64decode(raw_value, validate=True)
    except Exception as exc:
        raise PdfProcessingError(
            code="editor_invalid_image",
            user_message="The provided image data is not valid base64 content.",
        ) from exc


def _path_segments(path_data: str) -> list[tuple[float, float, float, float]]:
    tokens = _re.findall(r"[A-Za-z]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", path_data)
    segments: list[tuple[float, float, float, float]] = []
    command: str | None = None
    index = 0
    current_x = 0.0
    current_y = 0.0
    start_x = 0.0
    start_y = 0.0

    def read_number() -> float:
        nonlocal index
        if index >= len(tokens):
            raise PdfProcessingError(
                code="editor_invalid_draw_path",
                user_message="The drawing path ended before all coordinates were supplied.",
            )
        token = tokens[index]
        if len(token) == 1 and token.isalpha():
            raise PdfProcessingError(
                code="editor_invalid_draw_path",
                user_message="The drawing path is missing coordinates for one of its commands.",
            )
        index += 1
        return float(token)

    while index < len(tokens):
        token = tokens[index]
        if len(token) == 1 and token.isalpha():
            command = token
            index += 1
        elif command is None:
            raise PdfProcessingError(
                code="editor_invalid_draw_path",
                user_message="The drawing path must begin with a drawing command.",
            )

        assert command is not None
        normalized = command.upper()

        if normalized == "M":
            x = read_number()
            y = read_number()
            current_x, current_y = x, y
            start_x, start_y = x, y
            command = "L"
            continue

        if normalized == "L":
            x = read_number()
            y = read_number()
            segments.append((current_x, current_y, x, y))
            current_x, current_y = x, y
            continue

        if normalized == "H":
            x = read_number()
            segments.append((current_x, current_y, x, current_y))
            current_x = x
            continue

        if normalized == "V":
            y = read_number()
            segments.append((current_x, current_y, current_x, y))
            current_y = y
            continue

        if normalized == "C":
            read_number()
            read_number()
            read_number()
            read_number()
            x = read_number()
            y = read_number()
            segments.append((current_x, current_y, x, y))
            current_x, current_y = x, y
            continue

        if normalized == "Q":
            read_number()
            read_number()
            x = read_number()
            y = read_number()
            segments.append((current_x, current_y, x, y))
            current_x, current_y = x, y
            continue

        if normalized == "Z":
            segments.append((current_x, current_y, start_x, start_y))
            current_x, current_y = start_x, start_y
            command = None
            continue

        raise PdfProcessingError(
            code="editor_invalid_draw_path",
            user_message=f"The drawing path command '{command}' is not supported.",
        )

    return segments
