from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import enforce_job_rate_limit, get_current_user, get_job_service
from app.models.user import User
from app.schemas.job import (
    ExtractJobRequest,
    JobCreateResponse,
    MergeJobRequest,
    RemovePagesJobRequest,
    ReorderJobRequest,
    SplitJobRequest,
)
from app.services.job_service import JobService

router = APIRouter(prefix="/organize", dependencies=[Depends(enforce_job_rate_limit)])


@router.post("/merge", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def merge(
    payload: MergeJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="merge", payload=payload, owner=current_user)


@router.post("/split", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def split(
    payload: SplitJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="split", payload=payload, owner=current_user)


@router.post("/extract", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def extract(
    payload: ExtractJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="extract", payload=payload, owner=current_user)


@router.post("/remove-pages", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def remove_pages(
    payload: RemovePagesJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="remove", payload=payload, owner=current_user)


@router.post("/reorder", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def reorder(
    payload: ReorderJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="reorder", payload=payload, owner=current_user)
