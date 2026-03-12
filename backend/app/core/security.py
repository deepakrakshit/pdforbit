from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

import bcrypt
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import AppSettings


class AuthenticationError(Exception):
    pass


@dataclass(frozen=True)
class EncodedToken:
    token: str
    expires_at: datetime
    jti: str


class SecurityManager:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._password_hasher = PasswordHasher()

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, password_hash: str) -> bool:
        if password_hash.startswith("$2"):
            try:
                return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
            except ValueError:
                return False

        try:
            return self._password_hasher.verify(password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    def hash_refresh_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_access_token(self, user_id: UUID) -> EncodedToken:
        return self._encode_token(
            subject=user_id,
            secret=self._settings.jwt_access_secret,
            ttl=timedelta(minutes=self._settings.jwt_access_ttl_minutes),
            token_type="access",
        )

    def create_refresh_token(self, user_id: UUID) -> EncodedToken:
        return self._encode_token(
            subject=user_id,
            secret=self._settings.jwt_refresh_secret,
            ttl=timedelta(days=self._settings.jwt_refresh_ttl_days),
            token_type="refresh",
        )

    def decode_access_token(self, token: str) -> dict[str, Any]:
        return self._decode_token(token, self._settings.jwt_access_secret, expected_type="access")

    def decode_refresh_token(self, token: str) -> dict[str, Any]:
        return self._decode_token(token, self._settings.jwt_refresh_secret, expected_type="refresh")

    def _encode_token(
        self,
        *,
        subject: UUID,
        secret: str,
        ttl: timedelta,
        token_type: Literal["access", "refresh"],
    ) -> EncodedToken:
        now = datetime.now(timezone.utc)
        expires_at = now + ttl
        jti = uuid4().hex
        payload = {
            "sub": str(subject),
            "type": token_type,
            "jti": jti,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self._settings.app_name,
        }
        token = jwt.encode(payload, secret, algorithm="HS256")
        return EncodedToken(token=token, expires_at=expires_at, jti=jti)

    def _decode_token(
        self,
        token: str,
        secret: str,
        *,
        expected_type: Literal["access", "refresh"],
    ) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"require": ["exp", "iat", "nbf", "sub", "jti", "type"]},
                issuer=self._settings.app_name,
            )
        except ExpiredSignatureError as exc:
            raise AuthenticationError("Token has expired.") from exc
        except InvalidTokenError as exc:
            raise AuthenticationError("Token is invalid.") from exc

        if payload.get("type") != expected_type:
            raise AuthenticationError("Token type is invalid.")

        return payload
