"""
editor_apply.py — ApplyPdfEditorChangesProcessor
=================================================
Main processor for the PDF editor.  Accepts a validated EditorApplyJobRequest
and produces a fully edited PDF by:

  1. Validating all operations against the actual PDF document (page count, coords)
  2. Applying overlay operations to the fitz content stream (text, images, shapes)
  3. Applying structural operations via pikepdf (rotate, delete, reorder)
  4. Saving with linearisation and garbage collection

Integration points:
  • Register in processor.py: ``"editor_apply": lambda settings: ApplyPdfEditorChangesProcessor()``
  • Add EditorApplyJobRequest to TOOL_PAYLOAD_MODELS in schemas/job.py

Processing guarantees:
  • The source PDF is never modified.  All work is done in the job workspace.
  • Atomic: if any step fails, the workspace temp file is cleaned up.
  • Workspace-isolated: output paths are always relative to context.workspace.
"""
from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

import fitz

from app.models.enums import ArtifactKind
from app.schemas.editor_operations_schema import (
    OVERLAY_OPERATION_TYPES,
    STRUCTURAL_OPERATION_TYPES,
    AnyEditorOperation,
    EditorApplyJobRequest,
)
from app.services.pdf.advanced_utils import pdf_page_count
from app.services.pdf.common import (
    BaseToolProcessor,
    GeneratedArtifact,
    PDF_CONTENT_TYPE,
    PdfProcessingError,
    ProcessingResult,
    ProcessorContext,
    ensure_pdf_output_filename,
)
from app.services.pdf.editor_operations import (
    apply_overlay_operations,
    apply_structural_operations,
)
from app.services.pdf.editor_validation import validate_editor_job

log = logging.getLogger(__name__)


class ApplyPdfEditorChangesProcessor(BaseToolProcessor):
    """
    Applies a list of typed editor operations (JSON from the frontend editor UI)
    to a PDF and returns the modified PDF as a downloadable artifact.

    The operation pipeline is:
      Phase 1 — Validation   : validate_editor_job()
      Phase 2 — Overlay pass : open with fitz; apply text/shape/image ops
      Phase 3 — Save overlay : save fitz doc to workspace/<overlay>.pdf
      Phase 4 — Structural   : pikepdf rotate/delete/reorder to final output
      Phase 5 — Cleanup      : remove temp overlay file
    """

    tool_id = "editor_apply"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = EditorApplyJobRequest.model_validate(context.payload)
        source = context.require_single_input()
        output_filename = ensure_pdf_output_filename(payload.output_filename)
        start_time = time.time()

        # Workspace-relative output path — enforces path-traversal isolation
        output_path = _safe_workspace_path(context.workspace, output_filename)

        # ── Phase 1: Validate ──────────────────────────────────────────────
        log.info(
            "editor_apply: validating %d operations [job=%s tool=%s]",
            len(payload.operations),
            context.job_id,
            context.tool_id,
        )
        validate_editor_job(
            payload=payload,
            pdf_path=source.storage_path,
            pdf_size_bytes=source.size_bytes,
        )

        # Partition operations by kind
        overlay_ops: list[AnyEditorOperation] = [
            op for op in payload.operations if op.type in OVERLAY_OPERATION_TYPES
        ]
        structural_ops: list[AnyEditorOperation] = [
            op for op in payload.operations if op.type in STRUCTURAL_OPERATION_TYPES
        ]

        has_overlays = bool(overlay_ops)
        has_structural = bool(structural_ops)

        log.debug(
            "editor_apply: %d overlay ops, %d structural ops [job=%s]",
            len(overlay_ops),
            len(structural_ops),
            context.job_id,
        )

        # If there are no operations at all, copy source unchanged
        if not has_overlays and not has_structural:
            shutil.copy2(source.storage_path, output_path)
            log.info(
                "editor_apply: no operations to apply; source copied as-is [job=%s]",
                context.job_id,
            )
            return _build_result(output_path=output_path, filename=output_filename, ops_applied=0)

        # ── Phase 2 & 3: Overlay pass ──────────────────────────────────────
        overlay_output_path = context.workspace / "_editor_overlay_tmp.pdf"
        overlay_saved_path = context.workspace / "_editor_overlay_result.pdf"
        ops_applied = 0

        try:
            if has_overlays:
                # Copy source to overlay temp file so we never modify the original
                shutil.copy2(source.storage_path, overlay_output_path)

                with fitz.open(str(overlay_output_path)) as doc:
                    ops_applied = apply_overlay_operations(doc, overlay_ops)
                    # Save to a separate temp file because PyMuPDF does not allow
                    # non-incremental saves back onto the currently opened source path.
                    doc.save(
                        str(overlay_saved_path),
                        garbage=3,
                        deflate=True,
                        incremental=False,
                    )

                overlay_output_path.unlink(missing_ok=True)
                shutil.move(str(overlay_saved_path), str(overlay_output_path))

                log.info(
                    "editor_apply: applied %d overlay ops to page content [job=%s]",
                    ops_applied,
                    context.job_id,
                )
            else:
                # No overlay ops; pass source directly to structural stage
                shutil.copy2(source.storage_path, overlay_output_path)

            # ── Phase 4: Structural pass ───────────────────────────────────
            if has_structural:
                apply_structural_operations(
                    source_path=overlay_output_path,
                    output_path=output_path,
                    operations=structural_ops,
                )
                ops_applied += len(structural_ops)
                log.info(
                    "editor_apply: applied %d structural ops [job=%s]",
                    len(structural_ops),
                    context.job_id,
                )
            else:
                # No structural ops; rename/move the overlay result to final output
                if not overlay_output_path.exists():
                    raise PdfProcessingError(
                        code="editor_overlay_missing",
                        user_message="Temporary editor output was lost during processing.",
                    )
                shutil.move(str(overlay_output_path), str(output_path))

        except PdfProcessingError:
            raise
        except Exception as exc:
            log.exception(
                "editor_apply: unexpected error during processing [job=%s]: %s",
                context.job_id,
                exc,
            )
            raise PdfProcessingError(
                code="editor_apply_unexpected",
                user_message=f"PDF editor processing failed: {exc}",
            ) from exc
        finally:
            # ── Phase 5: Cleanup ───────────────────────────────────────────
            overlay_output_path.unlink(missing_ok=True)
            overlay_saved_path.unlink(missing_ok=True)

        # Sanity check: output must exist and be valid
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise PdfProcessingError(
                code="editor_apply_empty_output",
                user_message="The editor produced an empty or missing output file.",
            )

        final_pages = pdf_page_count(output_path)
        elapsed = time.time() - start_time
        log.info(
            "editor_apply: completed in %.2fs — %d ops applied, %d output pages, %.1f KB [job=%s]",
            elapsed,
            ops_applied,
            final_pages,
            output_path.stat().st_size / 1024,
            context.job_id,
        )

        return _build_result(
            output_path=output_path,
            filename=output_filename,
            ops_applied=ops_applied,
            final_pages=final_pages,
            overlay_count=len(overlay_ops),
            structural_count=len(structural_ops),
        )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_workspace_path(workspace: Path, filename: str) -> Path:
    """
    Resolves a filename within the workspace and validates it does not
    escape the workspace directory (path-traversal protection).
    """
    candidate = (workspace / filename).resolve()
    try:
        candidate.relative_to(workspace.resolve())
    except ValueError as exc:
        raise PdfProcessingError(
            code="editor_path_traversal",
            user_message="The requested output filename is not allowed.",
        ) from exc
    return candidate


def _build_result(
    *,
    output_path: Path,
    filename: str,
    ops_applied: int,
    final_pages: int | None = None,
    overlay_count: int = 0,
    structural_count: int = 0,
) -> ProcessingResult:
    """Constructs the ProcessingResult with rich metadata."""
    metadata: dict = {
        "operations_applied": ops_applied,
        "overlay_operations": overlay_count,
        "structural_operations": structural_count,
    }
    if final_pages is not None:
        metadata["pages_processed"] = final_pages

    return ProcessingResult(
        artifact=GeneratedArtifact(
            local_path=output_path,
            filename=filename,
            content_type=PDF_CONTENT_TYPE,
            kind=ArtifactKind.RESULT,
            metadata=metadata,
        ),
        completion_message=(
            f"PDF editor: {ops_applied} operation(s) applied successfully."
        ),
    )
