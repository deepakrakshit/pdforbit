from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import enforce_job_rate_limit, get_current_user, get_job_service
from app.models.user import User
from app.schemas.job import CompressJobRequest, JobCreateResponse, OcrJobRequest, RepairJobRequest
from app.services.job_service import JobService

router = APIRouter(prefix="/optimize", dependencies=[Depends(enforce_job_rate_limit)])


@router.post("/compress", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def compress(
    payload: CompressJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="compress", payload=payload, owner=current_user)


@router.post("/repair", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def repair(
    payload: RepairJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="repair", payload=payload, owner=current_user)


@router.post("/ocr", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def ocr(
    payload: OcrJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="ocr", payload=payload, owner=current_user)
