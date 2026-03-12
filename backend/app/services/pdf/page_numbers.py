"""
page_numbers.py — Enterprise-grade PDF Page Numbers Processor
=============================================================
KEY FEATURES:
  • Arabic, Roman (lower/upper), Alpha (lower/upper) numbering styles
  • skip_first_n_pages and skip_last_n_pages support
  • Background box behind the number for readability on complex backgrounds
  • Font family selection (helv, timr, cour)
  • Auto-shrink: if text doesn't fit in the box, reduces font size
  • insert_textbox return value checked for overflow
  • Margin from edge configurable (default 24pt)
"""
from __future__ import annotations

import logging

import fitz

from app.models.enums import ArtifactKind
from app.schemas.job import PageNumbersJobRequest
from app.services.pdf.advanced_utils import alignment_for_position, hex_to_rgb, resolve_position_rect
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

_ROMAN_ONES = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
_ROMAN_TENS = ["", "X", "XX", "XXX", "XL", "L", "LX", "LXX", "LXXX", "XC"]
_ROMAN_HUNDS = ["", "C", "CC", "CCC", "CD", "D", "DC", "DCC", "DCCC", "CM"]
_ROMAN_THOU = ["", "M", "MM", "MMM"]
_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class PageNumbersPdfProcessor(BaseToolProcessor):
    tool_id = "pagenums"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = PageNumbersJobRequest.model_validate(context.payload)
        source = context.require_single_input()
        output_filename = ensure_pdf_output_filename(payload.output_filename)
        output_path = context.workspace / output_filename

        color = _safe_hex_to_rgb(payload.color, field="color")
        font_name = _resolve_font(getattr(payload, "font_family", None))
        numbering_style = (getattr(payload, "numbering_style", None) or "arabic").lower()
        skip_first = max(0, getattr(payload, "skip_first_n_pages", 0) or 0)
        skip_last = max(0, getattr(payload, "skip_last_n_pages", 0) or 0)
        background_box: bool = getattr(payload, "background_box", False)

        with fitz.open(source.storage_path) as doc:
            page_count = doc.page_count
            pages_numbered = 0
            logical_number = payload.start_number  # tracks the displayed number

            for index in range(page_count):
                page_1indexed = index + 1
                # Determine if this page gets a number
                in_skip_first = index < skip_first
                in_skip_last = index >= page_count - skip_last
                if in_skip_first or in_skip_last:
                    logical_number += 1  # still advance the counter
                    continue

                page = doc.load_page(index)
                text = _format_number(
                    n=logical_number,
                    style=numbering_style,
                    prefix=payload.prefix or "",
                    suffix=payload.suffix or "",
                )

                font_size = float(payload.font_size)
                rect = resolve_position_rect(
                    page_rect=page.rect,
                    position=payload.position,
                    width=min(200, page.rect.width - 60),
                    height=font_size + 14,
                )

                # Draw background box if requested
                if background_box:
                    page.draw_rect(
                        rect,
                        color=None,
                        fill=(1.0, 1.0, 1.0),
                        overlay=True,
                    )

                # Try to insert, auto-shrink if it doesn't fit
                for attempt_size in (font_size, font_size * 0.8, font_size * 0.6, max(6.0, font_size * 0.4)):
                    result = page.insert_textbox(
                        rect,
                        text,
                        fontsize=attempt_size,
                        fontname=font_name,
                        color=color,
                        align=alignment_for_position(payload.position),
                        overlay=True,
                    )
                    if result >= 0:
                        break
                    # Negative result means text didn't fit; try smaller

                logical_number += 1
                pages_numbered += 1

            doc.save(output_path, garbage=3, deflate=True)

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=output_path,
                filename=output_filename,
                content_type=PDF_CONTENT_TYPE,
                kind=ArtifactKind.RESULT,
                metadata={
                    "pages_processed": pages_numbered,
                    "total_pages": page_count,
                    "numbering_style": numbering_style,
                    "start_number": payload.start_number,
                },
            ),
            completion_message=f"Page numbers added to {pages_numbered} page(s).",
        )


# ---------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------

def _format_number(*, n: int, style: str, prefix: str, suffix: str) -> str:
    """Formats a logical page number according to the requested style."""
    if style in ("roman_lower", "roman"):
        num_str = _to_roman(n).lower()
    elif style == "roman_upper":
        num_str = _to_roman(n).upper()
    elif style == "alpha_lower":
        num_str = _to_alpha(n).lower()
    elif style == "alpha_upper":
        num_str = _to_alpha(n).upper()
    else:  # arabic
        num_str = str(n)
    return f"{prefix}{num_str}{suffix}"


def _to_roman(n: int) -> str:
    """Converts a positive integer to a Roman numeral string (supports 1–3999)."""
    if n <= 0 or n >= 4000:
        return str(n)
    thousands = n // 1000
    hundreds = (n % 1000) // 100
    tens = (n % 100) // 10
    ones = n % 10
    return _ROMAN_THOU[thousands] + _ROMAN_HUNDS[hundreds] + _ROMAN_TENS[tens] + _ROMAN_ONES[ones]


def _to_alpha(n: int) -> str:
    """
    Converts a positive integer to alphabetical labeling:
    1→A, 2→B, …, 26→Z, 27→AA, 28→AB, …
    """
    if n <= 0:
        return str(n)
    result = ""
    while n > 0:
        n -= 1
        result = _ALPHA[n % 26] + result
        n //= 26
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_hex_to_rgb(value: str, *, field: str) -> tuple[float, float, float]:
    try:
        return hex_to_rgb(value)
    except ValueError as exc:
        raise PdfProcessingError(code="invalid_color", user_message=str(exc)) from exc


def _resolve_font(font_family: str | None) -> str:
    if not font_family:
        return "helv"
    mapping = {"helv": "helv", "helvetica": "helv", "arial": "helv",
               "timr": "timr", "times": "timr", "cour": "cour", "courier": "cour"}
    return mapping.get(font_family.lower(), "helv")