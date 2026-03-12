from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UploadResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_id: str
    filename: str
    size_bytes: int
    page_count: int | None = None
    is_encrypted: bool | None = None
    expires_at: datetime
