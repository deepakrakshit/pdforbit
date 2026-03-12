from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.request_context import set_request_id


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, request_id_header: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.request_id_header = request_id_header
        self.logger = logging.getLogger("app.http")

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(self.request_id_header, uuid4().hex)
        set_request_id(request_id)

        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            self.logger.exception(
                "request.failed",
                extra={
                    "method": request.method,
                    "path": str(request.url.path),
                },
            )
            raise

        duration_ms = round((perf_counter() - started) * 1000, 2)
        response.headers[self.request_id_header] = request_id
        self.logger.info(
            "request.completed",
            extra={
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

