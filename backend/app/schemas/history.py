from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job import JOB_ID_PATTERN

FILE_ID_PATTERN = r"^file_[A-Za-z0-9_-]{8,}$"


class HistoryPagination(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class JobHistoryItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(pattern=JOB_ID_PATTERN)
    tool_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: int = Field(ge=0, le=100)
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    download_url: str | None = None
    result_url: str | None = None
    original_bytes: int | None = None
    compressed_bytes: int | None = None
    savings_pct: float | None = None
    pages_processed: int | None = None
    parts_count: int | None = None
    redactions_applied: int | None = None
    different_pages: int | None = None
    detected_language: str | None = None
    word_count: int | None = None


class JobHistoryListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[JobHistoryItem]
    pagination: HistoryPagination


class UploadHistoryItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_id: str = Field(pattern=FILE_ID_PATTERN)
    filename: str
    content_type: str
    extension: str
    size_bytes: int = Field(ge=0)
    page_count: int | None = None
    is_pdf: bool
    is_encrypted: bool
    status: str
    created_at: datetime
    expires_at: datetime
    deleted_at: datetime | None = None


class UploadHistoryListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[UploadHistoryItem]
    pagination: HistoryPagination
