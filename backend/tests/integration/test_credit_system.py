from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.repositories.job import JobRepository
from app.db.repositories.user import UserRepository
from app.models.enums import UserPlan
from tests.support.integration import authenticate_user, create_migrated_client, upload_pdf


@pytest.fixture()
def credit_client(tmp_path: Path, backend_root: Path) -> TestClient:
    return create_migrated_client(
        tmp_path=tmp_path,
        backend_root=backend_root,
        database_name="credits.sqlite3",
        storage_name="storage",
        access_secret="credits-access-secret-with-32-plus-chars",
        refresh_secret="credits-refresh-secret-with-32-plus-chars",
    )


@pytest.fixture()
def internal_admin_client(tmp_path: Path, backend_root: Path) -> TestClient:
    client = create_migrated_client(
        tmp_path=tmp_path,
        backend_root=backend_root,
        database_name="credits-admin.sqlite3",
        storage_name="storage",
        access_secret="credits-admin-access-secret-with-32-plus-chars",
        refresh_secret="credits-admin-refresh-secret-with-32-plus-chars",
        settings_overrides={
            "INTERNAL_ADMIN_ENABLED": True,
            "INTERNAL_ADMIN_EMAIL": "internal-admin@pdforbit.test",
            "INTERNAL_ADMIN_PASSWORD": "InternalAdminPassword123",
        },
    )
    client.app.state.container.provision_internal_admin()
    return client


def test_job_creation_deducts_credits_for_authenticated_user(credit_client: TestClient) -> None:
    headers = authenticate_user(credit_client, email="credits1@pdforbit.test")
    file_id = upload_pdf(credit_client, headers=headers)

    before = credit_client.get("/api/v1/users/me", headers=headers)
    assert before.status_code == 200
    assert before.json()["credits_remaining"] == 30

    response = credit_client.post(
        "/api/v1/optimize/compress",
        json={"file_id": file_id, "level": "medium", "output_filename": "compressed.pdf"},
        headers=headers,
    )

    assert response.status_code == 201

    after = credit_client.get("/api/v1/users/me", headers=headers)
    assert after.status_code == 200
    assert after.json()["credits_remaining"] == 29


def test_translate_consumes_five_credits_per_task(credit_client: TestClient) -> None:
    headers = authenticate_user(credit_client, email="credits2@pdforbit.test")
    file_id = upload_pdf(credit_client, headers=headers)

    response = credit_client.post(
        "/api/v1/intelligence/translate",
        json={
            "file_id": file_id,
            "target_language": "en",
            "source_language": "fr",
        },
        headers=headers,
    )

    assert response.status_code == 201

    after = credit_client.get("/api/v1/users/me", headers=headers)
    assert after.status_code == 200
    assert after.json()["credits_remaining"] == 25


def test_insufficient_credits_blocks_ai_job(credit_client: TestClient) -> None:
    headers = authenticate_user(credit_client, email="credits2b@pdforbit.test")
    file_id = upload_pdf(credit_client, headers=headers)

    container = credit_client.app.state.container
    with container.database_manager.session_scope() as session:
        user = UserRepository(session).get_by_email("credits2b@pdforbit.test")
        assert user is not None
        user.credits_remaining = 4
        session.add(user)

    response = credit_client.post(
        "/api/v1/intelligence/summarize",
        json={"file_id": file_id, "output_language": "en", "length": "short"},
        headers=headers,
    )

    assert response.status_code == 402
    assert response.json()["detail"] == "Insufficient credits"


def test_daily_free_credit_reset_runs_on_authenticated_request(credit_client: TestClient) -> None:
    headers = authenticate_user(credit_client, email="credits3@pdforbit.test")

    container = credit_client.app.state.container
    with container.database_manager.session_scope() as session:
        user = UserRepository(session).get_by_email("credits3@pdforbit.test")
        assert user is not None
        user.credits_remaining = 0
        user.last_credit_refresh = datetime.now(timezone.utc) - timedelta(days=1, minutes=5)
        session.add(user)

    response = credit_client.get("/api/v1/users/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["credits_remaining"] == 30


def test_pro_plan_refreshes_daily_and_reports_completed_jobs(credit_client: TestClient) -> None:
    headers = authenticate_user(credit_client, email="credits4@pdforbit.test")
    file_id = upload_pdf(credit_client, headers=headers)

    container = credit_client.app.state.container
    with container.database_manager.session_scope() as session:
        users = UserRepository(session)
        jobs = JobRepository(session)
        user = users.get_by_email("credits4@pdforbit.test")
        assert user is not None
        user.plan = UserPlan.PRO
        user.credits_remaining = 0
        user.last_credit_refresh = datetime.now(timezone.utc) - timedelta(days=1, minutes=5)
        session.add(user)

    me_response = credit_client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["plan_type"] == "pro"
    assert me_response.json()["credits_remaining"] == 1000

    create_response = credit_client.post(
        "/api/v1/optimize/compress",
        json={"file_id": file_id, "level": "medium", "output_filename": "compressed.pdf"},
        headers=headers,
    )
    assert create_response.status_code == 201

    with container.database_manager.session_scope() as session:
        job = JobRepository(session).get_by_public_id(create_response.json()["job_id"])
        assert job is not None
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        session.add(job)

    refreshed_me = credit_client.get("/api/v1/users/me", headers=headers)
    assert refreshed_me.status_code == 200
    assert refreshed_me.json()["jobs_processed"] == 1


def test_internal_admin_account_skips_credit_deduction(internal_admin_client: TestClient) -> None:
    login_response = internal_admin_client.post(
        "/api/v1/auth/login",
        json={
            "email": "internal-admin@pdforbit.test",
            "password": "InternalAdminPassword123",
        },
    )

    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["user"]["is_admin"] is True

    headers = {"Authorization": f"Bearer {login_body['access_token']}"}
    initial_me_response = internal_admin_client.get("/api/v1/users/me", headers=headers)
    assert initial_me_response.status_code == 200
    assert initial_me_response.json()["credits_remaining"] >= 999_999_999

    file_id = upload_pdf(internal_admin_client, headers=headers)

    container = internal_admin_client.app.state.container
    with container.database_manager.session_scope() as session:
        user = UserRepository(session).get_by_email("internal-admin@pdforbit.test")
        assert user is not None
        user.credits_remaining = 0
        session.add(user)

    response = internal_admin_client.post(
        "/api/v1/optimize/compress",
        json={"file_id": file_id, "level": "medium", "output_filename": "compressed.pdf"},
        headers=headers,
    )

    assert response.status_code == 201

    me_response = internal_admin_client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["is_admin"] is True
    assert me_response.json()["credits_remaining"] >= 999_999_999