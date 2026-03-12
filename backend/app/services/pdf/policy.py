from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from app.core.config import AppSettings
from app.schemas.job import HtmlToPdfJobRequest, OcrJobRequest, PdfToImageJobRequest, SplitJobRequest
from app.services.pdf.common import PdfProcessingError, ProcessorContext, parse_split_ranges

MB = 1024 * 1024


@dataclass(frozen=True)
class ToolExecutionPolicy:
    max_inputs: int = 50
    max_total_input_bytes: int | None = None
    max_total_input_pages: int | None = None
    max_output_parts: int | None = None
    max_render_dpi: int | None = None
    allow_encrypted_inputs: bool = False


def build_execution_policies(settings: AppSettings) -> dict[str, ToolExecutionPolicy]:
    shared_limit_bytes = max(settings.user_max_upload_mb, settings.guest_max_upload_mb) * MB * 4
    default_policy = ToolExecutionPolicy(
        max_inputs=50,
        max_total_input_bytes=shared_limit_bytes,
        max_total_input_pages=5000,
        max_output_parts=2000,
        max_render_dpi=max(settings.pdf_render_dpi, 600),
        allow_encrypted_inputs=False,
    )
    return {
        "*": default_policy,
        "merge": ToolExecutionPolicy(max_inputs=50, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=8000, max_output_parts=1),
        "split": ToolExecutionPolicy(max_inputs=1, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=4000, max_output_parts=500),
        "extract": ToolExecutionPolicy(max_inputs=1, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=4000, max_output_parts=1),
        "remove": ToolExecutionPolicy(max_inputs=1, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=4000, max_output_parts=1),
        "reorder": ToolExecutionPolicy(max_inputs=1, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=4000, max_output_parts=1),
        "compress": ToolExecutionPolicy(max_inputs=1, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=4000, max_output_parts=1),
        "repair": ToolExecutionPolicy(max_inputs=1, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=4000, max_output_parts=1),
        "ocr": ToolExecutionPolicy(max_inputs=1, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=500, max_output_parts=1, max_render_dpi=600),
        "pdf2img": ToolExecutionPolicy(max_inputs=1, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=500, max_output_parts=500, max_render_dpi=600),
        "compare": ToolExecutionPolicy(max_inputs=2, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=250, max_output_parts=750, max_render_dpi=max(settings.pdf_render_dpi, 300)),
        "translate": ToolExecutionPolicy(max_inputs=1, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=1000, max_output_parts=1, max_render_dpi=600),
        "summarize": ToolExecutionPolicy(max_inputs=1, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=1000, max_output_parts=1, max_render_dpi=600),
        "unlock": ToolExecutionPolicy(max_inputs=1, max_total_input_bytes=shared_limit_bytes, max_total_input_pages=4000, max_output_parts=1, allow_encrypted_inputs=True),
    }


def validate_processing_context(context: ProcessorContext, *, settings: AppSettings) -> ToolExecutionPolicy:
    policies = build_execution_policies(settings)
    policy = policies.get(context.tool_id, policies["*"])

    if context.tool_id == "html2pdf":
        payload = HtmlToPdfJobRequest.model_validate(context.payload)
        if payload.url and not context.inputs:
            return policy

    if not context.inputs:
        raise PdfProcessingError(
            code="missing_job_input",
            user_message="At least one uploaded source file is required.",
        )

    if len(context.inputs) > policy.max_inputs:
        raise PdfProcessingError(
            code="too_many_job_inputs",
            user_message=f"This tool accepts at most {policy.max_inputs} uploaded file(s) per job.",
        )

    total_input_bytes = sum(max(item.size_bytes, 0) for item in context.inputs)
    if policy.max_total_input_bytes is not None and total_input_bytes > policy.max_total_input_bytes:
        raise PdfProcessingError(
            code="input_size_limit_exceeded",
            user_message="The uploaded files are too large for this processing workflow.",
        )

    if not policy.allow_encrypted_inputs and any(item.is_encrypted for item in context.inputs):
        raise PdfProcessingError(
            code="encrypted_pdf_unsupported",
            user_message="This tool cannot process encrypted PDFs. Unlock the file first and try again.",
        )

    known_page_counts = [page_count for page_count in (item.page_count for item in context.inputs) if page_count is not None]
    total_known_pages = sum(known_page_counts)
    if policy.max_total_input_pages is not None and total_known_pages and total_known_pages > policy.max_total_input_pages:
        raise PdfProcessingError(
            code="page_limit_exceeded",
            user_message="This PDF job exceeds the supported page count for this tool.",
        )

    if context.tool_id == "ocr":
        payload = OcrJobRequest.model_validate(context.payload)
        _validate_render_dpi(payload.dpi, policy=policy)
    elif context.tool_id == "pdf2img":
        payload = PdfToImageJobRequest.model_validate(context.payload)
        _validate_render_dpi(payload.dpi, policy=policy)
        if policy.max_output_parts is not None and total_known_pages and total_known_pages > policy.max_output_parts:
            raise PdfProcessingError(
                code="output_limit_exceeded",
                user_message="This PDF would generate too many output files for one job.",
            )
    elif context.tool_id == "split":
        payload = SplitJobRequest.model_validate(context.payload)
        source = context.require_single_input()
        if source.page_count is not None:
            if payload.mode == "by_range":
                part_count = len(parse_split_ranges(payload.ranges or "", page_count=source.page_count))
            else:
                part_count = ceil(source.page_count / max(payload.every_n_pages or 1, 1))
            if policy.max_output_parts is not None and part_count > policy.max_output_parts:
                raise PdfProcessingError(
                    code="output_limit_exceeded",
                    user_message="This split request would generate too many output files for one job.",
                )

    return policy


def _validate_render_dpi(dpi: int, *, policy: ToolExecutionPolicy) -> None:
    if policy.max_render_dpi is not None and dpi > policy.max_render_dpi:
        raise PdfProcessingError(
            code="invalid_render_dpi",
            user_message=f"The requested DPI exceeds the supported limit of {policy.max_render_dpi}.",
        )