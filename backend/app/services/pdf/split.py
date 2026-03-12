"""
split.py — Enterprise-grade PDF Split Processor
================================================
KEY FEATURES:
  • by_range mode      — comma-separated page ranges  (e.g. "1-3,5,8-10")
  • every_n_pages mode — fixed-size chunks
  • by_bookmark mode   — each top-level bookmark becomes its own PDF
                         with a filename derived from the bookmark title
  • ZIP_STORED for PDFs (PDFs are already compressed; deflating wastes CPU)
  • Single-range shortcut: returns a direct PDF instead of a 1-file ZIP
  • Per-part bookmark preservation (bookmarks pointing into the split range
    are included in each part with adjusted page numbers)
  • Metadata written to each part PDF
"""
from __future__ import annotations

import logging
import re
import zipfile
from pathlib import Path

import fitz
import pikepdf

from app.models.enums import ArtifactKind
from app.schemas.job import SplitJobRequest
from app.services.pdf.common import (
    BaseToolProcessor,
    GeneratedArtifact,
    PDF_CONTENT_TYPE,
    PdfProcessingError,
    ProcessingResult,
    ProcessorContext,
    ZIP_CONTENT_TYPE,
    chunk_page_numbers,
    ensure_pdf_output_filename,
    ensure_zip_output_filename,
    open_pdf,
    parse_split_ranges,
)

log = logging.getLogger(__name__)

# Maximum characters allowed in a bookmark-derived filename
_BOOKMARK_FILENAME_MAX = 80
# Regex for characters unsafe in filenames
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class SplitPdfProcessor(BaseToolProcessor):
    tool_id = "split"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = SplitJobRequest.model_validate(context.payload)
        source = context.require_single_input()
        prefix = Path(payload.output_prefix or Path(source.original_filename).stem).stem or "split"

        with open_pdf(source.storage_path) as source_pdf:
            page_count = len(source_pdf.pages)

            if payload.mode == "by_bookmark":
                groups, group_names = _groups_from_bookmarks(
                    source_pdf,
                    source_path=source.storage_path,
                    page_count=page_count,
                )
            elif payload.mode == "by_range":
                groups = parse_split_ranges(payload.ranges or "", page_count=page_count)
                group_names = [f"{prefix}-part-{i:02d}" for i in range(1, len(groups) + 1)]
            else:  # every_n_pages
                groups = chunk_page_numbers(page_count, payload.every_n_pages or 1)
                group_names = [f"{prefix}-part-{i:02d}" for i in range(1, len(groups) + 1)]

            if not groups:
                raise PdfProcessingError(
                    code="split_no_groups",
                    user_message="No page groups could be determined from the split parameters.",
                )

            split_dir = context.workspace / "split"
            split_dir.mkdir(parents=True, exist_ok=True)
            part_paths: list[Path] = []

            for group_pages, group_name in zip(groups, group_names):
                part_filename = ensure_pdf_output_filename(f"{group_name}.pdf")
                part_path = split_dir / part_filename
                _write_part(
                    source_pdf=source_pdf,
                    page_numbers=group_pages,
                    output_path=part_path,
                    title=group_name,
                )
                part_paths.append(part_path)
                log.debug("split: wrote part '%s' (%d pages)", part_filename, len(group_pages))

        # If only one part was produced, return it directly as a PDF
        if len(part_paths) == 1:
            final_path = context.workspace / ensure_pdf_output_filename(f"{prefix}-split.pdf")
            part_paths[0].replace(final_path)
            return ProcessingResult(
                artifact=GeneratedArtifact(
                    local_path=final_path,
                    filename=final_path.name,
                    content_type=PDF_CONTENT_TYPE,
                    kind=ArtifactKind.RESULT,
                    metadata={"parts_count": 1, "pages_processed": page_count},
                ),
                completion_message="Split PDF created successfully.",
            )

        # Multiple parts → ZIP archive. Use STORED because PDFs are already compressed.
        archive_filename = ensure_zip_output_filename(f"{prefix}-split.zip")
        archive_path = context.workspace / archive_filename
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
            for part_path in part_paths:
                archive.write(part_path, arcname=part_path.name)

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=archive_path,
                filename=archive_filename,
                content_type=ZIP_CONTENT_TYPE,
                kind=ArtifactKind.ARCHIVE,
                metadata={"parts_count": len(part_paths), "pages_processed": page_count},
            ),
            completion_message=f"Split {len(part_paths)} parts created successfully.",
        )


# ---------------------------------------------------------------------------
# Bookmark-based grouping
# ---------------------------------------------------------------------------

def _groups_from_bookmarks(
    pdf: pikepdf.Pdf,
    *,
    source_path: Path,
    page_count: int,
) -> tuple[list[list[int]], list[str]]:
    """
    Reads the top-level outline and maps each entry to a 1-indexed page range.
    Returns (groups, names) where groups[i] is the list of 1-indexed page numbers
    for the i-th bookmark and names[i] is the sanitised filename stem.
    """
    try:
        with pdf.open_outline() as outline:
            items = outline.root
    except Exception:
        raise PdfProcessingError(
            code="split_no_bookmarks",
            user_message="This PDF has no bookmarks. Use 'by_range' or 'every_n_pages' mode instead.",
        )

    if not items:
        raise PdfProcessingError(
            code="split_no_bookmarks",
            user_message="This PDF has no bookmarks. Use 'by_range' or 'every_n_pages' mode instead.",
        )

    # Resolve each bookmark to a 0-indexed page number
    resolved: list[tuple[str, int]] = []  # (title, 0-based page index)
    for item in items:
        page_idx = _resolve_bookmark_page(item, pdf=pdf)
        if page_idx is not None and 0 <= page_idx < page_count:
            resolved.append((item.title or f"Section-{len(resolved)+1}", page_idx))

    if not resolved:
        resolved = _resolve_bookmarks_with_fitz(source_path)

    if not resolved:
        raise PdfProcessingError(
            code="split_no_bookmarks",
            user_message="Could not resolve any bookmark destinations. Use 'by_range' mode instead.",
        )

    # Sort by page index (bookmarks may not be in order)
    resolved.sort(key=lambda x: x[1])

    # Build page ranges: bookmark[i] owns pages from its page to bookmark[i+1].page - 1
    groups: list[list[int]] = []
    names: list[str] = []
    for idx, (title, start_idx) in enumerate(resolved):
        end_idx = resolved[idx + 1][1] - 1 if idx + 1 < len(resolved) else page_count - 1
        pages_1indexed = list(range(start_idx + 1, end_idx + 2))
        if pages_1indexed:
            groups.append(pages_1indexed)
            names.append(_sanitize_bookmark_name(title, index=idx + 1))

    if not groups:
        raise PdfProcessingError(
            code="split_no_bookmarks",
            user_message="Bookmark ranges produced no pages. Use 'by_range' mode instead.",
        )

    return groups, names


def _resolve_bookmarks_with_fitz(source_path: Path) -> list[tuple[str, int]]:
    resolved: list[tuple[str, int]] = []
    try:
        with fitz.open(source_path) as document:
            for level, title, page in document.get_toc(simple=True):
                if level != 1:
                    continue
                resolved.append((title or f"Section-{len(resolved) + 1}", max(page - 1, 0)))
    except Exception:
        log.debug("split: fitz bookmark fallback failed", exc_info=True)
    return resolved


def _resolve_bookmark_page(item: pikepdf.OutlineItem, *, pdf: pikepdf.Pdf) -> int | None:
    """Returns 0-based page index for a bookmark item, or None if unresolvable."""
    try:
        dest = item.destination
        if isinstance(dest, list) and dest:
            dest_page = dest[0]
            if isinstance(dest_page, int):
                return dest_page
            try:
                return pdf.pages.index(dest_page)
            except Exception:
                pass
        if isinstance(dest, int):
            return dest
    except Exception:
        pass
    return None


def _sanitize_bookmark_name(title: str, *, index: int) -> str:
    """Produces a filesystem-safe filename stem from a bookmark title."""
    safe = _UNSAFE_FILENAME_CHARS.sub("-", title).strip("-. ")
    safe = re.sub(r"-{2,}", "-", safe)[:_BOOKMARK_FILENAME_MAX].strip("-. ") or f"section-{index:02d}"
    return safe


# ---------------------------------------------------------------------------
# Part PDF writer with bookmark preservation
# ---------------------------------------------------------------------------

def _write_part(
    *,
    source_pdf: pikepdf.Pdf,
    page_numbers: list[int],
    output_path: Path,
    title: str,
) -> None:
    """
    Writes a subset of source_pdf pages to output_path, preserving any
    bookmarks that point into the selected page range (with adjusted offsets).
    """
    page_set = set(page_numbers)
    # Build a mapping: old 1-indexed page number → new 0-indexed position
    old_to_new: dict[int, int] = {old: new for new, old in enumerate(page_numbers)}

    part_pdf = pikepdf.Pdf.new()
    for page_number in page_numbers:
        part_pdf.pages.append(source_pdf.pages[page_number - 1])

    # Copy bookmarks that reference pages within this part
    try:
        with source_pdf.open_outline() as src_outline, part_pdf.open_outline() as part_outline:
            for item in src_outline.root:
                page_idx = _resolve_bookmark_page(item, pdf=source_pdf)
                if page_idx is None:
                    continue
                old_1indexed = page_idx + 1
                if old_1indexed not in page_set:
                    continue
                new_0indexed = old_to_new[old_1indexed]
                cloned = pikepdf.OutlineItem(
                    item.title or title,
                    page_location=pikepdf.PageLocation.FitH,
                    destination=new_0indexed,
                )
                part_outline.root.append(cloned)
    except Exception:
        log.debug("split: could not copy bookmarks to part '%s'", title, exc_info=True)

    # Write metadata
    with part_pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
        meta["dc:title"] = title
        meta["xmp:CreatorTool"] = "PdfORBIT"

    part_pdf.save(
        output_path,
        compress_streams=True,
        object_stream_mode=pikepdf.ObjectStreamMode.generate,
    )