from __future__ import annotations

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.core.config import AppSettings
from app.db.repositories.user import UserRepository
from app.db.session import DatabaseManager
from app.models.enums import JobStatus
from app.models.job import Job
from app.models.user import User


@pytest.fixture()
def migrated_database_manager(tmp_path, backend_root):
    db_path = tmp_path / "phase2.sqlite3"
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"

    alembic_config = Config(str(backend_root / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location",
        str(backend_root / "app" / "db" / "migrations"),
    )
    alembic_config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(alembic_config, "head")

    database_manager = DatabaseManager(
        AppSettings(
            APP_ENV="test",
            DATABASE_URL=database_url,
            DOCS_ENABLED=False,
        )
    )

    try:
        yield database_manager
    finally:
        database_manager.dispose()


def test_alembic_upgrade_creates_expected_tables(migrated_database_manager: DatabaseManager) -> None:
    table_names = set(inspect(migrated_database_manager.engine).get_table_names())

    assert table_names == {
        "alembic_version",
        "job_artifacts",
        "job_events",
        "job_inputs",
        "jobs",
        "refresh_tokens",
        "uploads",
        "users",
    }


def test_user_repository_round_trip(migrated_database_manager: DatabaseManager) -> None:
    user_id = uuid4()

    with migrated_database_manager.session_scope() as session:
        repository = UserRepository(session)
        repository.add(
            User(
                id=user_id,
                email="architect@pdforbit.test",
                password_hash="argon2$placeholder",
            )
        )

    with migrated_database_manager.session_scope() as session:
        repository = UserRepository(session)
        loaded = repository.get_by_email("ARCHITECT@PDFORBIT.TEST")

    assert loaded is not None
    assert loaded.id == user_id
    assert loaded.email == "architect@pdforbit.test"


def test_unique_email_constraint_is_enforced(migrated_database_manager: DatabaseManager) -> None:
    with migrated_database_manager.session_scope() as session:
        session.add(
            User(
                email="duplicate@pdforbit.test",
                password_hash="argon2$placeholder",
            )
        )

    with pytest.raises(IntegrityError):
        with migrated_database_manager.session_scope() as session:
            session.add(
                User(
                    email="duplicate@pdforbit.test",
                    password_hash="argon2$placeholder",
                )
            )


def test_job_progress_check_constraint_is_enforced(migrated_database_manager: DatabaseManager) -> None:
    with pytest.raises(IntegrityError):
        with migrated_database_manager.session_scope() as session:
            session.add(
                Job(
                    public_id="job_invalid_progress",
                    tool_id="compress",
                    queue_name="pdf-default",
                    status=JobStatus.PENDING,
                    progress=101,
                    request_payload={"file_id": "file_123"},
                )
            )
