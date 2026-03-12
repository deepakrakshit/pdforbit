from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import AppSettings
from app.main import create_app


def build_test_settings() -> AppSettings:
    return AppSettings(
        APP_ENV="test",
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        DOCS_ENABLED=False,
        LOG_FORMAT="console",
        LOG_LEVEL="INFO",
    )


def create_test_client() -> TestClient:
    return TestClient(create_app(settings=build_test_settings()))


@pytest.fixture()
def client() -> TestClient:
    return create_test_client()


@pytest.fixture(scope="session")
def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]
