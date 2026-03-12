from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import AppSettings
from app.db.repositories.upload import UploadRepository
from app.models.upload import Upload
from app.models.user import User
from app.schemas.upload import UploadResponse
from app.services.storage_service import StorageService
from app.utils.files import UploadValidationError, detect_upload_file, sanitize_filename
from app.utils.ids import generate_public_id
from app.utils.pdf_validation import PdfMetadata, extract_pdf_metadata


class UploadService:
    def __init__(
        self,
        session: Session,
        settings: AppSettings,
        storage_service: StorageService,
    ) -> None:
        self._session = session
        self._settings = settings
        self._storage = storage_service
        self._uploads = UploadRepository(session)

    def upload_file(self, upload: UploadFile, *, owner: User | None = None) -> UploadResponse:
        original_filename = sanitize_filename(upload.filename)
        temp_suffix = Path(original_filename).suffix.lower() or ".upload"
        temp_path = self._storage.create_temporary_upload_path(suffix=temp_suffix)
        max_upload_bytes = self._resolve_max_upload_bytes(owner=owner)
        created_at = datetime.now(timezone.utc)

        sha256 = hashlib.sha256()
        size_bytes = 0

        try:
            with temp_path.open("wb") as temp_file:
                while True:
                    chunk = upload.file.read(self._settings.upload_chunk_size_bytes)
                    if not chunk:
                        break

                    size_bytes += len(chunk)
                    if size_bytes > max_upload_bytes:
                        raise UploadValidationError(
                            f"Uploaded file exceeds the {max_upload_bytes // (1024 * 1024)} MB size limit.",
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        )

                    sha256.update(chunk)
                    temp_file.write(chunk)

            detected_file = detect_upload_file(
                file_path=temp_path,
                original_filename=original_filename,
                declared_content_type=upload.content_type,
            )
            pdf_metadata = self._extract_pdf_metadata(
                file_path=temp_path,
                is_pdf=detected_file.kind == "pdf",
            )

            public_id = generate_public_id("file")
            relative_storage_path = self._storage.build_upload_relative_path(
                public_id=public_id,
                extension=detected_file.extension,
                created_at=created_at,
            )
            final_path = self._storage.commit_temp_file(
                temp_path=temp_path,
                relative_path=relative_storage_path,
            )

            upload_record = Upload(
                owner_user_id=owner.id if owner else None,
                public_id=public_id,
                original_filename=original_filename,
                stored_filename=final_path.name,
                storage_path=relative_storage_path,
                content_type=detected_file.content_type,
                extension=detected_file.extension,
                size_bytes=size_bytes,
                sha256=sha256.hexdigest(),
                page_count=pdf_metadata.page_count,
                is_pdf=detected_file.kind == "pdf",
                is_encrypted=pdf_metadata.is_encrypted,
                metadata_json={
                    "detected_kind": detected_file.kind,
                    "declared_content_type": upload.content_type,
                },
                expires_at=created_at + timedelta(minutes=self._settings.retention_minutes),
            )
            self._uploads.add(upload_record)
            try:
                self._session.commit()
            except Exception:
                self._session.rollback()
                self._storage.delete(relative_path=relative_storage_path)
                raise

            self._session.refresh(upload_record)
            return UploadResponse(
                file_id=upload_record.public_id,
                filename=upload_record.original_filename,
                size_bytes=upload_record.size_bytes,
                page_count=upload_record.page_count,
                is_encrypted=upload_record.is_encrypted if upload_record.is_pdf else None,
                expires_at=upload_record.expires_at,
            )
        except UploadValidationError as exc:
            self._session.rollback()
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        finally:
            upload.file.close()
            temp_path.unlink(missing_ok=True)

    def _resolve_max_upload_bytes(self, *, owner: User | None) -> int:
        megabytes = self._settings.user_max_upload_mb if owner else self._settings.guest_max_upload_mb
        return megabytes * 1024 * 1024

    def _extract_pdf_metadata(self, *, file_path: Path, is_pdf: bool) -> PdfMetadata:
        if not is_pdf:
            return PdfMetadata(page_count=None, is_encrypted=False)
        return extract_pdf_metadata(file_path)
