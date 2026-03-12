from __future__ import annotations

from uuid import UUID

import pytest

from app.core.config import AppSettings
from app.core.security import AuthenticationError, SecurityManager


@pytest.fixture()
def security_manager() -> SecurityManager:
    settings = AppSettings(
        APP_ENV="test",
        JWT_ACCESS_SECRET="access-secret-with-at-least-32-characters",
        JWT_REFRESH_SECRET="refresh-secret-with-at-least-32-characters",
    )
    return SecurityManager(settings)


def test_password_hashing_round_trip(security_manager: SecurityManager) -> None:
    password_hash = security_manager.hash_password("StrongPassword123")

    assert password_hash != "StrongPassword123"
    assert security_manager.verify_password("StrongPassword123", password_hash) is True
    assert security_manager.verify_password("wrong-password", password_hash) is False


def test_access_and_refresh_tokens_are_distinct(security_manager: SecurityManager) -> None:
    user_id = UUID("9be789b2-9cdc-4c46-a7cf-09d349faf44e")

    access = security_manager.create_access_token(user_id)
    refresh = security_manager.create_refresh_token(user_id)

    access_payload = security_manager.decode_access_token(access.token)
    refresh_payload = security_manager.decode_refresh_token(refresh.token)

    assert access_payload["type"] == "access"
    assert refresh_payload["type"] == "refresh"
    assert access_payload["sub"] == str(user_id)
    assert refresh_payload["sub"] == str(user_id)
    assert access_payload["jti"] != refresh_payload["jti"]


def test_refresh_token_cannot_be_decoded_as_access_token(security_manager: SecurityManager) -> None:
    refresh = security_manager.create_refresh_token(
        UUID("9be789b2-9cdc-4c46-a7cf-09d349faf44e")
    )

    with pytest.raises(AuthenticationError):
        security_manager.decode_access_token(refresh.token)
