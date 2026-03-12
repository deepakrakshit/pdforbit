from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_user_service
from app.models.user import User
from app.schemas.user import UserProfileResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users")


@router.get("/me", response_model=UserProfileResponse)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserProfileResponse:
    return user_service.get_profile(current_user)