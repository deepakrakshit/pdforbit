from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.models.enums import SubscriptionStatus, UserPlan
from app.models.user import User


class CreditService:
    ADMIN_CREDIT_LIMIT = 999_999_999
    FREE_DAILY_CREDITS = 30
    PRO_DAILY_CREDITS = 1000
    ENTERPRISE_DAILY_CREDITS = 10000

    TOOL_COSTS: dict[str, int] = {
        "merge": 1,
        "split": 1,
        "extract": 1,
        "remove": 1,
        "reorder": 1,
        "compress": 1,
        "repair": 1,
        "img2pdf": 1,
        "html2pdf": 1,
        "pdf2img": 1,
        "pdf2pdfa": 1,
        "rotate": 1,
        "watermark": 1,
        "pagenums": 1,
        "crop": 1,
        "unlock": 1,
        "protect": 1,
        "sign": 1,
        "redact": 1,
        "compare": 1,
        "ocr": 1,
        "word2pdf": 1,
        "excel2pdf": 1,
        "ppt2pdf": 1,
        "pdf2word": 1,
        "pdf2excel": 1,
        "pdf2ppt": 1,
        "translate": 5,
        "summarize": 5,
    }

    def initialize_user(self, user: User, *, now: datetime | None = None) -> None:
        current_time = now or datetime.now(timezone.utc)
        self.reconcile_subscription(user, now=current_time)
        if getattr(user, "plan", None) is None:
            user.plan = UserPlan.FREE
        if getattr(user, "last_credit_refresh", None) is None:
            user.last_credit_refresh = current_time
        if getattr(user, "credits_remaining", None) is None or user.is_admin:
            user.credits_remaining = self.get_user_credit_limit(user)

    def get_credit_limit(self, plan: UserPlan) -> int:
        if plan == UserPlan.FREE:
            return self.FREE_DAILY_CREDITS
        if plan == UserPlan.PRO:
            return self.PRO_DAILY_CREDITS
        return self.ENTERPRISE_DAILY_CREDITS

    def get_user_credit_limit(self, user: User) -> int:
        self.reconcile_subscription(user)
        if user.is_admin:
            return self.ADMIN_CREDIT_LIMIT
        return self.get_credit_limit(user.plan_type)

    def get_task_cost(self, tool_id: str) -> int:
        return self.TOOL_COSTS.get(tool_id, 1)

    def refresh_credits_if_due(self, user: User, *, now: datetime | None = None) -> bool:
        current_time = now or datetime.now(timezone.utc)
        self.initialize_user(user, now=current_time)

        if user.is_admin:
            if user.credits_remaining != self.ADMIN_CREDIT_LIMIT:
                user.credits_remaining = self.ADMIN_CREDIT_LIMIT
                user.last_credit_refresh = current_time
                return True
            return False

        refreshed_at = self._normalize(user.last_credit_refresh)

        if refreshed_at.date() >= current_time.date():
            return False

        user.credits_remaining = self.get_user_credit_limit(user)
        user.last_credit_refresh = current_time
        return True

    def reconcile_subscription(self, user: User, *, now: datetime | None = None) -> bool:
        current_time = now or datetime.now(timezone.utc)
        expires_at = getattr(user, "subscription_expires_at", None)

        if user.is_admin or expires_at is None or user.plan != UserPlan.PRO:
            return False

        normalized_expiry = self._normalize(expires_at)
        if normalized_expiry > current_time:
            if getattr(user, "subscription_status", None) != SubscriptionStatus.ACTIVE:
                user.subscription_status = SubscriptionStatus.ACTIVE
                return True
            return False

        user.plan = UserPlan.FREE
        user.subscription_status = SubscriptionStatus.EXPIRED
        user.subscription_interval = None
        user.subscription_started_at = None
        user.subscription_expires_at = normalized_expiry
        user.credits_remaining = min(getattr(user, "credits_remaining", 0), self.FREE_DAILY_CREDITS)
        return True

    def consume_credits(self, *, user: User, tool_id: str, now: datetime | None = None) -> int:
        if user.is_admin:
            self.refresh_credits_if_due(user, now=now)
            return 0

        self.refresh_credits_if_due(user, now=now)
        task_cost = self.get_task_cost(tool_id)

        if user.credits_remaining < task_cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits",
            )

        user.credits_remaining -= task_cost
        return task_cost

    @staticmethod
    def _normalize(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)