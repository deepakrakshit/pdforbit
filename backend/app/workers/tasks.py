from __future__ import annotations

from app.core.config import build_settings
from app.db.session import DatabaseManager
from app.services.job_execution_service import JobExecutionService
from app.services.storage_service import StorageService

def process_job(job_id: str, *, tool_id: str) -> None:
    settings = build_settings()
    database_manager = DatabaseManager(settings=settings)
    storage_service = StorageService(settings=settings)

    try:
        with database_manager.session_scope() as session:
            executor = JobExecutionService(
                session=session,
                settings=settings,
                storage_service=storage_service,
            )
            executor.execute(job_id=job_id, tool_id=tool_id)
    finally:
        database_manager.dispose()
