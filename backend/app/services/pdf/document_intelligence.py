from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.services.pdf.advanced_utils import render_page_to_pil
from app.services.pdf.common import PdfProcessingError
from app.utils.subprocesses import CommandExecutionError, run_command

OCR_LANGUAGE_MAP = {
    "ar": "ara",
    "de": "deu",
    "en": "eng",
    "es": "spa",
    "fr": "fra",
    "hi": "hin",
    "it": "ita",
    "ja": "jpn",
    "ko": "kor",
    "nl": "nld",
    "pl": "pol",
    "pt": "por",
    "ru": "rus",
    "tr": "tur",
    "zh": "chi_sim",
}


@dataclass(frozen=True)
class ExtractedPdfPage:
    page_number: int
    text: str
    extraction_mode: str
    native_char_count: int
    ocr_char_count: int


@dataclass(frozen=True)
class ExtractedPdfDocument:
    pages: list[ExtractedPdfPage]

    @property
    def page_texts(self) -> list[str]:
        return [page.text for page in self.pages]

    @property
    def pages_processed(self) -> int:
        return len(self.pages)

    @property
    def combined_text(self) -> str:
        return "\n\n".join(text for text in self.page_texts if text.strip())

    @property
    def word_count(self) -> int:
        return len(self.combined_text.split())

    @property
    def ocr_pages(self) -> int:
        return sum(1 for page in self.pages if "ocr" in page.extraction_mode)


class DocumentTextExtractor:
    def __init__(self, *, tesseract_bin: str, timeout_seconds: int, render_dpi: int) -> None:
        self._tesseract_bin = tesseract_bin
        self._timeout_seconds = timeout_seconds
        self._render_dpi = render_dpi

    def extract_pdf(self, file_path: str | bytes | fitz.Document | object, *, source_language: str | None) -> ExtractedPdfDocument:
        pages: list[ExtractedPdfPage] = []
        ocr_language = self._resolve_ocr_language(source_language)

        try:
            with fitz.open(file_path) as document:
                for index, page in enumerate(document, start=1):
                    native_text = self._clean_text(page.get_text("text"))
                    should_run_ocr = len(native_text) < 120 or (bool(page.get_images(full=True)) and len(native_text) < 500)
                    ocr_text = ""
                    if should_run_ocr:
                        ocr_text = self._extract_page_ocr(page=page, language=ocr_language)
                    merged_text = self._merge_text(native_text=native_text, ocr_text=ocr_text)
                    extraction_mode = self._resolve_extraction_mode(native_text=native_text, ocr_text=ocr_text)
                    pages.append(
                        ExtractedPdfPage(
                            page_number=index,
                            text=merged_text,
                            extraction_mode=extraction_mode,
                            native_char_count=len(native_text),
                            ocr_char_count=len(ocr_text),
                        )
                    )
        except PdfProcessingError:
            raise
        except Exception as exc:
            raise PdfProcessingError(
                code="text_extraction_failed",
                user_message="Unable to extract text from the uploaded PDF.",
            ) from exc

        return ExtractedPdfDocument(pages=pages)

    def _extract_page_ocr(self, *, page: fitz.Page, language: str) -> str:
        image = render_page_to_pil(page, dpi=self._render_dpi)
        variants = self._prepare_images(image)
        candidates: list[str] = []

        for variant in variants:
            for config in ("--oem 3 --psm 6", "--oem 1 --psm 11"):
                text = self._run_tesseract(variant, language=language, config=config)
                if text:
                    candidates.append(text)
                    if self._score_text(text)[0] >= 40:
                        return text

        if not candidates:
            return ""
        return max(candidates, key=self._score_text)

    def _run_tesseract(self, image: Image.Image, *, language: str, config: str) -> str:
        with TemporaryDirectory(prefix="pdforbit-ocr-") as temp_dir:
            directory = Path(temp_dir)
            image_path = directory / "page.png"
            output_base = directory / "ocr-output"
            image.save(image_path, format="PNG")

            try:
                run_command(
                    [
                        self._tesseract_bin,
                        str(image_path),
                        str(output_base),
                        "-l",
                        language,
                        *config.split(),
                    ],
                    timeout_seconds=self._timeout_seconds,
                )
            except CommandExecutionError as exc:
                stderr = exc.stderr.lower()
                if "timed out" in str(exc).lower():
                    raise PdfProcessingError(
                        code="ocr_timeout",
                        user_message="OCR processing took too long for this PDF.",
                    ) from exc
                if "failed loading language" in stderr or "error opening data file" in stderr:
                    raise PdfProcessingError(
                        code="ocr_language_unavailable",
                        user_message="The required OCR language data is not installed on the server.",
                    ) from exc
                if "command not found" in str(exc).lower():
                    raise PdfProcessingError(
                        code="ocr_unavailable",
                        user_message="OCR processing is not available on this server.",
                    ) from exc
                raise PdfProcessingError(
                    code="ocr_unavailable",
                    user_message="OCR processing failed while reading the PDF.",
                ) from exc

            output_path = output_base.with_suffix(".txt")
            if not output_path.exists():
                return ""
            return self._clean_text(output_path.read_text(encoding="utf-8", errors="ignore"))

    @staticmethod
    def _prepare_images(image: Image.Image) -> list[Image.Image]:
        grayscale = ImageOps.grayscale(image)
        contrast = ImageOps.autocontrast(grayscale)
        denoised = contrast.filter(ImageFilter.MedianFilter(size=3))
        sharpened = ImageEnhance.Sharpness(denoised).enhance(2.0)
        binary = sharpened.point(lambda value: 255 if value > 150 else 0)
        return [contrast, binary]

    @staticmethod
    def _clean_text(text: str) -> str:
        lines = [" ".join(segment.split()) for segment in text.replace("\r", "").splitlines()]
        return "\n".join(line for line in lines if line).strip()

    def _resolve_ocr_language(self, source_language: str | None) -> str:
        mapped = OCR_LANGUAGE_MAP.get((source_language or "").lower(), "eng")
        if mapped == "eng":
            return "eng+osd"
        return f"{mapped}+eng+osd"

    @staticmethod
    def _merge_text(*, native_text: str, ocr_text: str) -> str:
        if native_text and ocr_text:
            if DocumentTextExtractor._normalize_for_compare(native_text) == DocumentTextExtractor._normalize_for_compare(ocr_text):
                return native_text
            return f"{native_text}\n\n{ocr_text}".strip()
        return native_text or ocr_text

    @staticmethod
    def _normalize_for_compare(text: str) -> str:
        return "".join(character for character in text.lower() if character.isalnum())

    @staticmethod
    def _resolve_extraction_mode(*, native_text: str, ocr_text: str) -> str:
        if native_text and ocr_text:
            return "native+ocr"
        if ocr_text:
            return "ocr"
        if native_text:
            return "native"
        return "empty"

    @staticmethod
    def _score_text(text: str) -> tuple[int, int]:
        words = [word for word in text.split() if word]
        return (len(words), len(text))