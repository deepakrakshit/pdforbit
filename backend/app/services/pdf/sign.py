"""
sign.py — Enterprise-grade PDF Sign Processor
=============================================
Two-tier signing approach:

Tier 1 — Visual Signature Stamp (default):
  • Signature text + optional handwritten image upload
  • Automatic timestamp (ISO 8601 UTC)
  • Border style: box, underline, or none
  • Professional blue gradient background
  • Positioned within page bounds with validation

Tier 2 — Real Cryptographic Digital Signature (when use_digital_signature=True):
  • Uses pyhanko for PKCS#12 certificate-based signing
  • Produces a verifiable, tamper-evident PDF signature validated by Adobe Reader
  • PAdES / CAdES compatible signature format
  • Falls back to visual stamp gracefully if pyhanko is unavailable
"""
from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from pathlib import Path

import fitz

from app.models.enums import ArtifactKind
from app.schemas.job import SignJobRequest
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

_STAMP_BG = (0.90, 0.94, 1.00)
_STAMP_BORDER = (0.10, 0.22, 0.60)
_STAMP_TEXT_COLOR = (0.05, 0.15, 0.55)
_STAMP_LINE_COLOR = (0.10, 0.22, 0.60)


class SignPdfProcessor(BaseToolProcessor):
    tool_id = "sign"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = SignJobRequest.model_validate(context.payload)
        source = context.require_single_input()
        output_filename = ensure_pdf_output_filename(payload.output_filename)
        output_path = context.workspace / output_filename

        use_real_sig: bool = getattr(payload, "use_digital_signature", False)
        cert_password: str = getattr(payload, "cert_password", "") or ""

        # Locate optional .p12/.pfx certificate input
        cert_input = None
        if use_real_sig:
            for inp in context.inputs:
                if inp.original_filename.lower().endswith((".p12", ".pfx")):
                    cert_input = inp
                    break

        if use_real_sig and cert_input:
            try:
                _apply_real_digital_signature(
                    source_path=source.storage_path,
                    output_path=output_path,
                    cert_path=cert_input.storage_path,
                    cert_password=cert_password,
                    payload=payload,
                )
                return ProcessingResult(
                    artifact=GeneratedArtifact(
                        local_path=output_path,
                        filename=output_filename,
                        content_type=PDF_CONTENT_TYPE,
                        kind=ArtifactKind.RESULT,
                        metadata={
                            "pages_processed": pdf_page_count(output_path),
                            "signature_type": "cryptographic_pkcs12",
                            "signature_page": payload.page,
                        },
                    ),
                    completion_message="Document signed with a cryptographic digital signature.",
                )
            except ImportError:
                log.warning("sign: pyhanko not installed; falling back to visual stamp")
            except Exception as exc:
                log.warning("sign: pyhanko signing failed (%s); falling back to visual stamp", exc)

        # --- Tier 1: Visual stamp ---
        signature_text = payload.signature_text or "Signed via PdfORBIT"
        border_style: str = getattr(payload, "border_style", "box") or "box"
        include_timestamp: bool = getattr(payload, "include_timestamp", True)
        sig_image_id: str | None = getattr(payload, "signature_image_upload_id", None)

        sig_image_path: Path | None = None
        if sig_image_id:
            for inp in context.inputs:
                if inp.public_id == sig_image_id:
                    sig_image_path = inp.storage_path
                    break

        if include_timestamp:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            display_text = f"{signature_text}\n{ts}"
        else:
            display_text = signature_text

        with fitz.open(source.storage_path) as doc:
            if payload.page < 1 or payload.page > doc.page_count:
                raise PdfProcessingError(
                    code="invalid_signature_page",
                    user_message=f"Signature page must be between 1 and {doc.page_count}.",
                )
            page = doc.load_page(payload.page - 1)
            sig_rect = fitz.Rect(
                payload.x, payload.y,
                payload.x + payload.width,
                payload.y + payload.height,
            )
            _validate_rect_within_page(sig_rect, page)

            if sig_image_path and sig_image_path.exists():
                _draw_image_stamp(page, sig_rect=sig_rect, image_path=sig_image_path, opacity=0.9)
            else:
                _draw_text_stamp(page, sig_rect=sig_rect, text=display_text, border_style=border_style)

            doc.save(output_path, garbage=3, deflate=True)

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=output_path,
                filename=output_filename,
                content_type=PDF_CONTENT_TYPE,
                kind=ArtifactKind.RESULT,
                metadata={
                    "pages_processed": pdf_page_count(output_path),
                    "signature_type": "visual_stamp",
                    "signature_page": payload.page,
                    "has_timestamp": include_timestamp,
                    "has_image": bool(sig_image_path),
                },
            ),
            completion_message="Signature stamp added successfully.",
        )


# ---------------------------------------------------------------------------
# Visual stamp renderers
# ---------------------------------------------------------------------------

def _draw_text_stamp(
    page: fitz.Page,
    *,
    sig_rect: fitz.Rect,
    text: str,
    border_style: str,
) -> None:
    if border_style == "box":
        page.draw_rect(
            sig_rect,
            color=_STAMP_BORDER,
            fill=_STAMP_BG,
            overlay=True,
            width=1.5,
        )
    elif border_style == "underline":
        page.draw_line(
            fitz.Point(sig_rect.x0, sig_rect.y1),
            fitz.Point(sig_rect.x1, sig_rect.y1),
            color=_STAMP_LINE_COLOR,
            width=2.0,
        )

    inner_rect = fitz.Rect(
        sig_rect.x0 + 6, sig_rect.y0 + 6,
        sig_rect.x1 - 6, sig_rect.y1 - 6,
    )
    line_count = max(1, text.count("\n") + 1)
    font_size = max(7.0, min(14.0, (sig_rect.height - 12) / line_count * 0.75))
    page.insert_textbox(
        inner_rect,
        text,
        fontsize=font_size,
        fontname="helv",
        color=_STAMP_TEXT_COLOR,
        align=0,
        overlay=True,
    )


def _draw_image_stamp(
    page: fitz.Page,
    *,
    sig_rect: fitz.Rect,
    image_path: Path,
    opacity: float,
) -> None:
    try:
        from PIL import Image as PILImage, ImageOps, ImageEnhance

        with PILImage.open(image_path) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGBA")
            r, g, b, a = img.split()
            a = ImageEnhance.Brightness(a).enhance(opacity)
            img = PILImage.merge("RGBA", (r, g, b, a))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            page.insert_image(sig_rect, stream=buf.getvalue(), overlay=True)
    except Exception as exc:
        log.warning("sign: image stamp failed (%s), using text stamp", exc)
        _draw_text_stamp(page, sig_rect=sig_rect, text="[Signature]", border_style="box")


def _validate_rect_within_page(rect: fitz.Rect, page: fitz.Page) -> None:
    pr = page.rect
    if rect.x0 < pr.x0 - 0.5 or rect.y0 < pr.y0 - 0.5 or rect.x1 > pr.x1 + 0.5 or rect.y1 > pr.y1 + 0.5:
        raise PdfProcessingError(
            code="invalid_signature_bounds",
            user_message="Signature placement must be within the page boundaries.",
        )
    if rect.width <= 0 or rect.height <= 0:
        raise PdfProcessingError(
            code="invalid_signature_bounds",
            user_message="Signature width and height must both be positive.",
        )


# ---------------------------------------------------------------------------
# Tier 2: Real cryptographic digital signature via pyhanko
# ---------------------------------------------------------------------------

def _apply_real_digital_signature(
    *,
    source_path: Path,
    output_path: Path,
    cert_path: Path,
    cert_password: str,
    payload: SignJobRequest,
) -> None:
    """
    Signs with a PKCS#12 certificate. Produces a verifiable, tamper-evident
    digital signature that Adobe Acrobat Reader will show as valid.

    Raises ImportError if pyhanko is not installed.
    """
    from pyhanko.sign import signers, fields as sig_fields  # type: ignore
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter  # type: ignore
    from pyhanko.sign.fields import SigFieldSpec  # type: ignore

    signer = signers.SimpleSigner.load_pkcs12(
        pfx_file=str(cert_path),
        passphrase=cert_password.encode("utf-8") if cert_password else None,
    )

    sig_box = (
        payload.x,
        payload.y,
        payload.x + payload.width,
        payload.y + payload.height,
    )
    field_name = "PdfORBITSignature1"

    with open(source_path, "rb") as f_in:
        writer = IncrementalPdfFileWriter(f_in)
        try:
            sig_fields.append_signature_field(
                writer,
                sig_field_spec=SigFieldSpec(
                    field_name,
                    on_page=payload.page - 1,
                    box=sig_box,
                ),
            )
        except Exception:
            pass  # field may already exist

        meta = signers.PdfSignatureMetadata(field_name=field_name)
        with open(output_path, "wb") as f_out:
            signers.sign_pdf(
                writer,
                signature_meta=meta,
                signer=signer,
                output=f_out,
            )