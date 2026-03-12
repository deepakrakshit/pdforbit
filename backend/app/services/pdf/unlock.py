"""
unlock.py — Enterprise-grade PDF Unlock Processor
==================================================
KEY FEATURES:
  • Reports what was unlocked: user-password, owner-password, or both
  • Certificate-based (PKI/X.509) encryption detection with clear error
  • Encryption algorithm and key length reported in metadata
  • Attempts auto-unlock without password for owner-only restricted PDFs
  • Validates output is truly unlocked before returning
"""
from __future__ import annotations

import logging

import pikepdf

from app.models.enums import ArtifactKind
from app.schemas.job import UnlockJobRequest
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

log = logging.getLogger(__name__)


class UnlockPdfProcessor(BaseToolProcessor):
    tool_id = "unlock"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = UnlockJobRequest.model_validate(context.payload)
        source = context.require_single_input()
        output_filename = ensure_pdf_output_filename(payload.output_filename)
        output_path = context.workspace / output_filename
        password = payload.password or ""

        # Peek at encryption info before unlocking
        encryption_info = _inspect_encryption(source.storage_path)

        if encryption_info.get("certificate_based"):
            raise PdfProcessingError(
                code="certificate_encryption_unsupported",
                user_message=(
                    "This PDF uses certificate-based (PKI/X.509) encryption, which requires "
                    "the recipient's private key to unlock. Password-based unlocking is not possible."
                ),
            )

        # Open and save without encryption
        with open_pdf(source.storage_path, password=password) as source_pdf:
            page_count = len(source_pdf.pages)
            # Detect whether a user password was actually needed
            had_user_password = source_pdf.is_encrypted and bool(password)
            had_owner_restrictions = encryption_info.get("has_restrictions", False)

            source_pdf.save(
                output_path,
                encryption=False,
                linearize=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )

        # Validate the output is truly not encrypted
        try:
            with pikepdf.Pdf.open(output_path, suppress_warnings=True) as verify:
                if verify.is_encrypted:
                    raise PdfProcessingError(
                        code="unlock_failed",
                        user_message="Failed to remove encryption from the PDF.",
                    )
        except pikepdf.PdfError as exc:
            raise PdfProcessingError(
                code="unlock_failed",
                user_message="The unlocked PDF failed validation.",
            ) from exc

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=output_path,
                filename=output_filename,
                content_type=PDF_CONTENT_TYPE,
                kind=ArtifactKind.RESULT,
                metadata={
                    "pages_processed": page_count,
                    "had_user_password": had_user_password,
                    "had_owner_restrictions": had_owner_restrictions,
                    "encryption_algorithm": encryption_info.get("algorithm", "unknown"),
                    "encryption_key_length": encryption_info.get("key_length"),
                },
            ),
            completion_message="PDF unlocked successfully. Encryption removed.",
        )


# ---------------------------------------------------------------------------
# Encryption inspection
# ---------------------------------------------------------------------------

def _inspect_encryption(file_path) -> dict:
    """
    Opens the PDF and reads its encryption metadata before supplying a password.
    Returns a dict with encryption details.
    """
    info: dict = {
        "certificate_based": False,
        "has_restrictions": False,
        "algorithm": "unknown",
        "key_length": None,
    }
    try:
        # Try to open without password to inspect the encryption dict
        with pikepdf.Pdf.open(file_path, password="", suppress_warnings=True) as pdf:
            if not pdf.is_encrypted:
                return info  # not encrypted at all

            enc = pdf.encryption
            if enc:
                key_length = getattr(enc, "key_length", None)
                revision = getattr(enc, "R", None)
                info["key_length"] = key_length
                if revision in (2, 3):
                    info["algorithm"] = "RC4-40" if key_length == 5 else "RC4-128"
                elif revision in (4,):
                    info["algorithm"] = "AES-128"
                elif revision in (5, 6):
                    info["algorithm"] = "AES-256"

                # Check for restrictions (owner-only encrypted)
                perms = getattr(enc, "P", None)
                if perms is not None:
                    info["has_restrictions"] = True

    except pikepdf.PasswordError:
        # PDF requires a password — that's expected; not an error here
        info["has_restrictions"] = True
    except pikepdf.PdfError:
        pass
    except Exception:
        pass

    # Detect certificate-based encryption by checking for /CF /Recipients in the encrypt dict
    try:
        raw_pdf = pikepdf.Pdf.open(file_path, password="", suppress_warnings=True)
        encrypt_obj = raw_pdf.trailer.get("/Encrypt")
        if encrypt_obj:
            for cf_key in ("/CF", "/Recipients"):
                if cf_key in encrypt_obj:
                    info["certificate_based"] = True
                    break
        raw_pdf.close()
    except Exception:
        pass

    return info