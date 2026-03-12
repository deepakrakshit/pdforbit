from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    status: Literal["ok", "error"]
    detail: str


class LiveHealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
    service: str
    version: str
    environment: str
    timestamp: datetime
    uptime_seconds: float


class ReadyHealthResponse(LiveHealthResponse):
    status: Literal["ok", "error"]
    checks: list[HealthCheck]
