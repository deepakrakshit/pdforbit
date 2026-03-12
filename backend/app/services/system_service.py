from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import AppSettings
from app.db.session import DatabaseManager
from app.services.queue_service import QueueService
from app.schemas.health import HealthCheck, LiveHealthResponse, ReadyHealthResponse
from app.services.storage_service import StorageService


class SystemService:
    def __init__(
        self,
        settings: AppSettings,
        started_at: datetime,
        database_manager: DatabaseManager,
        queue_service: QueueService,
        storage_service: StorageService,
    ) -> None:
        self._settings = settings
        self._started_at = started_at
        self._database_manager = database_manager
        self._queue_service = queue_service
        self._storage_service = storage_service

    def _base_payload(self) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        return {
            "service": self._settings.app_name,
            "version": self._settings.app_version,
            "environment": self._settings.app_env,
            "timestamp": now,
            "uptime_seconds": round((now - self._started_at).total_seconds(), 3),
        }

    def get_liveness(self) -> LiveHealthResponse:
        return LiveHealthResponse(status="ok", **self._base_payload())

    def get_readiness(self) -> ReadyHealthResponse:
        checks = [
            HealthCheck(
                name="configuration",
                status="ok",
                detail="Application settings loaded successfully.",
            ),
            HealthCheck(
                name="router",
                status="ok",
                detail="HTTP router mounted and ready to accept traffic.",
            ),
        ]
        status = "ok"

        try:
            self._database_manager.ping()
            checks.append(
                HealthCheck(
                    name="database",
                    status="ok",
                    detail="Database connection established successfully.",
                )
            )
        except SQLAlchemyError as exc:
            status = "error"
            checks.append(
                HealthCheck(
                    name="database",
                    status="error",
                    detail=f"Database connectivity failed: {exc.__class__.__name__}.",
                )
            )

        try:
            self._queue_service.ping()
            checks.append(
                HealthCheck(
                    name="queue",
                    status="ok",
                    detail="Queue backend connection established successfully.",
                )
            )
        except Exception as exc:
            status = "error"
            checks.append(
                HealthCheck(
                    name="queue",
                    status="error",
                    detail=f"Queue backend connectivity failed: {exc.__class__.__name__}.",
                )
            )

        try:
            self._storage_service.ping()
            checks.append(
                HealthCheck(
                    name="storage",
                    status="ok",
                    detail="Storage root is writable.",
                )
            )
        except OSError as exc:
            status = "error"
            checks.append(
                HealthCheck(
                    name="storage",
                    status="error",
                    detail=f"Storage initialization failed: {exc.__class__.__name__}.",
                )
            )

        return ReadyHealthResponse(**self._base_payload(), status=status, checks=checks)
