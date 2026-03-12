"""
watermark.py — Enterprise-grade PDF Watermark Processor
========================================================
KEY FEATURES:
  • Vector text watermark via fitz (crisp at any zoom/print scale)
  • Image watermark support (company logo, CONFIDENTIAL stamp)
  • Rotation applied for ALL positions (not just diagonal)
  • skip_pages support (e.g., skip cover page)
  • first_page_only mode
  • Font family selection (helv, timr, cour, zadb)
  • Opacity range 0.0–1.0 with correct alpha blending
  • Per-page rendering adapts to page dimensions
  • Both text and image watermark can be combined
"""
from __future__ import annotations

import logging
import math
from pathlib import Path

import fitz

from app.models.enums import ArtifactKind
from app.schemas.job import WatermarkJobRequest
from app.services.pdf.advanced_utils import hex_to_rgb, pdf_page_count
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

# fitz built-in font names
_FONT_MAP = {
    "helv": "helv",
    "helvetica": "helv",
    "arial": "helv",
    "timr": "timr",
    "times": "timr",
    "times new roman": "timr",
    "cour": "cour",
    "courier": "cour",
    "zadb": "zadb",
}
_DEFAULT_FONT = "helv"


class WatermarkPdfProcessor(BaseToolProcessor):
    tool_id = "watermark"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = WatermarkJobRequest.model_validate(context.payload)
        source = context.require_single_input()
        output_filename = ensure_pdf_output_filename(payload.output_filename)
        output_path = context.workspace / output_filename

        # Parse optional extended parameters (with safe defaults for schema compat)
        skip_pages: set[int] = set(getattr(payload, "skip_pages", None) or [])
        first_page_only: bool = getattr(payload, "first_page_only", False)
        font_family: str = _FONT_MAP.get(
            (getattr(payload, "font_family", None) or "helv").lower(), _DEFAULT_FONT
        )
        # Optional image watermark upload path
        image_upload_path: Path | None = None
        image_upload_id = getattr(payload, "image_upload_id", None)
        if image_upload_id:
            for inp in context.inputs[1:]:  # second input = watermark image
                if inp.public_id == image_upload_id:
                    image_upload_path = inp.storage_path
                    break

        text_color = _safe_hex_to_rgb(getattr(payload, "color", "#000000") or "#000000")
        opacity = max(0.0, min(1.0, payload.opacity))
        rotation = payload.rotation  # degrees

        with fitz.open(source.storage_path) as doc:
            page_count = doc.page_count
            pages_watermarked = 0
            for page_idx in range(page_count):
                page_num_1indexed = page_idx + 1
                if page_num_1indexed in skip_pages:
                    continue
                if first_page_only and page_idx > 0:
                    continue

                page = doc.load_page(page_idx)

                if image_upload_path and image_upload_path.exists():
                    _apply_image_watermark(
                        page=page,
                        image_path=image_upload_path,
                        position=payload.position,
                        opacity=opacity,
                        rotation=rotation,
                    )

                _apply_vector_text_watermark(
                    page=page,
                    text=payload.text,
                    position=payload.position,
                    font_name=font_family,
                    font_size=payload.font_size,
                    color=text_color,
                    opacity=opacity,
                    rotation=rotation,
                )
                pages_watermarked += 1

            doc.save(
                output_path,
                garbage=3,
                deflate=True,
                clean=True,
            )

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=output_path,
                filename=output_filename,
                content_type=PDF_CONTENT_TYPE,
                kind=ArtifactKind.RESULT,
                metadata={
                    "pages_processed": pages_watermarked,
                    "total_pages": page_count,
                    "watermark_type": "image+text" if image_upload_path else "text",
                    "position": payload.position,
                    "opacity": opacity,
                },
            ),
            completion_message=f"Watermark applied to {pages_watermarked} page(s).",
        )


# ---------------------------------------------------------------------------
# Vector text watermark (superior to raster PNG overlay)
# ---------------------------------------------------------------------------

def _apply_vector_text_watermark(
    *,
    page: fitz.Page,
    text: str,
    position: str,
    font_name: str,
    font_size: float,
    color: tuple[float, float, float],
    opacity: float,
    rotation: float,
) -> None:
    """
    Inserts a vector text watermark using fitz's draw layer with transformation matrix.
    This is crisp at all zoom levels and print resolutions.
    """
    page_rect = page.rect
    pw, ph = page_rect.width, page_rect.height

    # Estimate text dimensions
    text_width_approx = len(text) * font_size * 0.55
    text_height_approx = font_size * 1.2

    # Compute center point for the text based on position
    cx, cy = _position_to_center(
        position=position,
        page_w=pw,
        page_h=ph,
        text_w=text_width_approx,
        text_h=text_height_approx,
    )

    # Build a transformation matrix: rotate around (cx, cy)
    angle_rad = math.radians(rotation)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    morph_matrix = fitz.Matrix(cos_a, -sin_a, sin_a, cos_a, 0, 0)
    morph_origin = fitz.Point(cx, cy)

    # Insert the text as a vector annotation
    page.insert_text(
        fitz.Point(cx - text_width_approx / 2, cy + text_height_approx / 4),
        text,
        fontname=font_name,
        fontsize=font_size,
        color=color,
        morph=(morph_origin, morph_matrix),
        overlay=True,
        fill_opacity=opacity,
        stroke_opacity=opacity,
    )


# ---------------------------------------------------------------------------
# Image watermark
# ---------------------------------------------------------------------------

def _apply_image_watermark(
    *,
    page: fitz.Page,
    image_path: Path,
    position: str,
    opacity: float,
    rotation: float,
) -> None:
    """
    Embeds an image watermark onto the page at the specified position.
    Opacity is applied via the image's alpha channel.
    """
    try:
        from PIL import Image as PILImage
        import io

        with PILImage.open(image_path) as img:
            # Convert to RGBA to apply opacity
            img_rgba = img.convert("RGBA")
            r, g, b, a = img_rgba.split()
            # Apply opacity to alpha channel
            import PIL.ImageEnhance
            a_opacity = PIL.ImageEnhance.Brightness(a).enhance(opacity)
            img_rgba = PILImage.merge("RGBA", (r, g, b, a_opacity))
            # Apply rotation
            if rotation != 0:
                img_rgba = img_rgba.rotate(-rotation, expand=True, resample=PILImage.Resampling.BICUBIC)

            buf = io.BytesIO()
            img_rgba.save(buf, format="PNG")
            buf.seek(0)
            img_bytes = buf.read()

        pw, ph = page.rect.width, page.rect.height
        # Scale image to 30% of page width
        img_display_w = pw * 0.30
        img_display_h = img_display_w * (img_rgba.height / img_rgba.width) if img_rgba.width > 0 else img_display_w

        cx, cy = _position_to_center(
            position=position,
            page_w=pw,
            page_h=ph,
            text_w=img_display_w,
            text_h=img_display_h,
        )
        rect = fitz.Rect(
            cx - img_display_w / 2,
            cy - img_display_h / 2,
            cx + img_display_w / 2,
            cy + img_display_h / 2,
        )
        page.insert_image(rect, stream=img_bytes, overlay=True)
    except Exception as exc:
        log.warning("watermark: failed to apply image watermark: %s", exc)


# ---------------------------------------------------------------------------
# Position helpers
# ---------------------------------------------------------------------------

def _position_to_center(
    *,
    position: str,
    page_w: float,
    page_h: float,
    text_w: float,
    text_h: float,
) -> tuple[float, float]:
    """Returns the (cx, cy) center point for watermark placement."""
    margin = 30.0
    if position in ("center", "diagonal"):
        return page_w / 2, page_h / 2
    if position == "top_left":
        return margin + text_w / 2, margin + text_h / 2
    if position == "top_right":
        return page_w - margin - text_w / 2, margin + text_h / 2
    if position == "bottom_left":
        return margin + text_w / 2, page_h - margin - text_h / 2
    if position == "bottom_right":
        return page_w - margin - text_w / 2, page_h - margin - text_h / 2
    if position == "top_center":
        return page_w / 2, margin + text_h / 2
    if position == "bottom_center":
        return page_w / 2, page_h - margin - text_h / 2
    return page_w / 2, page_h / 2


def _safe_hex_to_rgb(value: str) -> tuple[float, float, float]:
    try:
        return hex_to_rgb(value)
    except (ValueError, Exception):
        return (0.0, 0.0, 0.0)