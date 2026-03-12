"""
image_to_pdf.py — Enterprise-grade Image to PDF Processor
==========================================================
KEY FEATURES:
  • Multiple input images → one page per image in a single PDF
  • EXIF orientation auto-correction (fixes rotated phone photos)
  • RGBA/palette images composited over white background (no black bg)
  • Multi-frame TIFF support (each frame becomes a page)
  • Configurable DPI (default 150 for screen, 300 for print)
  • Page size modes: original (match image dimensions), A4, Letter, fit
  • fitz (PyMuPDF) PDF assembly for superior image embedding
  • Per-image error recovery (bad image → error in metadata, not crash)
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Iterator

import fitz
from PIL import Image, ImageOps

from app.models.enums import ArtifactKind
from app.schemas.job import ConvertToPdfJobRequest
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

log = logging.getLogger(__name__)

# Points per inch in PDF coordinate space
_POINTS_PER_INCH = 72.0

# Standard page sizes in points (width, height) — portrait
PAGE_SIZES_PT: dict[str, tuple[float, float]] = {
    "A4":     (595.28, 841.89),
    "Letter": (612.0,  792.0),
    "Legal":  (612.0,  1008.0),
    "A3":     (841.89, 1190.55),
}


class ImageToPdfProcessor(BaseToolProcessor):
    tool_id = "img2pdf"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = ConvertToPdfJobRequest.model_validate(context.payload)
        output_filename = ensure_pdf_output_filename(payload.output_filename)
        output_path = context.workspace / output_filename

        if not context.inputs:
            raise PdfProcessingError(
                code="missing_job_input",
                user_message="At least one image file is required.",
            )

        # Extract optional settings from payload (with safe defaults)
        dpi: int = getattr(payload, "dpi", 150) or 150
        page_size_name: str = getattr(payload, "page_size", "original") or "original"

        doc = fitz.open()
        total_pages = 0
        failed_inputs: list[str] = []

        for source in context.inputs:
            try:
                frames_added = _embed_image_file(
                    doc=doc,
                    image_path=source.storage_path,
                    dpi=dpi,
                    page_size_name=page_size_name,
                )
                total_pages += frames_added
                log.debug("img2pdf: embedded %d frame(s) from '%s'", frames_added, source.original_filename)
            except Exception as exc:
                log.warning("img2pdf: failed to embed '%s': %s", source.original_filename, exc)
                failed_inputs.append(source.original_filename)

        if total_pages == 0:
            raise PdfProcessingError(
                code="img2pdf_no_pages",
                user_message=(
                    "No images could be converted. "
                    + (f"Failed: {', '.join(failed_inputs)}" if failed_inputs else "")
                ),
            )

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=output_path,
                filename=output_filename,
                content_type=PDF_CONTENT_TYPE,
                kind=ArtifactKind.RESULT,
                metadata={
                    "pages_processed": total_pages,
                    "sources_count": len(context.inputs),
                    "dpi": dpi,
                    "page_size": page_size_name,
                    **({"failed_inputs": failed_inputs} if failed_inputs else {}),
                },
            ),
            completion_message=f"Converted {total_pages} image(s) to PDF successfully.",
        )


# ---------------------------------------------------------------------------
# Image embedding helpers
# ---------------------------------------------------------------------------

def _embed_image_file(
    *,
    doc: fitz.Document,
    image_path: Path,
    dpi: int,
    page_size_name: str,
) -> int:
    """
    Opens an image file (including multi-frame TIFF), corrects EXIF orientation,
    composites transparency over white, and inserts each frame as a PDF page.
    Returns the number of frames/pages added.
    """
    frames_added = 0
    for pil_image in _iter_frames(image_path):
        # 1. Apply EXIF orientation tag (critical for phone photos)
        pil_image = ImageOps.exif_transpose(pil_image)

        # 2. Composite RGBA / palette images over white background
        pil_image = _flatten_to_rgb(pil_image)

        # 3. Determine target page dimensions in points
        img_w_pt, img_h_pt = _image_size_in_points(pil_image, dpi=dpi)
        page_w_pt, page_h_pt = _target_page_size(
            img_w_pt=img_w_pt,
            img_h_pt=img_h_pt,
            page_size_name=page_size_name,
        )

        # 4. Create the PDF page
        page = doc.new_page(width=page_w_pt, height=page_h_pt)

        # 5. Fit the image into the page (centered if smaller, scaled if larger)
        img_rect = _fit_image_rect(
            img_w_pt=img_w_pt,
            img_h_pt=img_h_pt,
            page_w_pt=page_w_pt,
            page_h_pt=page_h_pt,
        )

        # 6. Embed as PNG bytes for lossless quality; fitz handles compression
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        buf.seek(0)
        page.insert_image(img_rect, stream=buf.read())

        frames_added += 1
    return frames_added


def _iter_frames(image_path: Path) -> Iterator[Image.Image]:
    """
    Yields PIL Image frames. For multi-frame TIFFs, yields each frame.
    For animated GIFs, yields each frame. For regular images, yields once.
    """
    with Image.open(image_path) as img:
        # Detect multi-frame images
        try:
            n_frames = getattr(img, "n_frames", 1)
        except Exception:
            n_frames = 1

        if n_frames <= 1:
            yield img.copy()
            return

        for frame_idx in range(n_frames):
            try:
                img.seek(frame_idx)
                yield img.copy()
            except EOFError:
                break


def _flatten_to_rgb(img: Image.Image) -> Image.Image:
    """
    Converts any image mode to RGB, compositing transparency over pure white.
    Handles: RGBA, LA, P (palette), 1 (binary), L (grayscale), CMYK, etc.
    """
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        rgba = img.convert("RGBA")
        background.alpha_composite(rgba)
        return background.convert("RGB")
    if img.mode == "P":
        # Palette mode may have transparency
        rgba = img.convert("RGBA")
        return _flatten_to_rgb(rgba)
    if img.mode in ("1", "L", "I", "F"):
        return img.convert("RGB")
    if img.mode == "CMYK":
        return img.convert("RGB")
    if img.mode == "RGB":
        return img
    # Fallback
    return img.convert("RGB")


def _image_size_in_points(img: Image.Image, *, dpi: int) -> tuple[float, float]:
    """Returns image physical size in PDF points at the given DPI."""
    # Prefer embedded DPI from image metadata if available
    img_dpi_x, img_dpi_y = _get_image_dpi(img, fallback=dpi)
    w_pt = img.width * (_POINTS_PER_INCH / img_dpi_x)
    h_pt = img.height * (_POINTS_PER_INCH / img_dpi_y)
    return w_pt, h_pt


def _get_image_dpi(img: Image.Image, *, fallback: int) -> tuple[float, float]:
    """Reads DPI from image info dict, falling back to the provided default."""
    try:
        dpi_info = img.info.get("dpi") or img.info.get("jfif_density")
        if isinstance(dpi_info, (tuple, list)) and len(dpi_info) == 2:
            x, y = float(dpi_info[0]), float(dpi_info[1])
            if x > 0 and y > 0:
                return x, y
    except Exception:
        pass
    return float(fallback), float(fallback)


def _target_page_size(
    *,
    img_w_pt: float,
    img_h_pt: float,
    page_size_name: str,
) -> tuple[float, float]:
    """Returns the PDF page dimensions in points."""
    if page_size_name == "original":
        # Page exactly matches the image dimensions
        return img_w_pt, img_h_pt
    if page_size_name == "fit":
        # Same as original but capped at A4 (useful for small images)
        max_w, max_h = PAGE_SIZES_PT["A4"]
        scale = min(max_w / img_w_pt, max_h / img_h_pt, 1.0)
        return img_w_pt * scale, img_h_pt * scale
    # Named page size (A4, Letter, etc.)
    w, h = PAGE_SIZES_PT.get(page_size_name, PAGE_SIZES_PT["A4"])
    # Keep portrait/landscape consistent with the image
    if img_w_pt > img_h_pt and w < h:
        return h, w  # rotate to landscape
    return w, h


def _fit_image_rect(
    *,
    img_w_pt: float,
    img_h_pt: float,
    page_w_pt: float,
    page_h_pt: float,
) -> fitz.Rect:
    """
    Returns the fitz.Rect where the image should be placed on the page.
    Scales down if the image is larger than the page; centers if smaller.
    """
    margin = 0.0  # no margin for "original" mode
    avail_w = page_w_pt - 2 * margin
    avail_h = page_h_pt - 2 * margin

    scale = min(avail_w / img_w_pt, avail_h / img_h_pt, 1.0)
    placed_w = img_w_pt * scale
    placed_h = img_h_pt * scale

    x0 = margin + (avail_w - placed_w) / 2
    y0 = margin + (avail_h - placed_h) / 2
    return fitz.Rect(x0, y0, x0 + placed_w, y0 + placed_h)