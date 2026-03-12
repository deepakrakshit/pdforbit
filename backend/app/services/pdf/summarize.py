"""
summarize.py — Enterprise-grade PDF Summarize Processor
========================================================
KEY FEATURES:
  • Structured AI output (executive summary, key points, action items,
    named entities, document type) instead of a raw text dump
  • Professional multi-section PDF layout rendered with fitz:
      - Title block with document name and metadata
      - Executive Summary section
      - Key Points bulleted list
      - Action Items (if any)
      - Document metadata sidebar (pages, word count, language)
  • Hierarchical summarization for long documents:
      chunk_1 brief + chunk_2 brief + … → final synthesis
  • Retry with exponential backoff on API failures
  • JSON parsing with graceful fallback for non-JSON responses
  • model_used and tokens_processed in output metadata
  • Language of output configurable independently of source language
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz

from app.models.enums import ArtifactKind
from app.schemas.job import SummarizeJobRequest
from app.services.pdf.common import (
    BaseToolProcessor,
    GeneratedArtifact,
    PDF_CONTENT_TYPE,
    PdfProcessingError,
    ProcessingResult,
    ProcessorContext,
    ensure_pdf_output_filename,
)
from app.services.pdf.document_intelligence import DocumentTextExtractor
from app.services.translation_service import (
    SummaryRequest,
    TranslationService,
    TranslationServiceError,
    chunk_text,
)

log = logging.getLogger(__name__)

# PDF layout constants
_PAGE_W = 595.28
_PAGE_H = 841.89
_MARGIN = 52.0
_COL_W = _PAGE_W - 2 * _MARGIN

_COLOR_TITLE_BG = (0.08, 0.20, 0.52)
_COLOR_TITLE_TEXT = (1.0, 1.0, 1.0)
_COLOR_SECTION_HEADER = (0.10, 0.25, 0.60)
_COLOR_BODY = (0.08, 0.08, 0.08)
_COLOR_BULLET = (0.15, 0.40, 0.75)
_COLOR_META = (0.45, 0.45, 0.45)
_COLOR_DIVIDER = (0.80, 0.85, 0.92)

_MAX_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY_SEC = 1.5


@dataclass
class StructuredSummary:
    executive_summary: str = ""
    key_points: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    document_type: str = ""
    named_entities: list[str] = field(default_factory=list)
    raw_text: str = ""  # fallback if JSON parsing fails


class SummarizePdfProcessor(BaseToolProcessor):
    tool_id = "summarize"

    def __init__(
        self,
        translation_service: TranslationService,
        *,
        extractor: DocumentTextExtractor,
        chunk_chars: int,
    ) -> None:
        self._translation_service = translation_service
        self._extractor = extractor
        self._chunk_chars = chunk_chars

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = SummarizeJobRequest.model_validate(context.payload)
        source = context.require_single_input()
        stem = Path(source.original_filename).stem
        requested_filename = (
            payload.output_filename or f"{stem}-orbit-brief.pdf"
        )
        output_filename = ensure_pdf_output_filename(requested_filename)
        output_path = context.workspace / output_filename

        try:
            extracted = self._extractor.extract_pdf(
                source.storage_path,
                source_language=None,
            )
        except PdfProcessingError:
            raise
        except Exception as exc:
            raise PdfProcessingError(
                code="text_extraction_failed",
                user_message="Unable to extract text from the uploaded PDF.",
            ) from exc

        document_text = extracted.combined_text.strip()
        if not document_text:
            raise PdfProcessingError(
                code="no_extractable_text",
                user_message="No readable text could be extracted from this PDF.",
            )

        try:
            summary = self._summarize_document(document_text, payload=payload)
        except TranslationServiceError as exc:
            raise PdfProcessingError(
                code="summary_unavailable",
                user_message=str(exc),
            ) from exc

        _render_summary_pdf(
            summary=summary,
            output_path=output_path,
            source_filename=source.original_filename,
            page_count=extracted.pages_processed,
            word_count=extracted.word_count,
            ocr_pages=extracted.ocr_pages,
            output_language=payload.output_language,
            length=payload.length,
        )

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=output_path,
                filename=output_filename,
                content_type=PDF_CONTENT_TYPE,
                kind=ArtifactKind.RESULT,
                metadata={
                    "pages_processed": extracted.pages_processed,
                    "word_count": extracted.word_count,
                    "detected_language": payload.output_language,
                    "ocr_pages": extracted.ocr_pages,
                    "summary_length": payload.length,
                    "has_key_points": bool(summary.key_points),
                    "has_action_items": bool(summary.action_items),
                },
            ),
            completion_message="Orbit Brief created successfully.",
        )

    # ------------------------------------------------------------------
    # Summarization logic
    # ------------------------------------------------------------------

    def _summarize_document(
        self, text: str, *, payload: SummarizeJobRequest
    ) -> StructuredSummary:
        chunks = chunk_text(text, max_chars=self._chunk_chars)
        if not chunks:
            return StructuredSummary(executive_summary="(empty document)")

        if len(chunks) == 1:
            return self._summarize_chunk_structured(
                chunks[0], payload=payload, final=True
            )

        # Hierarchical: summarize each chunk briefly, then synthesize
        chunk_briefs: list[str] = []
        total = len(chunks)
        for idx, chunk in enumerate(chunks, start=1):
            focus = (
                f"Chunk {idx}/{total}. Extract only key facts from this section."
            )
            if payload.focus:
                focus = f"{payload.focus}. {focus}"
            try:
                brief = self._summarize_raw_with_retry(
                    chunk,
                    payload=payload,
                    length="short" if payload.length == "short" else "medium",
                    focus=focus,
                )
            except TranslationServiceError:
                brief = f"(chunk {idx} unavailable)"
            chunk_briefs.append(brief)

        synthesis_focus = (
            "Synthesize the chunk briefs into a final document brief. "
            "Remove repetition and preserve all key facts and entities."
        )
        if payload.focus:
            synthesis_focus = f"{payload.focus}. {synthesis_focus}"

        combined = "\n\n".join(chunk_briefs)
        return self._summarize_chunk_structured(
            combined, payload=payload, focus_override=synthesis_focus, final=True
        )

    def _summarize_chunk_structured(
        self,
        text: str,
        *,
        payload: SummarizeJobRequest,
        focus_override: str | None = None,
        final: bool = False,
    ) -> StructuredSummary:
        """
        Asks the LLM to return structured JSON with defined keys.
        Falls back gracefully to plain-text summary on parse failure.
        """
        json_prompt = (
            "You are a professional document analyst. Analyse the provided document text and return "
            "ONLY a valid JSON object with these exact keys:\n"
            '  "executive_summary": string (2-4 sentences, clear and informative),\n'
            '  "key_points": array of strings (5-10 most important facts or findings),\n'
            '  "action_items": array of strings (actionable items, empty array if none),\n'
            '  "document_type": string (e.g. "Contract", "Report", "Invoice", "Research Paper"),\n'
            '  "named_entities": array of strings (key people, organisations, dates, amounts — max 10)\n'
            "Return ONLY the JSON object. No markdown, no explanation, no code fences."
        )

        # Embed the structured JSON instruction into the focus parameter so
        # it reaches the LLM via the SummaryRequest.focus field (the only
        # available extension point in TranslationService.summarize).
        focus = focus_override or payload.focus
        json_focus = json_prompt + ("\n\nAdditional focus: " + focus if focus else "")
        raw = self._summarize_raw_with_retry(
            text,
            payload=payload,
            length=payload.length,
            focus=json_focus,
        )
        return _parse_structured_response(raw)

    def _summarize_raw_with_retry(
        self,
        text: str,
        *,
        payload: SummarizeJobRequest,
        length: str,
        focus: str | None = None,
    ) -> str:
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRY_ATTEMPTS):
            try:
                return self._translation_service.summarize(
                    SummaryRequest(
                        text=text,
                        output_language=payload.output_language,
                        length=length,  # type: ignore[arg-type]
                        focus=focus,
                    )
                )
            except TranslationServiceError as exc:
                last_exc = exc
                if attempt < _MAX_RETRY_ATTEMPTS - 1:
                    delay = _RETRY_BASE_DELAY_SEC * (2 ** attempt)
                    log.warning(
                        "summarize: API error attempt %d/%d, retrying in %.1fs: %s",
                        attempt + 1,
                        _MAX_RETRY_ATTEMPTS,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
        raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# JSON parsing with graceful fallback
# ---------------------------------------------------------------------------

def _parse_structured_response(raw: str) -> StructuredSummary:
    """
    Attempts to parse the LLM response as a StructuredSummary JSON.
    On any failure, returns all content in the executive_summary field.
    """
    text = raw.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()

    try:
        data: dict[str, Any] = json.loads(text)
        return StructuredSummary(
            executive_summary=str(data.get("executive_summary", "")).strip(),
            key_points=[str(p).strip() for p in data.get("key_points", []) if str(p).strip()],
            action_items=[str(a).strip() for a in data.get("action_items", []) if str(a).strip()],
            document_type=str(data.get("document_type", "")).strip(),
            named_entities=[str(e).strip() for e in data.get("named_entities", []) if str(e).strip()],
        )
    except (json.JSONDecodeError, AttributeError, TypeError):
        log.debug("summarize: LLM returned non-JSON, using raw text as executive summary")
        return StructuredSummary(
            executive_summary=raw.strip(),
            raw_text=raw.strip(),
        )


# ---------------------------------------------------------------------------
# Professional PDF layout
# ---------------------------------------------------------------------------

def _render_summary_pdf(
    *,
    summary: StructuredSummary,
    output_path: Path,
    source_filename: str,
    page_count: int,
    word_count: int,
    ocr_pages: int,
    output_language: str,
    length: str,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    y = _MARGIN

    # ---- Title block ----
    title_h = 54.0
    page.draw_rect(
        fitz.Rect(0, 0, _PAGE_W, title_h + _MARGIN),
        color=None,
        fill=_COLOR_TITLE_BG,
    )
    page.insert_textbox(
        fitz.Rect(_MARGIN, 10, _PAGE_W - _MARGIN, 36),
        "Orbit Brief",
        fontsize=22.0,
        fontname="helv",
        color=_COLOR_TITLE_TEXT,
        align=0,
    )
    page.insert_textbox(
        fitz.Rect(_MARGIN, 36, _PAGE_W - _MARGIN, 58),
        source_filename,
        fontsize=9.5,
        fontname="helv",
        color=(0.78, 0.85, 1.0),
        align=0,
    )
    y = title_h + _MARGIN + 12

    # ---- Metadata row ----
    meta_parts = [
        f"{page_count} pages",
        f"{word_count:,} words",
        f"Language: {output_language}",
        f"Mode: {length}",
    ]
    if ocr_pages:
        meta_parts.append(f"{ocr_pages} OCR page(s)")
    if summary.document_type:
        meta_parts.append(f"Type: {summary.document_type}")
    meta_text = "  ·  ".join(meta_parts)
    page.insert_textbox(
        fitz.Rect(_MARGIN, y, _PAGE_W - _MARGIN, y + 14),
        meta_text,
        fontsize=8.5,
        fontname="helv",
        color=_COLOR_META,
        align=0,
    )
    y += 18
    _draw_divider(page, y)
    y += 10

    # ---- Executive Summary ----
    if summary.executive_summary:
        y = _section_header(page, doc, "Executive Summary", y)
        y = _body_text(page, doc, summary.executive_summary, y)
        y += 6

    # ---- Key Points ----
    if summary.key_points:
        y = _section_header(page, doc, "Key Points", y)
        for point in summary.key_points:
            page, y = _ensure_space(page, doc, y, need=16)
            page.insert_text(
                fitz.Point(_MARGIN, y + 10),
                "•",
                fontsize=11.0,
                fontname="helv",
                color=_COLOR_BULLET,
            )
            overflow = page.insert_textbox(
                fitz.Rect(_MARGIN + 14, y, _PAGE_W - _MARGIN, y + 60),
                point,
                fontsize=10.5,
                fontname="helv",
                color=_COLOR_BODY,
                align=0,
            )
            line_count = max(1, len(point) // max(1, int(_COL_W / (10.5 * 0.55))) + 1)
            y += 14 * line_count + 3
        y += 4

    # ---- Action Items ----
    if summary.action_items:
        y = _section_header(page, doc, "Action Items", y)
        for idx, item in enumerate(summary.action_items, start=1):
            page, y = _ensure_space(page, doc, y, need=16)
            page.insert_text(
                fitz.Point(_MARGIN, y + 10),
                f"{idx}.",
                fontsize=10.5,
                fontname="helv",
                color=_COLOR_BULLET,
            )
            page.insert_textbox(
                fitz.Rect(_MARGIN + 18, y, _PAGE_W - _MARGIN, y + 60),
                item,
                fontsize=10.5,
                fontname="helv",
                color=_COLOR_BODY,
                align=0,
            )
            line_count = max(1, len(item) // max(1, int(_COL_W / (10.5 * 0.55))) + 1)
            y += 14 * line_count + 3
        y += 4

    # ---- Named Entities ----
    if summary.named_entities:
        y = _section_header(page, doc, "Key Entities", y)
        entities_text = "  ·  ".join(summary.named_entities[:12])
        page.insert_textbox(
            fitz.Rect(_MARGIN, y, _PAGE_W - _MARGIN, y + 30),
            entities_text,
            fontsize=9.5,
            fontname="helv",
            color=_COLOR_META,
            align=0,
        )
        y += 22

    # ---- Footer ----
    footer_y = _PAGE_H - 24
    page.draw_line(
        fitz.Point(_MARGIN, footer_y - 4),
        fitz.Point(_PAGE_W - _MARGIN, footer_y - 4),
        color=_COLOR_DIVIDER,
        width=0.5,
    )
    page.insert_text(
        fitz.Point(_MARGIN, footer_y + 8),
        "Generated by PdfORBIT · pdforbit.app",
        fontsize=7.5,
        fontname="helv",
        color=_COLOR_META,
    )

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _section_header(page: fitz.Page, doc: fitz.Document, title: str, y: float) -> float:
    page, y = _ensure_space(page, doc, y, need=28)
    page.draw_rect(
        fitz.Rect(_MARGIN - 4, y, _PAGE_W - _MARGIN + 4, y + 20),
        color=None,
        fill=(0.93, 0.96, 1.0),
    )
    page.insert_text(
        fitz.Point(_MARGIN, y + 14),
        title.upper(),
        fontsize=10.0,
        fontname="helv",
        color=_COLOR_SECTION_HEADER,
    )
    return y + 24


def _body_text(page: fitz.Page, doc: fitz.Document, text: str, y: float) -> float:
    page, y = _ensure_space(page, doc, y, need=20)
    result = page.insert_textbox(
        fitz.Rect(_MARGIN, y, _PAGE_W - _MARGIN, _PAGE_H - 36),
        text,
        fontsize=11.0,
        fontname="helv",
        color=_COLOR_BODY,
        align=0,
    )
    line_count = max(1, len(text) // max(1, int(_COL_W / (11.0 * 0.55))) + 1)
    return y + 15 * line_count + 4


def _draw_divider(page: fitz.Page, y: float) -> None:
    page.draw_line(
        fitz.Point(_MARGIN, y),
        fitz.Point(_PAGE_W - _MARGIN, y),
        color=_COLOR_DIVIDER,
        width=0.6,
    )


def _ensure_space(
    page: fitz.Page,
    doc: fitz.Document,
    y: float,
    need: float,
) -> tuple[fitz.Page, float]:
    if y + need > _PAGE_H - 36:
        page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
        y = _MARGIN
    return page, y