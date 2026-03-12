from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.config import AppSettings
from app.main import create_app


@pytest.fixture()
def migrated_client(tmp_path: Path, backend_root: Path) -> TestClient:
    db_path = tmp_path / "auth-phase3.sqlite3"
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"

    alembic_config = Config(str(backend_root / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location",
        str(backend_root / "app" / "db" / "migrations"),
    )
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")

    settings = AppSettings(
        APP_ENV="test",
        DATABASE_URL=database_url,
        DOCS_ENABLED=False,
        JWT_ACCESS_SECRET="phase3-access-secret-with-32-plus-chars",
        JWT_REFRESH_SECRET="phase3-refresh-secret-with-32-plus-chars",
        PASSWORD_MIN_LENGTH=8,
    )
    return TestClient(create_app(settings=settings))


def test_register_login_refresh_logout_and_me_flow(migrated_client: TestClient) -> None:
    register_response = migrated_client.post(
        "/api/v1/auth/register",
        json={"email": "owner@pdforbit.test", "password": "StrongPassword123"},
    )

    assert register_response.status_code == 201
    register_body = register_response.json()
    assert register_body["user"]["email"] == "owner@pdforbit.test"
    assert register_body["token_type"] == "bearer"
    assert register_body["access_token"]
    assert register_body["refresh_token"]

    me_response = migrated_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {register_body['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "owner@pdforbit.test"
    assert me_response.json()["plan_type"] == "free"
    assert me_response.json()["credits_remaining"] == 30

    login_response = migrated_client.post(
        "/api/v1/auth/login",
        json={"email": "OWNER@PDFORBIT.TEST", "password": "StrongPassword123"},
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["refresh_token"] != register_body["refresh_token"]

    refresh_response = migrated_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_body["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refresh_body = refresh_response.json()
    assert refresh_body["refresh_token"] != login_body["refresh_token"]

    stale_refresh_response = migrated_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_body["refresh_token"]},
    )
    assert stale_refresh_response.status_code == 401

    logout_response = migrated_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_body["refresh_token"]},
    )
    assert logout_response.status_code == 204

    post_logout_refresh = migrated_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_body["refresh_token"]},
    )
    assert post_logout_refresh.status_code == 401


def test_register_rejects_duplicate_email(migrated_client: TestClient) -> None:
    payload = {"email": "duplicate@pdforbit.test", "password": "StrongPassword123"}

    first = migrated_client.post("/api/v1/auth/register", json=payload)
    second = migrated_client.post("/api/v1/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "An account with that email already exists."


def test_login_rejects_invalid_password(migrated_client: TestClient) -> None:
    migrated_client.post(
        "/api/v1/auth/register",
        json={"email": "login@pdforbit.test", "password": "StrongPassword123"},
    )

    response = migrated_client.post(
        "/api/v1/auth/login",
        json={"email": "login@pdforbit.test", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_me_requires_bearer_token(migrated_client: TestClient) -> None:
    response = migrated_client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication credentials were not provided."


def test_signup_alias_matches_register_flow(migrated_client: TestClient) -> None:
    response = migrated_client.post(
        "/api/v1/auth/signup",
        json={"email": "signup@pdforbit.test", "password": "StrongPassword123"},
    )

    assert response.status_code == 201
    assert response.json()["user"]["plan_type"] == "free"
    assert response.json()["user"]["credits_remaining"] == 30
