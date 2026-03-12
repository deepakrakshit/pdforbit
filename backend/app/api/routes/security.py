from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import enforce_job_rate_limit, get_current_user, get_job_service
from app.models.user import User
from app.schemas.job import (
    CompareJobRequest,
    JobCreateResponse,
    ProtectJobRequest,
    RedactJobRequest,
    SignJobRequest,
    UnlockJobRequest,
)
from app.services.job_service import JobService

router = APIRouter(prefix="/security", dependencies=[Depends(enforce_job_rate_limit)])


@router.post("/unlock", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def unlock(
    payload: UnlockJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="unlock", payload=payload, owner=current_user)


@router.post("/protect", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def protect(
    payload: ProtectJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="protect", payload=payload, owner=current_user)


@router.post("/sign", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def sign(
    payload: SignJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="sign", payload=payload, owner=current_user)


@router.post("/redact", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def redact(
    payload: RedactJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="redact", payload=payload, owner=current_user)


@router.post("/compare", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def compare(
    payload: CompareJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="compare", payload=payload, owner=current_user)
