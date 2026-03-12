from __future__ import annotations

import time

from app.core.config import AppSettings, build_settings
from app.core.logging import configure_logging
from app.db.session import DatabaseManager
from app.services.cleanup_service import CleanupService, CleanupSummary
from app.services.queue_service import QueueService
from app.services.storage_service import StorageService


def run_cleanup_cycle(settings: AppSettings | None = None) -> CleanupSummary:
    resolved_settings = settings or build_settings()
    database_manager = DatabaseManager(settings=resolved_settings)
    queue_service = QueueService(settings=resolved_settings)
    storage_service = StorageService(settings=resolved_settings)

    try:
        cleanup_service = CleanupService(
            settings=resolved_settings,
            database_manager=database_manager,
            queue_service=queue_service,
            storage_service=storage_service,
        )
        return cleanup_service.run_cycle()
    finally:
        database_manager.dispose()


def main() -> None:
    settings = build_settings()
    configure_logging(settings)

    while True:
        run_cleanup_cycle(settings=settings)
        time.sleep(settings.cleanup_interval_seconds)


if __name__ == "__main__":
    main()