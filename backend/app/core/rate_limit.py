from __future__ import annotations

from enum import Enum
from ipaddress import ip_address

from fastapi import HTTPException, Request, status
from redis import Redis

from app.core.config import AppSettings
from app.models.user import User


class RateLimitScope(str, Enum):
    AUTH = "auth"
    UPLOADS = "uploads"
    JOBS = "jobs"


class RedisRateLimiter:
    def __init__(self, *, settings: AppSettings, connection: Redis) -> None:
        self._settings = settings
        self._connection = connection

    def enforce(self, *, scope: RateLimitScope, request: Request, current_user: User | None) -> None:
        limit = self._resolve_limit(scope=scope, current_user=current_user)
        if limit <= 0:
            return

        actor_kind, actor_id = self._resolve_actor(request=request, current_user=current_user)
        bucket = self._build_bucket(scope=scope, actor_kind=actor_kind, actor_id=actor_id)
        current = int(self._connection.incr(bucket))
        if current == 1:
            self._connection.expire(bucket, 3600)

        if current <= limit:
            return

        retry_after = max(int(self._connection.ttl(bucket)), 1)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {scope.value}. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    def _resolve_limit(self, *, scope: RateLimitScope, current_user: User | None) -> int:
        if scope == RateLimitScope.AUTH:
            return self._settings.rate_limit_auth_attempts_per_hour
        if scope == RateLimitScope.UPLOADS:
            base = self._settings.rate_limit_uploads_per_hour
        else:
            base = self._settings.rate_limit_jobs_per_hour

        if current_user is None:
            return base
        return base * self._settings.rate_limit_authenticated_multiplier

    @staticmethod
    def _resolve_actor(*, request: Request, current_user: User | None) -> tuple[str, str]:
        if current_user is not None:
            return "user", str(current_user.id)

        forwarded_for = request.headers.get("X-Forwarded-For", "")
        first_hop = forwarded_for.split(",", 1)[0].strip()
        raw_ip = first_hop or (request.client.host if request.client else "127.0.0.1")
        try:
            normalized_ip = ip_address(raw_ip).compressed
        except ValueError:
            normalized_ip = raw_ip or "unknown"
        return "ip", normalized_ip

    @staticmethod
    def _build_bucket(*, scope: RateLimitScope, actor_kind: str, actor_id: str) -> str:
        return f"rate-limit:{scope.value}:{actor_kind}:{actor_id}"