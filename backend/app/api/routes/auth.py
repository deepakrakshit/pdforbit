from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import enforce_auth_rate_limit, get_auth_service, get_current_user
from app.models.user import User
from app.schemas.auth import (
    AuthenticatedUser,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenPairResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=TokenPairResponse, status_code=status.HTTP_201_CREATED)
@router.post("/signup", response_model=TokenPairResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _: Annotated[None, Depends(enforce_auth_rate_limit)],
) -> TokenPairResponse:
    return auth_service.register(payload)


@router.post("/login", response_model=TokenPairResponse)
def login(
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _: Annotated[None, Depends(enforce_auth_rate_limit)],
) -> TokenPairResponse:
    return auth_service.login(payload)


@router.post("/refresh", response_model=TokenPairResponse)
def refresh(
    payload: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _: Annotated[None, Depends(enforce_auth_rate_limit)],
) -> TokenPairResponse:
    return auth_service.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    auth_service.logout(payload.refresh_token)


@router.get("/me", response_model=AuthenticatedUser)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> AuthenticatedUser:
    return AuthenticatedUser.model_validate(current_user)
