from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import AppSettings
from app.core.security import AuthenticationError, SecurityManager
from app.db.repositories.refresh_token import RefreshTokenRepository
from app.db.repositories.user import UserRepository
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import AuthenticatedUser, LoginRequest, RegisterRequest, TokenPairResponse
from app.services.credit_service import CreditService


class AuthService:
    def __init__(self, session: Session, settings: AppSettings) -> None:
        self._session = session
        self._settings = settings
        self._security = SecurityManager(settings)
        self._credits = CreditService()
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)

    def register(self, payload: RegisterRequest) -> TokenPairResponse:
        self._validate_password(payload.password)
        user = User(
            email=payload.email,
            password_hash=self._security.hash_password(payload.password),
        )
        self._credits.initialize_user(user)
        self._users.add(user)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with that email already exists.",
            ) from exc

        token_pair = self._issue_token_pair(user)
        self._session.commit()
        self._session.refresh(user)
        return token_pair

    def login(self, payload: LoginRequest) -> TokenPairResponse:
        user = self._users.get_by_email(payload.email)
        if user is None or not self._security.verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is disabled.",
            )

        token_pair = self._issue_token_pair(user)
        self._session.commit()
        self._session.refresh(user)
        return token_pair

    def refresh(self, refresh_token: str) -> TokenPairResponse:
        payload = self._decode_refresh_token(refresh_token)
        token_hash = self._security.hash_refresh_token(refresh_token)
        stored_token = self._refresh_tokens.get_active_by_token_hash(token_hash)
        if stored_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is invalid or has been revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = self._users.get(UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is no longer available.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        self._refresh_tokens.revoke(stored_token)
        token_pair = self._issue_token_pair(user)
        self._session.commit()
        self._session.refresh(user)
        return token_pair

    def logout(self, refresh_token: str) -> None:
        try:
            self._decode_refresh_token(refresh_token)
        except HTTPException:
            raise

        stored_token = self._refresh_tokens.get_active_by_token_hash(
            self._security.hash_refresh_token(refresh_token)
        )
        if stored_token is not None:
            self._refresh_tokens.revoke(stored_token)
            self._session.commit()

    def get_current_user_from_access_token(self, access_token: str) -> User:
        try:
            payload = self._security.decode_access_token(access_token)
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        user = self._users.get(UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is no longer available.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if self._credits.refresh_credits_if_due(user):
            self._session.commit()
            self._session.refresh(user)
        return user

    def get_authenticated_user(self, user: User) -> AuthenticatedUser:
        return AuthenticatedUser.model_validate(user)

    def _issue_token_pair(self, user: User) -> TokenPairResponse:
        access_token = self._security.create_access_token(user.id)
        refresh_token = self._security.create_refresh_token(user.id)
        self._refresh_tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=self._security.hash_refresh_token(refresh_token.token),
                expires_at=refresh_token.expires_at,
            )
        )
        return TokenPairResponse(
            access_token=access_token.token,
            refresh_token=refresh_token.token,
            access_token_expires_at=access_token.expires_at,
            refresh_token_expires_at=refresh_token.expires_at,
            user=AuthenticatedUser.model_validate(user),
        )

    def _decode_refresh_token(self, refresh_token: str) -> dict[str, str]:
        try:
            return self._security.decode_refresh_token(refresh_token)
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    def _validate_password(self, password: str) -> None:
        if len(password) < self._settings.password_min_length:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Password must be at least {self._settings.password_min_length} characters long.",
            )
