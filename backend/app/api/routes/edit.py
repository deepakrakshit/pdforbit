from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import enforce_job_rate_limit, get_current_user, get_job_service
from app.models.user import User
from app.schemas.job import (
    CropJobRequest,
    JobCreateResponse,
    PageNumbersJobRequest,
    RotateJobRequest,
    WatermarkJobRequest,
)
from app.services.job_service import JobService

router = APIRouter(prefix="/edit", dependencies=[Depends(enforce_job_rate_limit)])


@router.post("/rotate", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def rotate(
    payload: RotateJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="rotate", payload=payload, owner=current_user)


@router.post("/watermark", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def watermark(
    payload: WatermarkJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="watermark", payload=payload, owner=current_user)


@router.post("/page-numbers", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def page_numbers(
    payload: PageNumbersJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="pagenums", payload=payload, owner=current_user)


@router.post("/crop", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def crop(
    payload: CropJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="crop", payload=payload, owner=current_user)
