from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_download_service
from app.services.download_service import DownloadService

router = APIRouter(prefix="/download")


@router.get("/{job_id}")
def download_artifact(
    job_id: str,
    exp: Annotated[int, Query(alias="exp", ge=0)],
    sig: Annotated[str, Query(alias="sig", min_length=32)],
    session: Annotated[Session, Depends(get_db_session)],
    download_service: Annotated[DownloadService, Depends(get_download_service)],
) -> FileResponse:
    resolved = download_service.resolve_download(
        session=session,
        job_id=job_id,
        expiration=exp,
        signature=sig,
    )
    return FileResponse(
        path=resolved.file_path,
        media_type=resolved.artifact.content_type,
        filename=resolved.artifact.filename,
        headers={"Cache-Control": "private, no-store"},
    )
