from __future__ import annotations

import logging
from typing import Any

from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job as RQJob

from app.core.config import AppSettings


class QueueService:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._logger = logging.getLogger("app.queue")
        self._connection = self._build_connection()

    @property
    def connection(self) -> Redis[Any]:
        return self._connection

    def ping(self) -> None:
        self._connection.ping()

    def enqueue_job(self, *, job_id: str, queue_name: str, tool_id: str) -> RQJob:
        queue = self.get_queue(queue_name)
        return queue.enqueue(
            "app.workers.tasks.process_job",
            job_id,
            tool_id=tool_id,
            job_id=job_id,
            description=f"{tool_id}:{job_id}",
            failure_ttl=24 * 60 * 60,
            result_ttl=0,
            job_timeout=self._settings.queue_default_timeout_seconds,
            meta={
                "job_id": job_id,
                "tool_id": tool_id,
                "queue_name": queue_name,
            },
        )

    def get_job(self, job_id: str) -> RQJob | None:
        try:
            return RQJob.fetch(job_id, connection=self._connection)
        except NoSuchJobError:
            return None

    def delete_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        if job is None:
            return
        job.delete()

    def get_queue(self, queue_name: str) -> Queue:
        return Queue(
            name=queue_name,
            connection=self._connection,
            default_timeout=self._settings.queue_default_timeout_seconds,
            is_async=True,
        )

    def _build_connection(self) -> Redis[Any]:
        if self._settings.app_env == "test" and not self._settings.redis_url:
            try:
                import fakeredis
            except ImportError as exc:
                raise RuntimeError("fakeredis is required for queue-backed tests.") from exc
            self._logger.debug("queue.using_fakeredis")
            return fakeredis.FakeRedis()

        if not self._settings.redis_url:
            raise RuntimeError("Queue service requires REDIS_URL to be configured.")

        return Redis.from_url(self._settings.redis_url)
