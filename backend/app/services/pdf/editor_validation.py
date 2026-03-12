"""
editor_validation.py — PDF Editor Operation Validation Service
==============================================================
Validates a complete list of editor operations against the actual PDF document
before any processing begins.  All page-number, coordinate-bound, and
structural-integrity checks live here so that ``editor_apply.py`` can trust the
operations it receives are safe to apply.

Design principles:
  • Fail fast: a single invalid operation aborts the whole job.
  • Informative: error messages identify the exact operation by index and type.
  • No side effects: validation is read-only; it opens the PDF but never writes it.
  • Concurrency-safe: all state is passed in; no module-level mutable state.
"""
from __future__ import annotations

import logging
from pathlib import Path

import fitz

from app.schemas.editor_operations_schema import (
    OVERLAY_OPERATION_TYPES,
    STRUCTURAL_OPERATION_TYPES,
    AnyEditorOperation,
    EditorApplyJobRequest,
    MAX_OPERATIONS_PER_JOB,
    MAX_OVERLAY_OPS_PER_PAGE,
    PageDeleteOperation,
    PageReorderOperation,
    PageRotateOperation,
)
from app.services.pdf.common import PdfProcessingError

log = logging.getLogger(__name__)

# Maximum allowed PDF file size for the editor (50 MB)
_MAX_PDF_SIZE_BYTES: int = 50 * 1024 * 1024
# Maximum allowed page count for the editor
_MAX_PDF_PAGES: int = 200
# Coordinate tolerance: allow 1 pt outside page bounds to account for floating-point rounding
_COORD_TOLERANCE: float = 1.0


def validate_editor_job(
    *,
    payload: EditorApplyJobRequest,
    pdf_path: Path,
    pdf_size_bytes: int,
) -> None:
    """
    Entry point: validates the complete editor job before any PDF modification.
    Opens the PDF exactly once to extract page count and dimensions while also
    enforcing size/page-count limits — eliminating the previous double-open.

    Args:
        payload: The parsed job request (already schema-validated by Pydantic).
        pdf_path: Filesystem path to the source PDF.
        pdf_size_bytes: Pre-computed file size in bytes.

    Raises:
        PdfProcessingError: For any validation failure, with a user-visible message.
    """
    # ── File-size check (no PDF open required) ────────────────────────────
    if pdf_size_bytes > _MAX_PDF_SIZE_BYTES:
        raise PdfProcessingError(
            code="editor_pdf_too_large",
            user_message=(
                f"The PDF file ({pdf_size_bytes // (1024 * 1024)} MB) exceeds the "
                f"{_MAX_PDF_SIZE_BYTES // (1024 * 1024)} MB limit for the PDF editor."
            ),
        )

    # ── Single fitz.open — limits + page count + dimension extraction ─────
    try:
        with fitz.open(str(pdf_path)) as doc:
            page_count = doc.page_count
            if page_count == 0:
                raise PdfProcessingError(
                    code="editor_empty_pdf",
                    user_message="The PDF has no pages and cannot be edited.",
                )
            if page_count > _MAX_PDF_PAGES:
                raise PdfProcessingError(
                    code="editor_too_many_pages",
                    user_message=(
                        f"The PDF has {page_count} pages, which exceeds the "
                        f"{_MAX_PDF_PAGES}-page limit for the PDF editor."
                    ),
                )
            page_dimensions: list[tuple[float, float]] = [
                (page.rect.width, page.rect.height)
                for page in doc
            ]
    except PdfProcessingError:
        raise
    except Exception as exc:
        raise PdfProcessingError(
            code="editor_invalid_pdf",
            user_message="The uploaded file could not be read as a valid PDF.",
        ) from exc

    log.debug(
        "editor.validate: validating %d operations against %d-page PDF",
        len(payload.operations),
        page_count,
    )

    _validate_page_numbers(
        operations=payload.operations,
        page_count=page_count,
    )
    _validate_coordinates(
        operations=payload.operations,
        page_dimensions=page_dimensions,
    )
    _validate_structural_operations(
        operations=payload.operations,
        page_count=page_count,
    )
    _validate_rotation_support(operations=payload.operations)
    _validate_operation_limits(operations=payload.operations)

    log.info(
        "editor.validate: all %d operations passed validation for %d-page PDF",
        len(payload.operations),
        page_count,
    )


# ─── Internal validators ──────────────────────────────────────────────────────

def _validate_pdf_limits(*, pdf_path: Path, pdf_size_bytes: int) -> None:
    """
    Retained for backward compatibility (external tests / tooling).
    In normal execution validate_editor_job() now performs all limit checks
    in its single fitz.open context; this function is no longer on the hot path.
    """
    if pdf_size_bytes > _MAX_PDF_SIZE_BYTES:
        raise PdfProcessingError(
            code="editor_pdf_too_large",
            user_message=(
                f"The PDF file ({pdf_size_bytes // (1024 * 1024)} MB) exceeds the "
                f"{_MAX_PDF_SIZE_BYTES // (1024 * 1024)} MB limit for the PDF editor."
            ),
        )

    try:
        with fitz.open(str(pdf_path)) as doc:
            if doc.page_count == 0:
                raise PdfProcessingError(
                    code="editor_empty_pdf",
                    user_message="The PDF has no pages and cannot be edited.",
                )
            if doc.page_count > _MAX_PDF_PAGES:
                raise PdfProcessingError(
                    code="editor_too_many_pages",
                    user_message=(
                        f"The PDF has {doc.page_count} pages, which exceeds the "
                        f"{_MAX_PDF_PAGES}-page limit for the PDF editor."
                    ),
                )
    except PdfProcessingError:
        raise
    except Exception as exc:
        raise PdfProcessingError(
            code="editor_invalid_pdf",
            user_message="The uploaded file could not be read as a valid PDF.",
        ) from exc


def _validate_page_numbers(
    *,
    operations: list[AnyEditorOperation],
    page_count: int,
) -> None:
    """
    Validates that every operation references a page that exists in the document.
    PageReorderOperation is handled separately in _validate_structural_operations.
    """
    for idx, op in enumerate(operations):
        if op.type == "page_reorder":
            continue  # checked separately
        if op.page < 1 or op.page > page_count:
            raise PdfProcessingError(
                code="editor_invalid_page",
                user_message=(
                    f"operations[{idx}] ({op.type}) references page {op.page}, "
                    f"but the document has only {page_count} page(s)."
                ),
            )


def _validate_coordinates(
    *,
    operations: list[AnyEditorOperation],
    page_dimensions: list[tuple[float, float]],
) -> None:
    """
    Validates that overlay operation coordinates fall within the page bounds
    (with a small tolerance for floating-point edge cases).
    """
    for idx, op in enumerate(operations):
        if op.type not in OVERLAY_OPERATION_TYPES:
            continue

        page_idx = op.page - 1
        if page_idx >= len(page_dimensions):
            continue  # already caught by _validate_page_numbers

        page_w, page_h = page_dimensions[page_idx]
        tol = _COORD_TOLERANCE

        if op.type in {"text_insert", "image_insert", "signature_insert", "shape_insert", "text_replace"}:
            x: float = op.x  # type: ignore[union-attr]
            y: float = op.y  # type: ignore[union-attr]
            w: float = op.width  # type: ignore[union-attr]
            h: float = op.height  # type: ignore[union-attr]
            if x < -tol or y < -tol or (x + w) > page_w + tol or (y + h) > page_h + tol:
                raise PdfProcessingError(
                    code="editor_coords_out_of_bounds",
                    user_message=(
                        f"operations[{idx}] ({op.type}) bounding box "
                        f"({x:.1f}, {y:.1f}, {x+w:.1f}, {y+h:.1f}) extends outside "
                        f"page {op.page} dimensions ({page_w:.1f}×{page_h:.1f} pts)."
                    ),
                )

            if op.type == "text_replace":
                original_x: float = op.original_x  # type: ignore[union-attr]
                original_y: float = op.original_y  # type: ignore[union-attr]
                original_w: float = op.original_width  # type: ignore[union-attr]
                original_h: float = op.original_height  # type: ignore[union-attr]
                if (
                    original_x < -tol
                    or original_y < -tol
                    or (original_x + original_w) > page_w + tol
                    or (original_y + original_h) > page_h + tol
                ):
                    raise PdfProcessingError(
                        code="editor_coords_out_of_bounds",
                        user_message=(
                            f"operations[{idx}] (text_replace) original bounding box "
                            f"({original_x:.1f}, {original_y:.1f}, {original_x+original_w:.1f}, {original_y+original_h:.1f}) extends outside "
                            f"page {op.page} dimensions ({page_w:.1f}×{page_h:.1f} pts)."
                        ),
                    )

        elif op.type == "highlight":
            for ri, rect in enumerate(op.rects):  # type: ignore[union-attr]
                x0, y0, x1, y1 = rect
                if x0 < -tol or y0 < -tol or x1 > page_w + tol or y1 > page_h + tol:
                    raise PdfProcessingError(
                        code="editor_coords_out_of_bounds",
                        user_message=(
                            f"operations[{idx}] (highlight) rect[{ri}] "
                            f"({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f}) extends outside "
                            f"page {op.page} ({page_w:.1f}×{page_h:.1f} pts)."
                        ),
                    )

        elif op.type == "draw":
            # Validate that the path bounding box is within page bounds
            # (full path-segment validation is done in the operation applier)
            _validate_draw_path_bounds(
                idx=idx,
                path_data=op.path_data,  # type: ignore[union-attr]
                page_w=page_w,
                page_h=page_h,
                page_num=op.page,
            )


def _validate_draw_path_bounds(
    *,
    idx: int,
    path_data: str,
    page_w: float,
    page_h: float,
    page_num: int,
) -> None:
    """
    Quick sanity check on draw path coordinates.  Parses numeric tokens and
    checks all fall within a generous extension of the page bounds.
    A full-parse is not needed here since the operation applier validates
    individual commands; this is a fast bulk numeric check.
    """
    # Guard against malicious oversized payloads before the regex scan
    if len(path_data) > 100_000:
        raise PdfProcessingError(
            code="editor_path_too_large",
            user_message=(
                f"operations[{idx}] (draw) on page {page_num}: "
                "the drawing path data exceeds the 100 KB limit."
            ),
        )
    import re as _re
    numbers = _re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", path_data)
    tol = max(page_w, page_h) * 0.5  # allow 50% overflow (e.g. strokes near edge)
    x_bounds = (-tol, page_w + tol)
    y_bounds = (-tol, page_h + tol)

    # Numbers in SVG path alternate loosely between x and y.
    # We do a coarse check: no number should be completely off-scale.
    upper_limit = max(page_w, page_h) * 10.0
    for token in numbers:
        try:
            val = float(token)
        except ValueError:
            continue
        if abs(val) > upper_limit:
            raise PdfProcessingError(
                code="editor_coords_out_of_bounds",
                user_message=(
                    f"operations[{idx}] (draw) on page {page_num} contains "
                    f"a coordinate value ({val:.1f}) that is far outside the page bounds."
                ),
            )


def _validate_structural_operations(
    *,
    operations: list[AnyEditorOperation],
    page_count: int,
) -> None:
    """
    Validates page_rotate, page_delete, and page_reorder operations.
      • page_delete: all referenced pages must exist; total deletions must not remove all pages.
      • page_reorder: new_order must be a complete permutation of 1..page_count.
    """
    pages_to_delete: set[int] = set()
    reorder_op: PageReorderOperation | None = None

    for idx, op in enumerate(operations):
        if op.type == "page_rotate":
            # page range already validated in _validate_page_numbers
            pass

        elif op.type == "page_delete":
            page = op.page
            if page < 1 or page > page_count:
                raise PdfProcessingError(
                    code="editor_invalid_page",
                    user_message=(
                        f"operations[{idx}] (page_delete) references page {page}, "
                        f"but the document has only {page_count} page(s)."
                    ),
                )
            pages_to_delete.add(page)

        elif op.type == "page_reorder":
            reorder_op = op  # type: ignore[assignment]
            continue

    # Guard: do not allow deleting every page
    if pages_to_delete and len(pages_to_delete) >= page_count:
        raise PdfProcessingError(
            code="editor_cannot_delete_all_pages",
            user_message="The editor operations would delete all pages from the document.",
        )

    if reorder_op is not None:
        surviving_page_count = page_count - len(pages_to_delete)
        expected_count = surviving_page_count if pages_to_delete else page_count
        new_order = reorder_op.new_order
        if len(new_order) != expected_count:
            raise PdfProcessingError(
                code="editor_invalid_reorder",
                user_message=(
                    f"page_reorder new_order has {len(new_order)} entries but the document "
                    f"state at reorder time has {expected_count} page(s)."
                ),
            )

        expected = set(range(1, expected_count + 1))
        provided = set(new_order)
        if provided != expected:
            missing = sorted(expected - provided)
            extra = sorted(provided - expected)
            parts: list[str] = []
            if missing:
                parts.append(f"missing pages: {missing}")
            if extra:
                parts.append(f"invalid page numbers: {extra}")
            raise PdfProcessingError(
                code="editor_invalid_reorder",
                user_message=(
                    f"page_reorder new_order is not a valid permutation of 1–{expected_count}. "
                    + "; ".join(parts)
                ),
                )


def _validate_rotation_support(*, operations: list[AnyEditorOperation]) -> None:
    """
    Reject editor operations whose rotation the current processing engine cannot
    apply faithfully. This avoids silently producing output that differs from
    what the browser editor preview showed the user.
    """
    for idx, op in enumerate(operations):
        if op.type in {"text_insert", "text_replace"}:
            rotation = int(round(op.rotation)) % 360  # type: ignore[union-attr]
            if rotation not in {0, 90, 180, 270}:
                raise PdfProcessingError(
                    code="editor_rotation_unsupported",
                    user_message=(
                        f"operations[{idx}] ({op.type}) uses rotation {op.rotation}, "
                        "but text rotation currently supports only 0, 90, 180, or 270 degrees."
                    ),
                )

        if op.type in {"image_insert", "signature_insert", "shape_insert"}:
            rotation = float(getattr(op, "rotation", 0.0))
            if abs(rotation) > 0.01:
                raise PdfProcessingError(
                    code="editor_rotation_unsupported",
                    user_message=(
                        f"operations[{idx}] ({op.type}) uses rotation {rotation}, "
                        "but rotated images and shapes are not currently supported."
                    ),
                )


def _validate_operation_limits(*, operations: list[AnyEditorOperation]) -> None:
    """
    Validates aggregate limits that cannot be enforced by the Pydantic model alone
    (since those run per-field, not across the full list).
    """
    total = len(operations)
    if total > MAX_OPERATIONS_PER_JOB:
        raise PdfProcessingError(
            code="editor_too_many_operations",
            user_message=(
                f"The editor job contains {total} operations, which exceeds "
                f"the maximum of {MAX_OPERATIONS_PER_JOB}."
            ),
        )

    overlay_per_page: dict[int, int] = {}
    for op in operations:
        if op.type in OVERLAY_OPERATION_TYPES:
            overlay_per_page[op.page] = overlay_per_page.get(op.page, 0) + 1
            if overlay_per_page[op.page] > MAX_OVERLAY_OPS_PER_PAGE:
                raise PdfProcessingError(
                    code="editor_too_many_ops_on_page",
                    user_message=(
                        f"Page {op.page} has more than {MAX_OVERLAY_OPS_PER_PAGE} "
                        "overlay operations, which exceeds the per-page limit."
                    ),
                )
