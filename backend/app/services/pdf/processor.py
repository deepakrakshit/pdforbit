from __future__ import annotations

from collections.abc import Callable

from app.core.config import AppSettings
from app.schemas.job import TOOL_PAYLOAD_MODELS
from app.services.pdf.common import BaseToolProcessor, PdfProcessingError, ProcessingResult, ProcessorContext
from app.services.pdf.compare import ComparePdfProcessor
from app.services.pdf.compress import CompressPdfProcessor
from app.services.pdf.crop import CropPdfProcessor
from app.services.pdf.excel_to_pdf import ExcelToPdfProcessor
from app.services.pdf.extract import ExtractPdfProcessor
from app.services.pdf.html_to_pdf import HtmlToPdfProcessor
from app.services.pdf.image_to_pdf import ImageToPdfProcessor
from app.services.pdf.merge import MergePdfProcessor
from app.services.pdf.ocr import OcrPdfProcessor
from app.services.pdf.page_numbers import PageNumbersPdfProcessor
from app.services.pdf.pdf_to_excel import PdfToExcelProcessor
from app.services.pdf.pdf_to_image import PdfToImageProcessor
from app.services.pdf.pdf_to_pdfa import PdfToPdfaProcessor
from app.services.pdf.pdf_to_powerpoint import PdfToPowerPointProcessor
from app.services.pdf.pdf_to_word import PdfToWordProcessor
from app.services.pdf.powerpoint_to_pdf import PowerPointToPdfProcessor
from app.services.pdf.protect import ProtectPdfProcessor
from app.services.pdf.redact import RedactPdfProcessor
from app.services.pdf.document_intelligence import DocumentTextExtractor
from app.services.pdf.editor_apply import ApplyPdfEditorChangesProcessor
from app.services.pdf.remove_pages import RemovePagesPdfProcessor
from app.services.pdf.reorder import ReorderPdfProcessor
from app.services.pdf.repair import RepairPdfProcessor
from app.services.pdf.rotate import RotatePdfProcessor
from app.services.pdf.sign import SignPdfProcessor
from app.services.pdf.split import SplitPdfProcessor
from app.services.pdf.summarize import SummarizePdfProcessor
from app.services.pdf.translate import TranslatePdfProcessor
from app.services.pdf.unlock import UnlockPdfProcessor
from app.services.pdf.watermark import WatermarkPdfProcessor
from app.services.pdf.word_to_pdf import WordToPdfProcessor
from app.services.translation_service import TranslationService


ProcessorFactory = Callable[[AppSettings], BaseToolProcessor]


def _build_processor_factories() -> dict[str, ProcessorFactory]:
    return {
        "merge": lambda settings: MergePdfProcessor(),
        "split": lambda settings: SplitPdfProcessor(),
        "extract": lambda settings: ExtractPdfProcessor(),
        "remove": lambda settings: RemovePagesPdfProcessor(),
        "reorder": lambda settings: ReorderPdfProcessor(),
        "compress": lambda settings: CompressPdfProcessor(),
        "repair": lambda settings: RepairPdfProcessor(),
        "rotate": lambda settings: RotatePdfProcessor(),
        "editor_apply": lambda settings: ApplyPdfEditorChangesProcessor(),
        "unlock": lambda settings: UnlockPdfProcessor(),
        "protect": lambda settings: ProtectPdfProcessor(),
        "watermark": lambda settings: WatermarkPdfProcessor(),
        "pagenums": lambda settings: PageNumbersPdfProcessor(),
        "crop": lambda settings: CropPdfProcessor(),
        "sign": lambda settings: SignPdfProcessor(),
        "redact": lambda settings: RedactPdfProcessor(),
        "ocr": lambda settings: OcrPdfProcessor(
            tesseract_bin=settings.tesseract_bin,
            timeout_seconds=settings.ocr_timeout_seconds,
        ),
        "compare": lambda settings: ComparePdfProcessor(render_dpi=settings.pdf_render_dpi),
        "img2pdf": lambda settings: ImageToPdfProcessor(),
        "word2pdf": lambda settings: WordToPdfProcessor(),
        "excel2pdf": lambda settings: ExcelToPdfProcessor(),
        "ppt2pdf": lambda settings: PowerPointToPdfProcessor(),
        "html2pdf": lambda settings: HtmlToPdfProcessor(),
        "pdf2img": lambda settings: PdfToImageProcessor(),
        "pdf2word": lambda settings: PdfToWordProcessor(),
        "pdf2excel": lambda settings: PdfToExcelProcessor(),
        "pdf2ppt": lambda settings: PdfToPowerPointProcessor(),
        "pdf2pdfa": lambda settings: PdfToPdfaProcessor(),
        "translate": lambda settings: TranslatePdfProcessor(
            TranslationService(settings),
            extractor=DocumentTextExtractor(
                tesseract_bin=settings.tesseract_bin,
                timeout_seconds=settings.ocr_timeout_seconds,
                render_dpi=settings.intelligence_ocr_dpi,
            ),
            chunk_chars=settings.intelligence_chunk_chars,
        ),
        "summarize": lambda settings: SummarizePdfProcessor(
            TranslationService(settings),
            extractor=DocumentTextExtractor(
                tesseract_bin=settings.tesseract_bin,
                timeout_seconds=settings.ocr_timeout_seconds,
                render_dpi=settings.intelligence_ocr_dpi,
            ),
            chunk_chars=settings.intelligence_summary_chunk_chars,
        ),
    }


class PdfJobProcessor:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._factories = _build_processor_factories()
        self._processors: dict[str, BaseToolProcessor] = {}
        self._validate_registry()

    def process(self, context: ProcessorContext) -> ProcessingResult:
        processor = self._get_processor(context.tool_id)
        if processor is not None:
            return processor.process(context)
        raise PdfProcessingError(
            code="tool_not_implemented",
            user_message="This PDF tool is not implemented yet.",
        )

    def _get_processor(self, tool_id: str) -> BaseToolProcessor | None:
        if tool_id in self._processors:
            return self._processors[tool_id]

        factory = self._factories.get(tool_id)
        if factory is None:
            return None

        processor = factory(self._settings)
        if not processor.supports(tool_id):
            raise RuntimeError(f"Processor registry mismatch for tool '{tool_id}'.")
        self._processors[tool_id] = processor
        return processor

    def _validate_registry(self) -> None:
        missing_processors = sorted(set(TOOL_PAYLOAD_MODELS) - set(self._factories))
        if missing_processors:
            raise RuntimeError(f"Missing PDF processors for tools: {', '.join(missing_processors)}")
