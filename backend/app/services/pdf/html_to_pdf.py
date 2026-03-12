"""
html_to_pdf.py — Enterprise-grade HTML to PDF Processor
========================================================
KEY FEATURES:
  • Four-engine fallback chain:
      1. Playwright/Chromium headless — pixel-perfect CSS rendering, JS support
      2. WeasyPrint — CSS-aware, no browser dependency, fast
      3. wkhtmltopdf — widely available on Linux servers
      4. LibreOffice — handles basic HTML layouts
      5. BeautifulSoup text extraction — last resort
  • URL fetch support with timeout and scheme validation
  • CSS media=print applied for clean page layout
  • Page size (A4, Letter, A3, Legal) propagated to all engines
  • Conversion engine and source URL reported in metadata
  • SSRF protection: blocks private/internal IP ranges on URL fetch
"""
from __future__ import annotations

import ipaddress
import logging
import shutil
import socket
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from bs4 import BeautifulSoup

from app.models.enums import ArtifactKind
from app.schemas.job import HtmlToPdfJobRequest
from app.services.pdf.advanced_utils import HTML_PAGE_SIZES, pdf_page_count, write_text_pdf
from app.services.pdf.common import (
    BaseToolProcessor,
    GeneratedArtifact,
    PDF_CONTENT_TYPE,
    PdfProcessingError,
    ProcessingResult,
    ProcessorContext,
    ensure_pdf_output_filename,
)
from app.utils.libreoffice import LibreOfficeConversionError, LibreOfficeUnavailableError, convert_with_libreoffice
from app.utils.subprocesses import CommandExecutionError, run_command

log = logging.getLogger(__name__)

# Private/loopback CIDR ranges that must not be fetched (SSRF protection)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # IPv4 link-local (AWS metadata, etc.)
    ipaddress.ip_network("0.0.0.0/8"),         # "This" network
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]

_PAGE_SIZE_PLAYWRIGHT = {
    "A4":     {"width": "210mm", "height": "297mm"},
    "A3":     {"width": "297mm", "height": "420mm"},
    "Letter": {"width": "8.5in", "height": "11in"},
    "Legal":  {"width": "8.5in", "height": "14in"},
}


class HtmlToPdfProcessor(BaseToolProcessor):
    tool_id = "html2pdf"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = HtmlToPdfJobRequest.model_validate(context.payload)
        output_filename = ensure_pdf_output_filename(payload.output_filename)
        output_path = context.workspace / output_filename
        page_size = payload.page_size or "A4"

        # Resolve source HTML path
        if payload.url:
            source_path = self._download_url_html(payload.url, workspace=context.workspace)
        else:
            source_path = context.require_single_input().storage_path

        # Try each engine in order of fidelity
        engine_used, pages = self._convert(
            source_path=source_path,
            output_path=output_path,
            page_size=page_size,
            workspace=context.workspace,
        )
        log.info("html2pdf: converted using engine '%s'", engine_used)

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=output_path,
                filename=output_filename,
                content_type=PDF_CONTENT_TYPE,
                kind=ArtifactKind.RESULT,
                metadata={
                    "pages_processed": pages,
                    "conversion_engine": engine_used,
                    "source_url": payload.url,
                    "page_size": page_size,
                },
            ),
            completion_message="HTML converted to PDF successfully.",
        )

    def _convert(
        self,
        *,
        source_path: Path,
        output_path: Path,
        page_size: str,
        workspace: Path,
    ) -> tuple[str, int]:
        """Tries engines in order, returning (engine_name, page_count)."""

        # 1. Playwright
        if self._try_playwright(source_path, output_path, page_size=page_size):
            return "playwright", pdf_page_count(output_path)

        # 2. WeasyPrint
        if self._try_weasyprint(source_path, output_path, page_size=page_size):
            return "weasyprint", pdf_page_count(output_path)

        # 3. wkhtmltopdf
        if self._try_wkhtmltopdf(source_path, output_path, page_size=page_size):
            return "wkhtmltopdf", pdf_page_count(output_path)

        # 4. LibreOffice
        try:
            converted_path = convert_with_libreoffice(source_path, output_dir=output_path.parent, target_format="pdf")
            if converted_path != output_path:
                converted_path.replace(output_path)
            return "libreoffice", pdf_page_count(output_path)
        except (LibreOfficeUnavailableError, LibreOfficeConversionError):
            pass

        # 5. BeautifulSoup text extraction (last resort)
        html = source_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n", strip=True) or "(empty HTML document)"
        write_text_pdf(
            page_texts=[text],
            output_path=output_path,
            page_size=HTML_PAGE_SIZES.get(page_size, HTML_PAGE_SIZES["A4"]),
        )
        return "beautifulsoup-fallback", pdf_page_count(output_path)

    @staticmethod
    def _try_playwright(source_path: Path, output_path: Path, *, page_size: str) -> bool:
        """Attempts HTML→PDF via Playwright (headless Chromium)."""
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError:
            return False
        try:
            size = _PAGE_SIZE_PLAYWRIGHT.get(page_size, _PAGE_SIZE_PLAYWRIGHT["A4"])
            with sync_playwright() as p:
                browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
                page = browser.new_page()
                page.goto(source_path.as_uri(), wait_until="networkidle", timeout=30_000)
                page.pdf(
                    path=str(output_path),
                    width=size["width"],
                    height=size["height"],
                    print_background=True,
                    margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"},
                )
                browser.close()
            return output_path.exists() and output_path.stat().st_size > 0
        except Exception as exc:
            log.debug("html2pdf: playwright failed: %s", exc)
            if output_path.exists():
                output_path.unlink()
            return False

    @staticmethod
    def _try_weasyprint(source_path: Path, output_path: Path, *, page_size: str) -> bool:
        """Attempts HTML→PDF via WeasyPrint (CSS-aware, no browser)."""
        try:
            from weasyprint import HTML, CSS  # type: ignore
        except ImportError:
            return False
        try:
            css_override = CSS(string=f"@page {{ size: {page_size}; margin: 15mm; }}")
            HTML(filename=str(source_path)).write_pdf(str(output_path), stylesheets=[css_override])
            return output_path.exists() and output_path.stat().st_size > 0
        except Exception as exc:
            log.debug("html2pdf: weasyprint failed: %s", exc)
            if output_path.exists():
                output_path.unlink()
            return False

    @staticmethod
    def _try_wkhtmltopdf(source_path: Path, output_path: Path, *, page_size: str) -> bool:
        """Attempts HTML→PDF via wkhtmltopdf subprocess."""
        wk_bin = shutil.which("wkhtmltopdf")
        if not wk_bin:
            return False
        try:
            run_command(
                [
                    wk_bin,
                    "--quiet",
                    "--page-size", page_size,
                    "--margin-top", "15mm",
                    "--margin-bottom", "15mm",
                    "--margin-left", "15mm",
                    "--margin-right", "15mm",
                    "--enable-local-file-access",
                    "--load-error-handling", "ignore",
                    str(source_path),
                    str(output_path),
                ],
                timeout_seconds=120,
            )
            return output_path.exists() and output_path.stat().st_size > 0
        except (CommandExecutionError, Exception) as exc:
            log.debug("html2pdf: wkhtmltopdf failed: %s", exc)
            if output_path.exists():
                output_path.unlink()
            return False

    # ------------------------------------------------------------------
    # URL fetching with SSRF protection
    # ------------------------------------------------------------------

    @staticmethod
    def _download_url_html(url: str, *, workspace: Path) -> Path:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise PdfProcessingError(
                code="invalid_html_url",
                user_message="HTML source URL must use http or https.",
            )

        # SSRF protection: resolve hostname and block private IPs
        hostname = parsed.hostname or ""
        try:
            resolved_ip = socket.gethostbyname(hostname)
            addr = ipaddress.ip_address(resolved_ip)
            for blocked in _BLOCKED_NETWORKS:
                if addr in blocked:
                    raise PdfProcessingError(
                        code="blocked_html_url",
                        user_message="The requested URL resolves to a private or internal address.",
                    )
        except PdfProcessingError:
            raise
        except Exception:
            pass  # DNS resolution failure will surface during fetch

        try:
            with urlopen(url, timeout=20) as response:
                content_type = response.headers.get("Content-Type", "")
                if "html" not in content_type.lower() and "text" not in content_type.lower():
                    log.warning("html2pdf: URL returned non-HTML content type: %s", content_type)
                html = response.read().decode("utf-8", errors="ignore")
        except PdfProcessingError:
            raise
        except Exception as exc:
            raise PdfProcessingError(
                code="html_fetch_failed",
                user_message="Unable to fetch the requested URL. Check that it is publicly accessible.",
            ) from exc

        source_path = workspace / "remote-source.html"
        source_path.write_text(html, encoding="utf-8")
        return source_path