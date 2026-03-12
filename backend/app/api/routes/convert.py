from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import enforce_job_rate_limit, get_current_user, get_job_service
from app.models.user import User
from app.schemas.job import (
    ConvertFromPdfRouteRequest,
    ConvertToPdfJobRequest,
    HtmlToPdfJobRequest,
    JobCreateResponse,
)
from app.services.job_service import JobService

router = APIRouter(prefix="/convert", dependencies=[Depends(enforce_job_rate_limit)])


@router.post("/to-pdf", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def to_pdf(
    payload: ConvertToPdfJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    tool_id = job_service.resolve_convert_to_pdf_tool(payload=payload, owner=current_user)
    return job_service.create_job(tool_id=tool_id, payload=payload, owner=current_user)


@router.post("/html-to-pdf", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def html_to_pdf(
    payload: HtmlToPdfJobRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    return job_service.create_job(tool_id="html2pdf", payload=payload, owner=current_user)


@router.post("/from-pdf", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def from_pdf(
    payload: ConvertFromPdfRouteRequest,
    job_service: Annotated[JobService, Depends(get_job_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobCreateResponse:
    tool_id = job_service.resolve_convert_from_pdf_tool(payload)
    normalized_payload = job_service.normalize_convert_from_pdf_payload(tool_id=tool_id, payload=payload)
    return job_service.create_job(tool_id=tool_id, payload=normalized_payload, owner=current_user)
