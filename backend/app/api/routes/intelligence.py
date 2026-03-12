from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import enforce_job_rate_limit, get_current_user, get_job_service
from app.models.user import User
from app.schemas.job import JobCreateResponse, SummarizeJobRequest, TranslateJobRequest
from app.services.job_service import JobService

router = APIRouter(prefix="/intelligence", dependencies=[Depends(enforce_job_rate_limit)])


@router.post("/translate", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def translate(
    payload: TranslateJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="translate", payload=payload, owner=current_user)


@router.post("/summarize", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def summarize(
    payload: SummarizeJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="summarize", payload=payload, owner=current_user)
