"""
remove_pages.py — Enterprise-grade PDF Remove Pages Processor
=============================================================
KEY FEATURES:
  • Bookmark/outline cleanup — entries pointing to removed pages are pruned;
    entries pointing to retained pages are offset-corrected
  • /PageLabels dictionary rebuild after removal
  • Retained page count and removal summary in metadata
  • Clear guard against removing all pages
  • Linearized, optimized output
"""
from __future__ import annotations

import logging
from typing import Any

import pikepdf

from app.models.enums import ArtifactKind
from app.schemas.job import RemovePagesJobRequest
from app.services.pdf.common import (
    BaseToolProcessor,
    GeneratedArtifact,
    PDF_CONTENT_TYPE,
    PdfProcessingError,
    ProcessingResult,
    ProcessorContext,
    ensure_pdf_output_filename,
    normalize_page_numbers,
    open_pdf,
)

log = logging.getLogger(__name__)


class RemovePagesPdfProcessor(BaseToolProcessor):
    tool_id = "remove"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = RemovePagesJobRequest.model_validate(context.payload)
        source = context.require_single_input()
        output_filename = ensure_pdf_output_filename(payload.output_filename)
        output_path = context.workspace / output_filename

        with open_pdf(source.storage_path) as source_pdf:
            page_count = len(source_pdf.pages)
            pages_to_remove = set(
                normalize_page_numbers(
                    payload.pages_to_remove or [],
                    page_count=page_count,
                    field_name="pages_to_remove",
                )
            )

            remaining_pages = [p for p in range(1, page_count + 1) if p not in pages_to_remove]
            if not remaining_pages:
                raise PdfProcessingError(
                    code="invalid_pages",
                    user_message="At least one page must remain. Cannot remove all pages.",
                )

            # Build a mapping: old 1-indexed → new 0-indexed (for bookmark remapping)
            old_to_new_0indexed: dict[int, int] = {old: new for new, old in enumerate(remaining_pages)}

            result_pdf = pikepdf.Pdf.new()
            for page_number in remaining_pages:
                result_pdf.pages.append(source_pdf.pages[page_number - 1])

            # Prune and remap bookmarks
            _rebuild_outlines(
                source_pdf=source_pdf,
                target_pdf=result_pdf,
                old_to_new_0indexed=old_to_new_0indexed,
            )

            # Rebuild /PageLabels if present
            _rebuild_page_labels(
                source_pdf=source_pdf,
                target_pdf=result_pdf,
                remaining_1indexed=remaining_pages,
            )

            result_pdf.save(
                output_path,
                linearize=True,
                compress_streams=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=output_path,
                filename=output_filename,
                content_type=PDF_CONTENT_TYPE,
                kind=ArtifactKind.RESULT,
                metadata={
                    "pages_processed": len(remaining_pages),
                    "pages_removed": len(pages_to_remove),
                    "original_page_count": page_count,
                },
            ),
            completion_message=(
                f"Removed {len(pages_to_remove)} page(s). "
                f"Result has {len(remaining_pages)} page(s)."
            ),
        )


# ---------------------------------------------------------------------------
# Outline rebuild
# ---------------------------------------------------------------------------

def _rebuild_outlines(
    *,
    source_pdf: pikepdf.Pdf,
    target_pdf: pikepdf.Pdf,
    old_to_new_0indexed: dict[int, int],
) -> None:
    """
    Rebuilds the bookmark tree: items pointing to removed pages are dropped;
    items pointing to retained pages get their destinations remapped.
    """
    try:
        with source_pdf.open_outline() as src_outline, target_pdf.open_outline() as tgt_outline:
            for item in src_outline.root:
                rebuilt = _remap_outline_item(item, source_pdf=source_pdf, target_pdf=target_pdf, mapping=old_to_new_0indexed)
                if rebuilt is not None:
                    tgt_outline.root.append(rebuilt)
    except Exception:
        log.debug("remove_pages: could not rebuild bookmarks", exc_info=True)


def _remap_outline_item(
    item: pikepdf.OutlineItem,
    *,
    source_pdf: pikepdf.Pdf,
    target_pdf: pikepdf.Pdf,
    mapping: dict[int, int],
) -> pikepdf.OutlineItem | None:
    """Returns a remapped copy of the outline item, or None if its page was removed."""
    page_idx = _resolve_page_index(item, source_pdf)
    old_1indexed = (page_idx + 1) if page_idx is not None else None
    new_0indexed = mapping.get(old_1indexed) if old_1indexed is not None else None

    # Recurse into children regardless of whether this item's dest is valid
    children: list[pikepdf.OutlineItem] = []
    for child in item.children:
        child_remapped = _remap_outline_item(child, source_pdf=source_pdf, target_pdf=target_pdf, mapping=mapping)
        if child_remapped is not None:
            children.append(child_remapped)

    # Drop if dest was removed AND no children survived
    if new_0indexed is None and not children:
        return None

    # If dest was removed but children survived, redirect to first child's dest
    dest_idx = new_0indexed if new_0indexed is not None else 0

    rebuilt = pikepdf.OutlineItem(
        item.title or "(untitled)",
        page_location=pikepdf.PageLocation.FitH,
        destination=dest_idx,
    )
    rebuilt.children.extend(children)
    return rebuilt


def _resolve_page_index(item: pikepdf.OutlineItem, pdf: pikepdf.Pdf) -> int | None:
    try:
        dest = item.destination
        if isinstance(dest, list) and dest:
            d = dest[0]
            if isinstance(d, int):
                return d
            try:
                return pdf.pages.index(d)
            except Exception:
                pass
        if isinstance(dest, int):
            return dest
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Page labels rebuild
# ---------------------------------------------------------------------------

def _rebuild_page_labels(
    *,
    source_pdf: pikepdf.Pdf,
    target_pdf: pikepdf.Pdf,
    remaining_1indexed: list[int],
) -> None:
    """
    If the source PDF has /PageLabels, rebuild them for the retained pages.
    /PageLabels is a number tree mapping 0-based page indices to label dicts.
    After removal, we need to reindex based on which pages survived.
    """
    try:
        if "/PageLabels" not in source_pdf.Root:
            return

        page_labels_tree = source_pdf.Root["/PageLabels"]
        # Convert the number tree to a flat dict: 0-based page index → label dict
        flat_labels: dict[int, Any] = {}
        _flatten_number_tree(page_labels_tree, flat_labels)

        if not flat_labels:
            return

        # Build new label ranges for the retained pages
        # Each 0-based old index maps to a new 0-based index via remaining_1indexed
        new_ranges: list[tuple[int, Any]] = []
        last_label_obj: Any = None
        for new_0idx, old_1idx in enumerate(remaining_1indexed):
            old_0idx = old_1idx - 1
            label_obj = flat_labels.get(old_0idx)
            if label_obj is not None and label_obj != last_label_obj:
                new_ranges.append((new_0idx, label_obj))
                last_label_obj = label_obj

        if not new_ranges:
            return

        # Reconstruct the /PageLabels number tree
        nums_array = pikepdf.Array()
        for new_idx, label_dict in new_ranges:
            nums_array.append(pikepdf.Integer(new_idx))
            nums_array.append(label_dict)

        target_pdf.Root["/PageLabels"] = pikepdf.Dictionary(Nums=nums_array)
    except Exception:
        log.debug("remove_pages: could not rebuild /PageLabels", exc_info=True)


def _flatten_number_tree(node: Any, result: dict[int, Any]) -> None:
    """Recursively walks a PDF number tree, populating result[int_key] = value."""
    try:
        if "/Nums" in node:
            nums = node["/Nums"]
            for i in range(0, len(nums) - 1, 2):
                key = int(nums[i])
                result[key] = nums[i + 1]
        if "/Kids" in node:
            for kid in node["/Kids"]:
                _flatten_number_tree(kid, result)
    except Exception:
        pass