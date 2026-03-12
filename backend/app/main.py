from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import AppSettings, get_settings
from app.core.container import AppContainer
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.request_context import get_request_id
from fastapi.middleware.cors import CORSMiddleware


def create_app(settings: AppSettings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    logger = logging.getLogger("app.lifecycle")
    container = AppContainer(settings=resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "application.startup",
            extra={
                "environment": resolved_settings.app_env,
                "version": resolved_settings.app_version,
            },
        )
        container.provision_internal_admin()
        yield
        container.dispose()
        logger.info("application.shutdown")

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        docs_url="/docs" if resolved_settings.docs_enabled else None,
        redoc_url="/redoc" if resolved_settings.docs_enabled else None,
        openapi_url="/openapi.json" if resolved_settings.docs_enabled else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins
        or ["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.container = container
    app.add_middleware(
        RequestContextMiddleware,
        request_id_header=resolved_settings.request_id_header,
    )
    app.include_router(api_router, prefix=resolved_settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, Any]:
        return {
            "service": resolved_settings.app_name,
            "version": resolved_settings.app_version,
            "environment": resolved_settings.app_env,
        }

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("app.errors").exception(
            "unhandled.exception",
            extra={
                "method": request.method,
                "path": str(request.url.path),
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error.",
                "code": "internal_server_error",
                "request_id": get_request_id(),
            },
        )

    return app


app = create_app()
