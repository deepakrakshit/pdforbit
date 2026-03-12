"""
compare.py — Enterprise-grade PDF Compare Processor
====================================================
KEY FEATURES:
  • Text-level diff (difflib word-by-word) as primary comparison mode
  • Annotated output PDFs with colored highlights (green=added, red=removed)
  • Visual pixel diff as secondary comparison mode
  • Combined mode: both text diff annotations + visual diff images
  • Memory-safe lazy page processing (never loads all pages at once)
  • Rich summary.txt: lists actual text changes per page
  • diff_mode: "text" | "visual" | "combined" (default: "combined")
  • Page count mismatch handling with clear per-document context
  • ZIP uses STORED compression (images are already compressed)
"""
from __future__ import annotations

import difflib
import io
import logging
import zipfile
from pathlib import Path

import fitz
from PIL import Image, ImageChops

from app.models.enums import ArtifactKind
from app.schemas.job import CompareJobRequest
from app.services.pdf.common import (
    BaseToolProcessor,
    GeneratedArtifact,
    PdfProcessingError,
    ProcessingResult,
    ProcessorContext,
    ZIP_CONTENT_TYPE,
    ensure_zip_output_filename,
)

log = logging.getLogger(__name__)

# Highlight colours (R, G, B) in fitz 0–1 float scale
_COLOR_ADDED = (0.0, 0.8, 0.2)     # green  — text present in right doc only
_COLOR_REMOVED = (0.9, 0.1, 0.1)   # red    — text present in left doc only
_COLOR_CHANGED = (0.9, 0.6, 0.0)   # orange — text changed between docs
_DIFF_DPI = 120                     # DPI for visual diff rendering


class ComparePdfProcessor(BaseToolProcessor):
    tool_id = "compare"

    def __init__(self, *, render_dpi: int) -> None:
        self._render_dpi = min(render_dpi, _DIFF_DPI)

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = CompareJobRequest.model_validate(context.payload)
        if len(context.inputs) != 2:
            raise PdfProcessingError(
                code="invalid_job_inputs",
                user_message="Compare requires exactly two uploaded PDFs.",
            )

        archive_filename = ensure_zip_output_filename(payload.output_filename)
        archive_path = context.workspace / archive_filename
        diff_mode: str = (getattr(payload, "diff_mode", None) or "combined").lower()

        different_pages = 0
        compared_pages = 0
        summary_lines: list[str] = []

        # Build annotated copies of both PDFs for text-mode output
        left_annotated_path = context.workspace / "left-annotated.pdf"
        right_annotated_path = context.workspace / "right-annotated.pdf"

        with (
            fitz.open(context.inputs[0].storage_path) as left_doc,
            fitz.open(context.inputs[1].storage_path) as right_doc,
            zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive,
        ):
            max_pages = max(left_doc.page_count, right_doc.page_count)

            for page_idx in range(max_pages):
                compared_pages += 1
                left_missing = page_idx >= left_doc.page_count
                right_missing = page_idx >= right_doc.page_count

                if left_missing or right_missing:
                    different_pages += 1
                    side = "Document 2" if left_missing else "Document 1"
                    summary_lines.append(f"Page {page_idx + 1}: only present in {side}.")
                    continue

                left_page = left_doc.load_page(page_idx)
                right_page = right_doc.load_page(page_idx)

                # --- Text diff ---
                left_text = _extract_page_text(left_page)
                right_text = _extract_page_text(right_page)
                text_changes = _compute_text_diff(left_text, right_text)

                # --- Visual diff (memory-safe: one page at a time) ---
                visual_diff_found = False
                if diff_mode in ("visual", "combined"):
                    left_img = _render_page(left_page, dpi=self._render_dpi)
                    right_img = _render_page(right_page, dpi=self._render_dpi)
                    left_img, right_img = _align_images(left_img, right_img)
                    diff_img = ImageChops.difference(left_img, right_img)
                    visual_diff_found = diff_img.getbbox() is not None

                    if visual_diff_found:
                        _write_image_to_archive(archive, f"page-{page_idx + 1:03d}-left.jpg", left_img)
                        _write_image_to_archive(archive, f"page-{page_idx + 1:03d}-right.jpg", right_img)
                        _write_image_to_archive(archive, f"page-{page_idx + 1:03d}-diff.png", diff_img)

                    # Free memory immediately
                    del left_img, right_img, diff_img

                # --- Apply text diff annotations to pages ---
                if diff_mode in ("text", "combined") and text_changes:
                    _annotate_diff(left_page, right_page, changes=text_changes)

                has_diff = bool(text_changes) or visual_diff_found
                if has_diff:
                    different_pages += 1
                    change_summary = _build_change_summary(page_idx + 1, text_changes)
                    summary_lines.append(change_summary)
                    log.debug("compare: page %d has differences", page_idx + 1)
                else:
                    summary_lines.append(f"Page {page_idx + 1}: identical.")

            # Save annotated PDFs to ZIP
            if diff_mode in ("text", "combined"):
                _save_annotated_pdf(left_doc, left_annotated_path)
                _save_annotated_pdf(right_doc, right_annotated_path)
                if left_annotated_path.exists():
                    archive.write(left_annotated_path, arcname="document-1-annotated.pdf")
                if right_annotated_path.exists():
                    archive.write(right_annotated_path, arcname="document-2-annotated.pdf")

            # Write comprehensive summary
            header = (
                f"PdfORBIT Comparison Report\n"
                f"Document 1: {context.inputs[0].original_filename}\n"
                f"Document 2: {context.inputs[1].original_filename}\n"
                f"Pages compared: {compared_pages} | Pages with differences: {different_pages}\n"
                f"{'=' * 60}\n\n"
            )
            archive.writestr("summary.txt", header + "\n".join(summary_lines))

        # Cleanup annotated temp files
        for p in (left_annotated_path, right_annotated_path):
            p.unlink(missing_ok=True)

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=archive_path,
                filename=archive_filename,
                content_type=ZIP_CONTENT_TYPE,
                kind=ArtifactKind.ARCHIVE,
                metadata={
                    "different_pages": different_pages,
                    "pages_processed": compared_pages,
                    "diff_mode": diff_mode,
                },
            ),
            completion_message=(
                f"Comparison complete: {different_pages}/{compared_pages} pages have differences."
            ),
        )


# ---------------------------------------------------------------------------
# Text diff helpers
# ---------------------------------------------------------------------------

def _extract_page_text(page: fitz.Page) -> list[str]:
    """Returns a list of words from the page for diff purposes."""
    raw = page.get_text("text", flags=0)
    return raw.split()


def _compute_text_diff(
    left_words: list[str],
    right_words: list[str],
) -> list[tuple[str, str, str]]:
    """
    Returns a list of (tag, left_text, right_text) tuples.
    tag is one of: 'equal', 'replace', 'delete', 'insert'
    """
    matcher = difflib.SequenceMatcher(None, left_words, right_words, autojunk=False)
    changes: list[tuple[str, str, str]] = []
    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == "equal":
            continue
        left_chunk = " ".join(left_words[i1:i2])
        right_chunk = " ".join(right_words[j1:j2])
        changes.append((opcode, left_chunk, right_chunk))
    return changes


def _annotate_diff(
    left_page: fitz.Page,
    right_page: fitz.Page,
    changes: list[tuple[str, str, str]],
) -> None:
    """
    Searches for changed text in both pages and adds highlight annotations.
    Green = addition (right), Red = removal (left), Orange = replacement.
    """
    for tag, left_text, right_text in changes[:50]:  # cap to 50 changes per page
        if tag in ("delete", "replace") and left_text.strip():
            _highlight_text_on_page(left_page, left_text, color=_COLOR_REMOVED)
        if tag in ("insert", "replace") and right_text.strip():
            _highlight_text_on_page(right_page, right_text, color=_COLOR_ADDED)


def _highlight_text_on_page(page: fitz.Page, text: str, color: tuple) -> None:
    """Searches for text on a page and highlights all occurrences."""
    try:
        # Search for up to first 6 words for robustness (long phrases may not match)
        search_phrase = " ".join(text.split()[:6])
        if not search_phrase:
            return
        rects = page.search_for(search_phrase, quads=False)
        for rect in rects[:10]:
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=color)
            annot.update()
    except Exception:
        pass


def _build_change_summary(page_num: int, changes: list[tuple[str, str, str]]) -> str:
    """Builds a human-readable summary line for a page's text changes."""
    if not changes:
        return f"Page {page_num}: visual differences detected (no text changes)."
    parts = [f"Page {page_num}: {len(changes)} text change(s):"]
    for tag, left_text, right_text in changes[:5]:
        left_preview = left_text[:40].replace("\n", " ")
        right_preview = right_text[:40].replace("\n", " ")
        if tag == "delete":
            parts.append(f"  - Removed: '{left_preview}'")
        elif tag == "insert":
            parts.append(f"  + Added:   '{right_preview}'")
        elif tag == "replace":
            parts.append(f"  ~ Changed: '{left_preview}' → '{right_preview}'")
    if len(changes) > 5:
        parts.append(f"  ... and {len(changes) - 5} more change(s).")
    return "\n".join(parts)


def _save_annotated_pdf(doc: fitz.Document, output_path: Path) -> None:
    """Saves a fitz document with annotations to a file."""
    try:
        doc.save(str(output_path), garbage=3, deflate=True)
    except Exception as exc:
        log.debug("compare: could not save annotated PDF: %s", exc)


# ---------------------------------------------------------------------------
# Visual diff helpers (memory-safe)
# ---------------------------------------------------------------------------

def _render_page(page: fitz.Page, *, dpi: int) -> Image.Image:
    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")


def _align_images(left: Image.Image, right: Image.Image) -> tuple[Image.Image, Image.Image]:
    w = max(left.width, right.width)
    h = max(left.height, right.height)
    if left.size == (w, h) and right.size == (w, h):
        return left, right
    canvas_l = Image.new("RGB", (w, h), "white")
    canvas_r = Image.new("RGB", (w, h), "white")
    canvas_l.paste(left, (0, 0))
    canvas_r.paste(right, (0, 0))
    return canvas_l, canvas_r


def _write_image_to_archive(archive: zipfile.ZipFile, name: str, image: Image.Image) -> None:
    buf = io.BytesIO()
    if name.endswith(".png"):
        image.save(buf, format="PNG", optimize=True)
    else:
        image.convert("RGB").save(buf, format="JPEG", quality=80)
    archive.writestr(name, buf.getvalue())