from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user, get_history_service
from app.models.user import User
from app.schemas.history import JobHistoryListResponse, UploadHistoryListResponse
from app.services.history_service import HistoryService

router = APIRouter(prefix="/history")


@router.get("/jobs", response_model=JobHistoryListResponse)
def list_job_history(
    current_user: Annotated[User, Depends(get_current_user)],
    history_service: Annotated[HistoryService, Depends(get_history_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobHistoryListResponse:
    return history_service.list_jobs(owner=current_user, limit=limit, offset=offset)


@router.get("/uploads", response_model=UploadHistoryListResponse)
def list_upload_history(
    current_user: Annotated[User, Depends(get_current_user)],
    history_service: Annotated[HistoryService, Depends(get_history_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UploadHistoryListResponse:
    return history_service.list_uploads(owner=current_user, limit=limit, offset=offset)
