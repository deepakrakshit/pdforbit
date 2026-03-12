"""
pdf_to_image.py — Enterprise-grade PDF to Image Processor
==========================================================
KEY FEATURES:
  • JPEG quality configurable (default 85 for high quality)
  • Guaranteed white background for all formats (no transparency artifacts)
  • Single-page mode: returns a direct image file instead of a ZIP
  • Thumbnail mode: fast low-res preview of page 1 (or any page)
  • WEBP support with quality parameter
  • ZIP uses STORED compression (images already compressed)
  • DPI validated against policy before processing
  • Memory-efficient: processes pages one at a time without buffering all
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
import zipfile

import fitz
from PIL import Image as PILImage

from app.models.enums import ArtifactKind
from app.schemas.job import PdfToImageJobRequest
from app.services.pdf.common import (
    BaseToolProcessor,
    GeneratedArtifact,
    ProcessingResult,
    ProcessorContext,
    ZIP_CONTENT_TYPE,
    ensure_zip_output_filename,
    PdfProcessingError,
)

log = logging.getLogger(__name__)

# MIME types for each image format
_IMAGE_CONTENT_TYPES = {
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "png":  "image/png",
    "webp": "image/webp",
}


class PdfToImageProcessor(BaseToolProcessor):
    tool_id = "pdf2img"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = PdfToImageJobRequest.model_validate(context.payload)
        source = context.require_single_input()

        fmt = payload.format.lower()
        dpi = payload.dpi
        quality: int = getattr(payload, "quality", 85) or 85
        single_page: int | None = getattr(payload, "single_page", None)
        thumbnail: bool = getattr(payload, "thumbnail", False)
        thumbnail_max_px: int = getattr(payload, "thumbnail_max_px", 512) or 512

        if thumbnail:
            dpi = 72
            single_page = single_page or 1

        with fitz.open(source.storage_path) as doc:
            total_pages = doc.page_count

            # --- Single-page mode: return a direct image file ---
            if single_page is not None:
                if single_page < 1 or single_page > total_pages:
                    raise PdfProcessingError(
                        code="invalid_page",
                        user_message=f"Page {single_page} does not exist (document has {total_pages} pages).",
                    )
                stem = Path(source.original_filename).stem
                image_filename = f"{stem}-page-{single_page}.{fmt}"
                image_path = context.workspace / image_filename
                image_bytes = _render_page_to_bytes(
                    doc.load_page(single_page - 1),
                    dpi=dpi,
                    fmt=fmt,
                    quality=quality,
                    thumbnail_max_px=thumbnail_max_px if thumbnail else None,
                )
                image_path.write_bytes(image_bytes)
                return ProcessingResult(
                    artifact=GeneratedArtifact(
                        local_path=image_path,
                        filename=image_filename,
                        content_type=_IMAGE_CONTENT_TYPES.get(fmt, "image/jpeg"),
                        kind=ArtifactKind.RESULT,
                        metadata={
                            "pages_processed": 1,
                            "page_number": single_page,
                            "format": fmt,
                            "dpi": dpi,
                            "thumbnail": thumbnail,
                        },
                    ),
                    completion_message=f"Page {single_page} exported as {fmt.upper()} successfully.",
                )

            # --- Multi-page mode: ZIP archive ---
            stem = Path(source.original_filename).stem
            archive_filename = ensure_zip_output_filename(f"{stem}-{fmt}.zip")
            archive_path = context.workspace / archive_filename

            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
                for index in range(total_pages):
                    image_bytes = _render_page_to_bytes(
                        doc.load_page(index),
                        dpi=dpi,
                        fmt=fmt,
                        quality=quality,
                        thumbnail_max_px=None,
                    )
                    image_name = f"page-{index + 1:04d}.{fmt}"
                    archive.writestr(image_name, image_bytes)
                    log.debug("pdf2img: rendered page %d/%d", index + 1, total_pages)

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=archive_path,
                filename=archive_filename,
                content_type=ZIP_CONTENT_TYPE,
                kind=ArtifactKind.ARCHIVE,
                metadata={
                    "parts_count": total_pages,
                    "pages_processed": total_pages,
                    "format": fmt,
                    "dpi": dpi,
                    "quality": quality,
                },
            ),
            completion_message=f"Exported {total_pages} pages as {fmt.upper()} images.",
        )


# ---------------------------------------------------------------------------
# Page rendering
# ---------------------------------------------------------------------------

def _render_page_to_bytes(
    page: fitz.Page,
    *,
    dpi: int,
    fmt: str,
    quality: int,
    thumbnail_max_px: int | None,
) -> bytes:
    """
    Renders a PDF page to image bytes.
    alpha=False ensures a white background on all image formats.
    """

    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    # Convert pixmap → PIL Image for format-specific encoding
    pil_img = PILImage.open(io.BytesIO(pixmap.tobytes("png")))

    # Thumbnail mode: scale down to fit within thumbnail_max_px × thumbnail_max_px
    if thumbnail_max_px:
        pil_img.thumbnail((thumbnail_max_px, thumbnail_max_px), PILImage.Resampling.LANCZOS)

    buf = io.BytesIO()
    if fmt in {"jpg", "jpeg"}:
        pil_img = pil_img.convert("RGB")  # ensure no alpha for JPEG
        pil_img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    elif fmt == "webp":
        pil_img.save(buf, format="WEBP", quality=quality, method=4)
    else:  # png
        pil_img.save(buf, format="PNG", optimize=True, compress_level=6)

    return buf.getvalue()