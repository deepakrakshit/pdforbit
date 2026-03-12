"""
compress.py — Enterprise-grade PDF Compress Processor
======================================================
KEY FEATURES:
  • Ghostscript primary path with 3 finely-tuned compression profiles
  • pikepdf fallback (no GS dependency required)
  • GS FastWebView (-dFastWebView) for linearized web-delivery
  • Negative savings protection (already-optimized detection)
  • Savings clamped to [0, 100] with already_optimized flag
  • Technique reported in metadata (ghostscript / pikepdf)
  • Input size guard: if compressed > original, returns original
  • All compression parameters fully documented
"""
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pikepdf

from app.models.enums import ArtifactKind
from app.schemas.job import CompressJobRequest
from app.services.pdf.common import (
    BaseToolProcessor,
    GeneratedArtifact,
    PDF_CONTENT_TYPE,
    PdfProcessingError,
    ProcessingResult,
    ProcessorContext,
    ensure_pdf_output_filename,
    open_pdf,
)
from app.utils.pdf_validation import extract_pdf_metadata
from app.utils.subprocesses import CommandExecutionError, run_command

log = logging.getLogger(__name__)

GHOSTSCRIPT_COMMAND_CANDIDATES = ("gswin64c", "gswin32c", "gs")


@dataclass(frozen=True)
class CompressionProfile:
    pdf_settings: str
    color_resolution: int
    gray_resolution: int
    mono_resolution: int
    jpeg_quality: int
    fallback_linearize: bool
    fallback_recompress_flate: bool
    fallback_use_object_streams: bool


COMPRESSION_PROFILES: dict[str, CompressionProfile] = {
    "low": CompressionProfile(
        pdf_settings="screen",
        color_resolution=72,
        gray_resolution=72,
        mono_resolution=144,
        jpeg_quality=40,
        fallback_linearize=False,
        fallback_recompress_flate=True,
        fallback_use_object_streams=True,
    ),
    "medium": CompressionProfile(
        pdf_settings="ebook",
        color_resolution=110,
        gray_resolution=110,
        mono_resolution=180,
        jpeg_quality=65,
        fallback_linearize=True,
        fallback_recompress_flate=True,
        fallback_use_object_streams=True,
    ),
    "high": CompressionProfile(
        pdf_settings="printer",
        color_resolution=200,
        gray_resolution=200,
        mono_resolution=300,
        jpeg_quality=90,
        fallback_linearize=True,
        fallback_recompress_flate=False,
        fallback_use_object_streams=False,
    ),
}


class CompressPdfProcessor(BaseToolProcessor):
    tool_id = "compress"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = CompressJobRequest.model_validate(context.payload)
        source = context.require_single_input()
        output_filename = ensure_pdf_output_filename(payload.output_filename)
        output_path = context.workspace / output_filename

        page_count, technique = self._compress_pdf(
            source_path=source.storage_path,
            output_path=output_path,
            level=payload.level,
        )

        compressed_bytes = output_path.stat().st_size
        original_bytes = source.size_bytes
        raw_savings = (1.0 - (compressed_bytes / original_bytes)) * 100.0 if original_bytes > 0 else 0.0
        savings_pct = round(max(0.0, raw_savings), 2)
        already_optimized = compressed_bytes >= original_bytes

        # If compression made it larger, return original to avoid harm
        if already_optimized and compressed_bytes > original_bytes:
            import shutil as _shutil
            _shutil.copy2(source.storage_path, output_path)
            compressed_bytes = original_bytes
            savings_pct = 0.0
            log.info("compress: output larger than input; returning original (level=%s)", payload.level)

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=output_path,
                filename=output_filename,
                content_type=PDF_CONTENT_TYPE,
                kind=ArtifactKind.RESULT,
                metadata={
                    "pages_processed": page_count,
                    "original_bytes": original_bytes,
                    "compressed_bytes": compressed_bytes,
                    "savings_pct": savings_pct,
                    "already_optimized": already_optimized,
                    "compression_level": payload.level,
                    "technique": technique,
                },
            ),
            completion_message=(
                f"Compressed successfully. Saved {savings_pct:.1f}% "
                f"({original_bytes - compressed_bytes:,} bytes)."
                if not already_optimized
                else "File is already optimally compressed."
            ),
        )

    def _compress_pdf(
        self, *, source_path: Path, output_path: Path, level: str
    ) -> tuple[int, str]:
        """Returns (page_count, technique_used)."""
        with open_pdf(source_path) as src:
            page_count = len(src.pages)

        ghostscript_bin = self._resolve_ghostscript_command()
        if ghostscript_bin is not None:
            try:
                self._compress_with_ghostscript(
                    ghostscript_bin=ghostscript_bin,
                    source_path=source_path,
                    output_path=output_path,
                    level=level,
                )
                self._validate_output(output_path)
                log.debug("compress: ghostscript succeeded (level=%s)", level)
                return page_count, "ghostscript"
            except (CommandExecutionError, PdfProcessingError) as exc:
                if output_path.exists():
                    output_path.unlink()
                log.warning("compress: ghostscript failed, falling back to pikepdf: %s", exc)

        # pikepdf fallback
        with open_pdf(source_path) as src:
            src.save(output_path, **self._fallback_compression_kwargs(level))
        self._validate_output(output_path)
        log.debug("compress: pikepdf fallback used (level=%s)", level)
        return page_count, "pikepdf"

    @staticmethod
    def _resolve_ghostscript_command() -> str | None:
        for candidate in GHOSTSCRIPT_COMMAND_CANDIDATES:
            path = shutil.which(candidate)
            if path:
                return path
        return None

    @staticmethod
    def _compression_profile(level: str) -> CompressionProfile:
        return COMPRESSION_PROFILES.get(level, COMPRESSION_PROFILES["medium"])

    def _compress_with_ghostscript(
        self,
        *,
        ghostscript_bin: str,
        source_path: Path,
        output_path: Path,
        level: str,
    ) -> None:
        profile = self._compression_profile(level)
        run_command(
            [
                ghostscript_bin,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.7",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                "-dSAFER",
                "-dFastWebView=true",          # linearize for web delivery
                "-dDetectDuplicateImages=true",
                "-dCompressFonts=true",
                "-dSubsetFonts=true",
                "-dEmbedAllFonts=true",
                "-dAutoFilterColorImages=false",
                "-dAutoFilterGrayImages=false",
                "-dColorImageFilter=/DCTEncode",
                "-dGrayImageFilter=/DCTEncode",
                "-dMonoImageFilter=/CCITTFaxEncode",
                "-dColorImageDownsampleType=/Bicubic",
                "-dGrayImageDownsampleType=/Bicubic",
                "-dMonoImageDownsampleType=/Subsample",
                "-dDownsampleColorImages=true",
                "-dDownsampleGrayImages=true",
                "-dDownsampleMonoImages=true",
                f"-dJPEGQ={profile.jpeg_quality}",
                f"-dColorImageResolution={profile.color_resolution}",
                f"-dGrayImageResolution={profile.gray_resolution}",
                f"-dMonoImageResolution={profile.mono_resolution}",
                f"-dPDFSETTINGS=/{profile.pdf_settings}",
                f"-sOutputFile={output_path}",
                str(source_path),
            ],
            timeout_seconds=300,
        )

    @staticmethod
    def _fallback_compression_kwargs(level: str) -> dict[str, Any]:
        profile = CompressPdfProcessor._compression_profile(level)
        kwargs: dict[str, Any] = {"compress_streams": True}
        kwargs["recompress_flate"] = profile.fallback_recompress_flate
        kwargs["linearize"] = profile.fallback_linearize
        if profile.fallback_use_object_streams:
            kwargs["object_stream_mode"] = pikepdf.ObjectStreamMode.generate
        return kwargs

    @staticmethod
    def _validate_output(output_path: Path) -> None:
        if not output_path.exists() or output_path.stat().st_size <= 0:
            raise PdfProcessingError(
                code="compression_failed",
                user_message="Compression did not produce a usable PDF output.",
            )
        extract_pdf_metadata(output_path)