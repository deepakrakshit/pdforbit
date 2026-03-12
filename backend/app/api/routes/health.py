from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import get_system_service
from app.schemas.health import LiveHealthResponse, ReadyHealthResponse
from app.services.system_service import SystemService

router = APIRouter()


@router.get("/live", response_model=LiveHealthResponse, summary="Liveness probe")
async def liveness(
    system_service: Annotated[SystemService, Depends(get_system_service)],
) -> LiveHealthResponse:
    return system_service.get_liveness()


@router.get("/ready", response_model=ReadyHealthResponse, summary="Readiness probe")
async def readiness(
    system_service: Annotated[SystemService, Depends(get_system_service)],
) -> ReadyHealthResponse | JSONResponse:
    payload = system_service.get_readiness()
    if payload.status == "error":
        return JSONResponse(status_code=503, content=payload.model_dump(mode="json"))
    return payload
