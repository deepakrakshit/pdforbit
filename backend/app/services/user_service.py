from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.repositories.job import JobRepository
from app.models.user import User
from app.schemas.user import UserProfileResponse
from app.services.credit_service import CreditService


class UserService:
    def __init__(self, *, session: Session) -> None:
        self._jobs = JobRepository(session)
        self._credits = CreditService()

    def get_profile(self, user: User) -> UserProfileResponse:
        return UserProfileResponse(
            id=user.id,
            email=user.email,
            plan_type=user.plan_type,
            is_admin=user.is_admin,
            credits_remaining=user.credits_remaining,
            credit_limit=self._credits.get_user_credit_limit(user),
            jobs_processed=self._jobs.count_completed_by_owner(owner_id=user.id),
            subscription_status=user.subscription_status,
            subscription_interval=user.subscription_interval,
            subscription_started_at=user.subscription_started_at,
            subscription_expires_at=user.subscription_expires_at,
            created_at=user.created_at,
            last_credit_refresh=user.last_credit_refresh,
        )