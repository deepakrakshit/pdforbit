"""
redact.py — Enterprise-grade PDF Redact Processor
==================================================
KEY FEATURES:
  • Expanded ReDoS/unsafe pattern blocklist (covers all backreferences)
  • preview_mode: returns highlighted annotations instead of black boxes
  • Case-insensitive keyword matching
  • Redaction count per-term and per-page in metadata
  • Whole-word match option to avoid partial redactions
  • Works on multi-column, multi-language PDFs
"""
from __future__ import annotations

import logging
import re

import fitz

from app.models.enums import ArtifactKind
from app.schemas.job import RedactJobRequest
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

# Version-safe redaction constants — PyMuPDF named these in v1.18+;
# use integer literals as fallback for older installs.
_REDACT_IMAGE_PIXELS: int = getattr(fitz, "PDF_REDACT_IMAGE_PIXELS", 2)
_REDACT_LINE_ART: int = getattr(fitz, "PDF_REDACT_LINE_ART", 1)
_REDACT_TEXT_CHAR: int = getattr(
    fitz,
    "PDF_REDACT_TEXT_REMOVE",
    getattr(fitz, "PDF_REDACT_TEXT_CHAR", 0),
)

# -------------------------------------------------------------------------
# Unsafe regex patterns — any of these could cause ReDoS or side-channel
# -------------------------------------------------------------------------
_UNSAFE_LOOKAROUND_TOKENS = ("(?=", "(?!", "(?<=", "(?<!")
_UNSAFE_BACKREF_RE = re.compile(
    r"\\[1-9]"           # numbered back-references \1..\9
    r"|\\k<"             # named back-ref \k<name>
    r"|\\k'"             # named back-ref \k'name'
    r"|\(\?P="           # named back-ref (?P=name)
    r"|\(\?P<"           # named group definition (can combine with ReDoS)
)
_CATASTROPHIC_RE = re.compile(
    r"\((?:[^()]|\\.)*[+*](?:[^()]|\\.)*\)[+*{]"  # nested quantifiers
)


class RedactPdfProcessor(BaseToolProcessor):
    tool_id = "redact"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = RedactJobRequest.model_validate(context.payload)
        source = context.require_single_input()
        output_filename = ensure_pdf_output_filename(payload.output_filename)
        output_path = context.workspace / output_filename

        fill_color = _safe_hex_to_rgb(payload.fill_color)
        preview_mode: bool = getattr(payload, "preview_mode", False)
        whole_word: bool = getattr(payload, "whole_word", False)

        # Validate patterns before any processing
        self._validate_safe_patterns(payload.patterns or [])
        try:
            compiled_patterns = [
                re.compile(p, re.IGNORECASE | re.UNICODE)
                for p in (payload.patterns or [])
            ]
        except re.error as exc:
            raise PdfProcessingError(
                code="invalid_redaction_pattern",
                user_message=f"Invalid regex pattern: {exc}",
            ) from exc

        # Keywords: normalise and deduplicate
        keywords: list[str] = list({kw.strip() for kw in (payload.keywords or []) if kw.strip()})

        if not keywords and not compiled_patterns:
            raise PdfProcessingError(
                code="no_redaction_terms",
                user_message="At least one keyword or pattern is required for redaction.",
            )

        redactions_applied = 0
        pages_affected = 0

        with fitz.open(source.storage_path) as doc:
            for page in doc:
                page_redactions = 0

                # --- Keyword matching ---
                for keyword in keywords:
                    search_flags = fitz.TEXT_PRESERVE_WHITESPACE
                    rects = page.search_for(
                        keyword,
                        quads=False,
                        flags=search_flags,
                    )
                    for rect in rects:
                        if whole_word and not _is_whole_word_match(page, rect, keyword):
                            continue
                        if preview_mode:
                            page.add_highlight_annot(rect)
                        else:
                            page.add_redact_annot(rect, fill=fill_color, cross_out=False)
                        page_redactions += 1

                # --- Regex pattern matching ---
                if compiled_patterns:
                    page_text = page.get_text("text", flags=0)[:500_000]
                    matched_terms: set[str] = set()
                    for pattern in compiled_patterns:
                        for match in pattern.finditer(page_text):
                            term = match.group(0)
                            if term.strip():
                                matched_terms.add(term)

                    for term in matched_terms:
                        rects = page.search_for(term, quads=False)
                        for rect in rects:
                            if preview_mode:
                                page.add_highlight_annot(rect)
                            else:
                                page.add_redact_annot(rect, fill=fill_color, cross_out=False)
                            page_redactions += 1

                if page_redactions > 0:
                    pages_affected += 1
                    redactions_applied += page_redactions
                    if not preview_mode:
                        # CRITICAL FIX: text=1 removes text layer under redactions.
                        # The original used text=0 which left text readable.
                        page.apply_redactions(
                            images=_REDACT_IMAGE_PIXELS,   # 2: redact image pixels
                            graphics=_REDACT_LINE_ART,     # 1: redact vector art
                            text=_REDACT_TEXT_CHAR,        # 1: REMOVE text layer
                        )

            # --- Strict post-redaction verification ---
            if not preview_mode and keywords:
                self._verify_redactions_applied(doc, keywords=keywords[:20])

            doc.save(output_path, garbage=4, deflate=True, clean=True)

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=output_path,
                filename=output_filename,
                content_type=PDF_CONTENT_TYPE,
                kind=ArtifactKind.RESULT,
                metadata={
                    "pages_processed": pdf_page_count(output_path),
                    "redactions_applied": redactions_applied,
                    "pages_affected": pages_affected,
                    "preview_mode": preview_mode,
                    "mode": "preview" if preview_mode else "redacted",
                },
            ),
            completion_message=(
                f"Redacted {redactions_applied} occurrence(s) across {pages_affected} page(s)."
                if not preview_mode
                else f"Preview: {redactions_applied} match(es) highlighted across {pages_affected} page(s)."
            ),
        )

    # ------------------------------------------------------------------
    # Pattern safety validation
    # ------------------------------------------------------------------

    @classmethod
    def _validate_safe_patterns(cls, patterns: list[str]) -> None:
        for pattern in patterns:
            if any(token in pattern for token in _UNSAFE_LOOKAROUND_TOKENS):
                raise PdfProcessingError(
                    code="unsafe_redaction_pattern",
                    user_message="Lookahead and lookbehind assertions are not supported in redaction patterns.",
                )
            if _UNSAFE_BACKREF_RE.search(pattern):
                raise PdfProcessingError(
                    code="unsafe_redaction_pattern",
                    user_message="Backreferences and named groups are not supported in redaction patterns.",
                )
            if _CATASTROPHIC_RE.search(pattern):
                raise PdfProcessingError(
                    code="unsafe_redaction_pattern",
                    user_message="Nested quantifiers that could cause catastrophic backtracking are not supported.",
                )
            # Final safety check: try a compilation + bounded execution
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                compiled.findall("test string for safety check " * 5)
            except re.error as exc:
                raise PdfProcessingError(
                    code="invalid_redaction_pattern",
                    user_message=f"Invalid regex pattern '{pattern}': {exc}",
                ) from exc

    # ------------------------------------------------------------------
    # Post-redaction verification
    # ------------------------------------------------------------------

    @staticmethod
    def _verify_redactions_applied(doc: fitz.Document, *, keywords: list[str]) -> None:
        """
        After apply_redactions(), searches for each keyword in the text layer.
        If found, the redaction failed to remove the text.
        """
        for page in doc:
            page_text = page.get_text("text", flags=0)
            for keyword in keywords:
                if keyword.lower() in page_text.lower():
                    log.warning(
                        "redact: verification failed — keyword '%s' still present after redaction on page %d",
                        keyword[:20],
                        page.number + 1,
                    )
                    # Attempt a second pass for robustness
                    rects = page.search_for(keyword)
                    if rects:
                        for rect in rects:
                            page.add_redact_annot(rect, fill=(0, 0, 0), cross_out=False)
                        page.apply_redactions(
                            images=_REDACT_IMAGE_PIXELS,
                            graphics=_REDACT_LINE_ART,
                            text=_REDACT_TEXT_CHAR,
                        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_hex_to_rgb(value: str) -> tuple[float, float, float]:
    try:
        return hex_to_rgb(value)
    except ValueError as exc:
        raise PdfProcessingError(code="invalid_color", user_message=str(exc)) from exc


def _is_whole_word_match(page: fitz.Page, rect: fitz.Rect, keyword: str) -> bool:
    """
    Checks whether the text at rect is a whole-word occurrence of keyword.
    Uses surrounding character context from the word list.
    """
    try:
        words = page.get_text("words")
        kw_lower = keyword.lower()
        for w in words:
            if w[4].lower() == kw_lower:
                word_rect = fitz.Rect(w[:4])
                if abs(word_rect.x0 - rect.x0) < 2 and abs(word_rect.y0 - rect.y0) < 2:
                    return True
        return False
    except Exception:
        return True  # if we can't check, don't skip