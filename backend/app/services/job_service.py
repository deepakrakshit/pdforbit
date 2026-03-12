from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import AppSettings
from app.db.repositories.job import JobRepository
from app.db.repositories.upload import UploadRepository
from app.models.artifact import JobArtifact
from app.models.enums import JobStatus, UploadStatus
from app.models.job import Job
from app.models.job_event import JobEvent
from app.models.job_input import JobInput
from app.models.upload import Upload
from app.models.user import User
from app.schemas.job import (
    CanonicalJobCreateRequest,
    ConvertFromPdfRouteRequest,
    JobCreateResponse,
    JobStatusResponse,
    TOOL_PAYLOAD_MODELS,
)
from app.services.credit_service import CreditService
from app.services.download_service import DownloadService
from app.services.queue_service import QueueService
from app.utils.ids import generate_public_id


@dataclass(frozen=True)
class UploadBindingSpec:
    field_name: str
    role: str
    multiple: bool = False
    allowed_extensions: frozenset[str] | None = None


@dataclass(frozen=True)
class ToolDefinition:
    tool_id: str
    queue_name: str
    payload_model: type[BaseModel]
    upload_bindings: tuple[UploadBindingSpec, ...]
    allowed_extensions: frozenset[str]


@dataclass(frozen=True)
class ResolvedJobInput:
    upload: Upload
    role: str
    position: int


PDF_EXTENSIONS = frozenset({".pdf"})
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"})
WORD_EXTENSIONS = frozenset({".doc", ".docx"})
EXCEL_EXTENSIONS = frozenset({".xls", ".xlsx"})
PPT_EXTENSIONS = frozenset({".ppt", ".pptx"})
HTML_EXTENSIONS = frozenset({".html", ".htm"})
CERTIFICATE_EXTENSIONS = frozenset({".p12", ".pfx"})

TOOL_DEFINITIONS: dict[str, ToolDefinition] = {
    "merge": ToolDefinition(
        tool_id="merge",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["merge"],
        upload_bindings=(UploadBindingSpec(field_name="file_ids", role="source", multiple=True),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "split": ToolDefinition(
        tool_id="split",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["split"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "extract": ToolDefinition(
        tool_id="extract",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["extract"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "remove": ToolDefinition(
        tool_id="remove",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["remove"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "reorder": ToolDefinition(
        tool_id="reorder",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["reorder"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "compress": ToolDefinition(
        tool_id="compress",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["compress"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "repair": ToolDefinition(
        tool_id="repair",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["repair"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "ocr": ToolDefinition(
        tool_id="ocr",
        queue_name="pdf-ocr",
        payload_model=TOOL_PAYLOAD_MODELS["ocr"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "img2pdf": ToolDefinition(
        tool_id="img2pdf",
        queue_name="pdf-convert",
        payload_model=TOOL_PAYLOAD_MODELS["img2pdf"],
        upload_bindings=(
            UploadBindingSpec(field_name="file_id", role="source"),
            UploadBindingSpec(field_name="file_ids", role="source", multiple=True),
        ),
        allowed_extensions=IMAGE_EXTENSIONS,
    ),
    "word2pdf": ToolDefinition(
        tool_id="word2pdf",
        queue_name="pdf-convert",
        payload_model=TOOL_PAYLOAD_MODELS["word2pdf"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=WORD_EXTENSIONS,
    ),
    "excel2pdf": ToolDefinition(
        tool_id="excel2pdf",
        queue_name="pdf-convert",
        payload_model=TOOL_PAYLOAD_MODELS["excel2pdf"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=EXCEL_EXTENSIONS,
    ),
    "ppt2pdf": ToolDefinition(
        tool_id="ppt2pdf",
        queue_name="pdf-convert",
        payload_model=TOOL_PAYLOAD_MODELS["ppt2pdf"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PPT_EXTENSIONS,
    ),
    "html2pdf": ToolDefinition(
        tool_id="html2pdf",
        queue_name="pdf-convert",
        payload_model=TOOL_PAYLOAD_MODELS["html2pdf"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=HTML_EXTENSIONS,
    ),
    "pdf2img": ToolDefinition(
        tool_id="pdf2img",
        queue_name="pdf-convert",
        payload_model=TOOL_PAYLOAD_MODELS["pdf2img"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "pdf2word": ToolDefinition(
        tool_id="pdf2word",
        queue_name="pdf-convert",
        payload_model=TOOL_PAYLOAD_MODELS["pdf2word"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "pdf2excel": ToolDefinition(
        tool_id="pdf2excel",
        queue_name="pdf-convert",
        payload_model=TOOL_PAYLOAD_MODELS["pdf2excel"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "pdf2ppt": ToolDefinition(
        tool_id="pdf2ppt",
        queue_name="pdf-convert",
        payload_model=TOOL_PAYLOAD_MODELS["pdf2ppt"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "pdf2pdfa": ToolDefinition(
        tool_id="pdf2pdfa",
        queue_name="pdf-convert",
        payload_model=TOOL_PAYLOAD_MODELS["pdf2pdfa"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "rotate": ToolDefinition(
        tool_id="rotate",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["rotate"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "editor_apply": ToolDefinition(
        tool_id="editor_apply",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["editor_apply"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "watermark": ToolDefinition(
        tool_id="watermark",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["watermark"],
        upload_bindings=(
            UploadBindingSpec(field_name="file_id", role="source"),
            UploadBindingSpec(
                field_name="image_upload_id",
                role="overlay",
                allowed_extensions=IMAGE_EXTENSIONS,
            ),
        ),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "pagenums": ToolDefinition(
        tool_id="pagenums",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["pagenums"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "crop": ToolDefinition(
        tool_id="crop",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["crop"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "unlock": ToolDefinition(
        tool_id="unlock",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["unlock"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "protect": ToolDefinition(
        tool_id="protect",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["protect"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "sign": ToolDefinition(
        tool_id="sign",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["sign"],
        upload_bindings=(
            UploadBindingSpec(field_name="file_id", role="source"),
            UploadBindingSpec(
                field_name="signature_image_upload_id",
                role="signature-image",
                allowed_extensions=IMAGE_EXTENSIONS,
            ),
            UploadBindingSpec(
                field_name="cert_file_id",
                role="certificate",
                allowed_extensions=CERTIFICATE_EXTENSIONS,
            ),
        ),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "redact": ToolDefinition(
        tool_id="redact",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["redact"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "compare": ToolDefinition(
        tool_id="compare",
        queue_name="pdf-default",
        payload_model=TOOL_PAYLOAD_MODELS["compare"],
        upload_bindings=(
            UploadBindingSpec(field_name="file_id_a", role="left"),
            UploadBindingSpec(field_name="file_id_b", role="right"),
        ),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "translate": ToolDefinition(
        tool_id="translate",
        queue_name="pdf-ocr",
        payload_model=TOOL_PAYLOAD_MODELS["translate"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
    "summarize": ToolDefinition(
        tool_id="summarize",
        queue_name="pdf-ocr",
        payload_model=TOOL_PAYLOAD_MODELS["summarize"],
        upload_bindings=(UploadBindingSpec(field_name="file_id", role="source"),),
        allowed_extensions=PDF_EXTENSIONS,
    ),
}

TO_PDF_EXTENSION_MAP = {
    **{extension: "img2pdf" for extension in IMAGE_EXTENSIONS},
    **{extension: "word2pdf" for extension in WORD_EXTENSIONS},
    **{extension: "excel2pdf" for extension in EXCEL_EXTENSIONS},
    **{extension: "ppt2pdf" for extension in PPT_EXTENSIONS},
}

FROM_PDF_FORMAT_MAP = {
    "word": "pdf2word",
    "excel": "pdf2excel",
    "ppt": "pdf2ppt",
}

FRONTEND_STATUS_MAP = {
    JobStatus.PENDING: "pending",
    JobStatus.PROCESSING: "processing",
    JobStatus.COMPLETED: "completed",
    JobStatus.FAILED: "failed",
    JobStatus.EXPIRED: "failed",
}


def ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class JobService:
    def __init__(
        self,
        session: Session,
        settings: AppSettings,
        queue_service: QueueService,
        download_service: DownloadService,
    ) -> None:
        self._session = session
        self._settings = settings
        self._queue = queue_service
        self._downloads = download_service
        self._credits = CreditService()
        self._jobs = JobRepository(session)
        self._uploads = UploadRepository(session)
        self._logger = logging.getLogger("app.jobs")

    def create_canonical_job(
        self,
        request: CanonicalJobCreateRequest,
        *,
        owner: User | None = None,
    ) -> JobCreateResponse:
        validated_payload = self.validate_payload(request.tool_id, request.payload)
        return self.create_job(tool_id=request.tool_id, payload=validated_payload, owner=owner)

    def create_job(
        self,
        *,
        tool_id: str,
        payload: BaseModel | dict[str, Any],
        owner: User | None = None,
    ) -> JobCreateResponse:
        if owner is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        definition = self._get_tool_definition(tool_id)
        task_cost = self._credits.consume_credits(user=owner, tool_id=tool_id)
        validated_payload = self._coerce_payload(definition, payload)
        payload_data = validated_payload.model_dump(mode="json", exclude_none=True)
        resolved_inputs = self._resolve_job_inputs(
            definition=definition,
            payload=payload_data,
            owner=owner,
        )

        public_id = generate_public_id("job")
        job = Job(
            owner_user_id=owner.id if owner else None,
            public_id=public_id,
            tool_id=definition.tool_id,
            queue_name=definition.queue_name,
            status=JobStatus.PENDING,
            progress=0,
            request_payload=payload_data,
        )
        job.inputs = [
            JobInput(upload_id=resolved.upload.id, role=resolved.role, position=resolved.position)
            for resolved in resolved_inputs
        ]
        job.events = [
            JobEvent(
                status=JobStatus.PENDING,
                progress=0,
                message="Job queued.",
                metadata_json={"queue_name": definition.queue_name, "credit_cost": task_cost},
            )
        ]

        self._jobs.add(job)
        for upload in {resolved.upload.id: resolved.upload for resolved in resolved_inputs}.values():
            if upload.status == UploadStatus.UPLOADED:
                upload.status = UploadStatus.IN_USE
                self._session.add(upload)

        self._session.flush()

        try:
            self._queue.enqueue_job(
                job_id=job.public_id,
                queue_name=job.queue_name,
                tool_id=job.tool_id,
            )
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            try:
                self._queue.delete_job(job.public_id)
            except Exception as queue_cleanup_exc:
                self._logger.warning(
                    "queue.cleanup_failed",
                    extra={"job_id": job.public_id, "error": str(queue_cleanup_exc)},
                )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to enqueue job at this time.",
            ) from exc

        return JobCreateResponse(job_id=job.public_id)

    def get_job_status(self, job_id: str, *, owner: User | None = None) -> JobStatusResponse:
        job = self._jobs.get_by_public_id(job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

        if job.owner_user_id is not None:
            if owner is None or job.owner_user_id != owner.id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

        artifact = self._downloads.get_active_artifact(job)
        artifact_metadata = artifact.metadata_json if artifact and artifact.metadata_json else {}
        download_url = self._downloads.build_download_url(job=job, artifact=artifact)

        error_message = job.error_message
        if job.status == JobStatus.EXPIRED and not error_message:
            error_message = "Result has expired."

        return JobStatusResponse(
            job_id=job.public_id,
            status=FRONTEND_STATUS_MAP[job.status],
            progress=job.progress,
            error=error_message,
            result_url=download_url,
            download_url=download_url,
            original_bytes=artifact_metadata.get("original_bytes"),
            compressed_bytes=artifact_metadata.get("compressed_bytes"),
            savings_pct=artifact_metadata.get("savings_pct"),
            pages_processed=artifact_metadata.get("pages_processed"),
            parts_count=artifact_metadata.get("parts_count"),
            redactions_applied=artifact_metadata.get("redactions_applied"),
            different_pages=artifact_metadata.get("different_pages"),
            detected_language=artifact_metadata.get("detected_language"),
            word_count=artifact_metadata.get("word_count"),
            processing_time_ms=artifact_metadata.get("processing_time_ms"),
            ocr_pages=artifact_metadata.get("ocr_pages"),
        )

    def validate_payload(self, tool_id: str, payload: dict[str, Any]) -> BaseModel:
        definition = self._get_tool_definition(tool_id)
        return self._validate_payload_model(definition.payload_model, payload)

    def resolve_convert_to_pdf_tool(self, *, payload: BaseModel, owner: User | None = None) -> str:
        payload_data = payload.model_dump(mode="json", exclude_none=True)
        raw_file_ids: list[str] = []
        if payload_data.get("file_id"):
            raw_file_ids.append(payload_data["file_id"])
        raw_file_ids.extend(payload_data.get("file_ids", []))

        if not raw_file_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one uploaded file is required for PDF conversion.",
            )

        resolved_tool_ids: list[str] = []
        for file_id in raw_file_ids:
            upload = self._resolve_upload(
                file_id=file_id,
                owner=owner,
                allowed_extensions=frozenset(TO_PDF_EXTENSION_MAP.keys()),
                tool_id="convert/to-pdf",
            )
            try:
                resolved_tool_ids.append(TO_PDF_EXTENSION_MAP[upload.extension])
            except KeyError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Uploaded file type is not supported for PDF conversion.",
                ) from exc

        unique_tool_ids = set(resolved_tool_ids)
        if len(unique_tool_ids) != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="All uploaded files for PDF conversion must be of the same supported type.",
            )

        resolved_tool_id = resolved_tool_ids[0]
        if len(raw_file_ids) > 1 and resolved_tool_id != "img2pdf":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only image-to-PDF supports converting multiple uploaded files in one job.",
            )

        return resolved_tool_id

    def resolve_convert_from_pdf_tool(self, payload: ConvertFromPdfRouteRequest) -> str:
        if payload.pdfa_level:
            return "pdf2pdfa"

        normalized_format = (payload.format or "").lower()
        if normalized_format in {"jpg", "jpeg", "png", "webp"}:
            return "pdf2img"

        try:
            return FROM_PDF_FORMAT_MAP[normalized_format]
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unsupported PDF conversion format.",
            ) from exc

    def normalize_convert_from_pdf_payload(
        self,
        *,
        tool_id: str,
        payload: ConvertFromPdfRouteRequest,
    ) -> BaseModel:
        payload_data: dict[str, Any] = {"file_id": payload.file_id}

        if tool_id == "pdf2img":
            payload_data["format"] = (payload.format or "jpg").lower()
            if payload.dpi is not None:
                payload_data["dpi"] = payload.dpi
            if payload.quality is not None:
                payload_data["quality"] = payload.quality
            if payload.single_page is not None:
                payload_data["single_page"] = payload.single_page
            if payload.thumbnail:
                payload_data["thumbnail"] = True
            if payload.thumbnail_max_px is not None:
                payload_data["thumbnail_max_px"] = payload.thumbnail_max_px
        elif tool_id in {"pdf2word", "pdf2excel", "pdf2ppt"}:
            payload_data["format"] = (payload.format or "").lower()
            if payload.output_filename is not None:
                payload_data["output_filename"] = payload.output_filename
        elif tool_id == "pdf2pdfa":
            payload_data["pdfa_level"] = payload.pdfa_level
            if payload.output_filename is not None:
                payload_data["output_filename"] = payload.output_filename
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unsupported PDF conversion format.",
            )

        return self.validate_payload(tool_id, payload_data)

    def _coerce_payload(
        self,
        definition: ToolDefinition,
        payload: BaseModel | dict[str, Any],
    ) -> BaseModel:
        if isinstance(payload, BaseModel):
            payload_data = payload.model_dump(mode="json", exclude_none=True)
        else:
            payload_data = payload
        return self._validate_payload_model(definition.payload_model, payload_data)

    def _validate_payload_model(
        self,
        payload_model: type[BaseModel],
        payload_data: dict[str, Any],
    ) -> BaseModel:
        try:
            return payload_model.model_validate(payload_data)
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc

    def _get_tool_definition(self, tool_id: str) -> ToolDefinition:
        try:
            return TOOL_DEFINITIONS[tool_id]
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unsupported tool identifier.",
            ) from exc

    def _resolve_job_inputs(
        self,
        *,
        definition: ToolDefinition,
        payload: dict[str, Any],
        owner: User | None,
    ) -> list[ResolvedJobInput]:
        resolved_inputs: list[ResolvedJobInput] = []
        position = 0

        for binding in definition.upload_bindings:
            raw_value = payload.get(binding.field_name)
            if raw_value in (None, [], ""):
                continue
            values = list(raw_value) if binding.multiple else [raw_value]

            for file_id in values:
                upload = self._resolve_upload(
                    file_id=file_id,
                    owner=owner,
                    allowed_extensions=binding.allowed_extensions or definition.allowed_extensions,
                    tool_id=definition.tool_id,
                )
                resolved_inputs.append(ResolvedJobInput(upload=upload, role=binding.role, position=position))
                position += 1

        return resolved_inputs

    def _resolve_upload(
        self,
        *,
        file_id: str,
        owner: User | None,
        allowed_extensions: frozenset[str],
        tool_id: str,
    ) -> Upload:
        upload = self._uploads.get_by_public_id(file_id)
        if upload is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Uploaded file '{file_id}' was not found.",
            )

        if owner and upload.owner_user_id and upload.owner_user_id != owner.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to that uploaded file.",
            )

        now = datetime.now(timezone.utc)
        if upload.deleted_at is not None or upload.status in {UploadStatus.DELETED, UploadStatus.EXPIRED}:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Uploaded file '{file_id}' is no longer available.",
            )
        if ensure_utc_datetime(upload.expires_at) <= now:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Uploaded file '{file_id}' has expired.",
            )
        if upload.status == UploadStatus.QUARANTINED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Uploaded file '{file_id}' is quarantined and cannot be processed.",
            )
        if upload.extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Uploaded file '{file_id}' is not a valid input for tool '{tool_id}'.",
            )

        return upload
