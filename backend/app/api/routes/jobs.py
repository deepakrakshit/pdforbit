from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import enforce_job_rate_limit, get_current_user, get_job_service, get_optional_current_user
from app.models.user import User
from app.schemas.job import CanonicalJobCreateRequest, JobCreateResponse, JobStatusResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs")


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: CanonicalJobCreateRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(enforce_job_rate_limit)],
) -> JobCreateResponse:
    return job_service.create_canonical_job(payload, owner=current_user)


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
) -> JobStatusResponse:
    return job_service.get_job_status(job_id, owner=current_user)
