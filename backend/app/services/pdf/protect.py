"""
protect.py — Enterprise-grade PDF Protect Processor
=====================================================
KEY FEATURES:
  • AES-256 encryption by default (not AES-128)
  • Cryptographically random fallback owner password (not hardcoded)
  • Full granular permissions: print, copy, annotate, form fill
  • Separate user and owner password support
  • Permission summary in metadata for audit trail
  • Validates the output is openable with the user password before returning
"""
from __future__ import annotations

import logging
import secrets

import pikepdf

from app.models.enums import ArtifactKind
from app.schemas.job import ProtectJobRequest
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


class ProtectPdfProcessor(BaseToolProcessor):
    tool_id = "protect"

    def process(self, context: ProcessorContext) -> ProcessingResult:
        payload = ProtectJobRequest.model_validate(context.payload)
        source = context.require_single_input()
        output_filename = ensure_pdf_output_filename(payload.output_filename)
        output_path = context.workspace / output_filename

        # SECURITY FIX: always use a cryptographically random owner password
        # if the user hasn't specified one.
        owner_password: str = payload.owner_password or secrets.token_urlsafe(32)
        user_password: str = payload.user_password or ""

        # Map encryption bit-length to pikepdf revision
        # R=6 → AES-256 (PDF 1.7 extension), R=4 → AES-128 (PDF 1.4)
        encryption_revision = 6 if payload.encryption == 256 else 4

        permissions = pikepdf.Permissions(
            accessibility=True,           # always allow screen readers
            extract=payload.allow_copying,
            modify_annotation=payload.allow_annotations,
            modify_form=payload.allow_form_filling,
            print_lowres=payload.allow_printing,
            print_highres=payload.allow_printing,
            modify_assembly=False,        # disallow page rearrangement
        )
        encryption_config = pikepdf.Encryption(
            owner=owner_password,
            user=user_password,
            R=encryption_revision,
            allow=permissions,
        )

        with open_pdf(source.storage_path) as source_pdf:
            page_count = len(source_pdf.pages)
            source_pdf.save(output_path, encryption=encryption_config)

        # Validate: confirm the output is openable with the user password
        try:
            with pikepdf.Pdf.open(output_path, password=user_password, suppress_warnings=True) as verify:
                if not verify.is_encrypted:
                    raise PdfProcessingError(
                        code="protect_failed",
                        user_message="Protection was not applied to the output PDF.",
                    )
        except pikepdf.PasswordError as exc:
            raise PdfProcessingError(
                code="protect_verification_failed",
                user_message="Protected PDF could not be opened with the provided user password.",
            ) from exc

        return ProcessingResult(
            artifact=GeneratedArtifact(
                local_path=output_path,
                filename=output_filename,
                content_type=PDF_CONTENT_TYPE,
                kind=ArtifactKind.RESULT,
                metadata={
                    "pages_processed": page_count,
                    "encryption_bits": payload.encryption,
                    "encryption_revision": encryption_revision,
                    "has_user_password": bool(payload.user_password),
                    "has_owner_password": bool(payload.owner_password),
                    "permissions": {
                        "allow_printing": payload.allow_printing,
                        "allow_copying": payload.allow_copying,
                        "allow_annotations": payload.allow_annotations,
                        "allow_form_filling": payload.allow_form_filling,
                    },
                },
            ),
            completion_message=(
                f"PDF protected with AES-{payload.encryption} encryption."
            ),
        )