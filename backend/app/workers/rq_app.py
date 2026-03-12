from __future__ import annotations

import os

from redis import Redis
from rq import SimpleWorker, Worker
from rq.timeouts import TimerDeathPenalty

from app.core.config import AppSettings, build_settings
from app.core.logging import configure_logging

QUEUE_NAMES = ("pdf-default", "pdf-ocr", "pdf-convert", "pdf-cleanup")


class InProcessWorker(SimpleWorker):
    """Runs jobs in-process for test and Windows environments."""

    death_penalty_class = TimerDeathPenalty


def resolve_worker_class(settings: AppSettings) -> type[Worker]:
    if settings.app_env == "test" or os.name == "nt":
        return InProcessWorker
    return Worker


def build_worker(
    settings: AppSettings | None = None,
    *,
    connection: Redis | None = None,
) -> Worker:
    resolved_settings = settings or build_settings()
    resolved_connection = connection
    if resolved_connection is None:
        if not resolved_settings.redis_url:
            raise RuntimeError("REDIS_URL is required unless an RQ connection is provided explicitly.")
        resolved_connection = Redis.from_url(resolved_settings.redis_url)

    worker_class = resolve_worker_class(resolved_settings)
    return worker_class(QUEUE_NAMES, connection=resolved_connection)


def main() -> None:
    settings = build_settings()
    configure_logging(settings)
    worker = build_worker(settings=settings)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
