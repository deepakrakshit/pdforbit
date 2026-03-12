from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.dependencies import enforce_upload_rate_limit, get_optional_current_user, get_upload_service
from app.models.user import User
from app.schemas.upload import UploadResponse
from app.services.upload_service import UploadService

router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    file: Annotated[UploadFile, File(...)],
    upload_service: Annotated[UploadService, Depends(get_upload_service)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    _: Annotated[None, Depends(enforce_upload_rate_limit)],
) -> UploadResponse:
    return upload_service.upload_file(file, owner=current_user)
