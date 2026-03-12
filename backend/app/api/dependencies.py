from collections.abc import Iterator
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.container import AppContainer
from app.core.rate_limit import RateLimitScope, RedisRateLimiter
from app.db.session import DatabaseManager
from app.db.repositories.job import JobRepository
from app.db.repositories.refresh_token import RefreshTokenRepository
from app.db.repositories.upload import UploadRepository
from app.db.repositories.user import UserRepository
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService
from app.services.download_service import DownloadService
from app.services.history_service import HistoryService
from app.services.job_service import JobService
from app.services.queue_service import QueueService
from app.services.storage_service import StorageService
from app.services.system_service import SystemService
from app.services.upload_service import UploadService
from app.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_system_service(
    container: Annotated[AppContainer, Depends(get_container)],
) -> SystemService:
    return container.system_service


def get_database_manager(
    container: Annotated[AppContainer, Depends(get_container)],
) -> DatabaseManager:
    return container.database_manager


def get_storage_service(
    container: Annotated[AppContainer, Depends(get_container)],
) -> StorageService:
    return container.storage_service


def get_queue_service(
    container: Annotated[AppContainer, Depends(get_container)],
) -> QueueService:
    return container.queue_service


def get_rate_limiter(
    container: Annotated[AppContainer, Depends(get_container)],
    queue_service: Annotated[QueueService, Depends(get_queue_service)],
) -> RedisRateLimiter:
    return RedisRateLimiter(settings=container.settings, connection=queue_service.connection)


def get_download_service(
    container: Annotated[AppContainer, Depends(get_container)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> DownloadService:
    return DownloadService(
        settings=container.settings,
        storage_service=storage_service,
    )


def get_db_session(
    database_manager: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> Iterator[Session]:
    yield from database_manager.get_session()


def get_user_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> UserRepository:
    return UserRepository(session)


def get_upload_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> UploadRepository:
    return UploadRepository(session)


def get_job_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> JobRepository:
    return JobRepository(session)


def get_refresh_token_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> RefreshTokenRepository:
    return RefreshTokenRepository(session)


def get_auth_service(
    session: Annotated[Session, Depends(get_db_session)],
    container: Annotated[AppContainer, Depends(get_container)],
) -> AuthService:
    return AuthService(
        session=session,
        settings=container.settings,
    )


def get_upload_service(
    session: Annotated[Session, Depends(get_db_session)],
    container: Annotated[AppContainer, Depends(get_container)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> UploadService:
    return UploadService(
        session=session,
        settings=container.settings,
        storage_service=storage_service,
    )


def get_job_service(
    session: Annotated[Session, Depends(get_db_session)],
    container: Annotated[AppContainer, Depends(get_container)],
    queue_service: Annotated[QueueService, Depends(get_queue_service)],
    download_service: Annotated[DownloadService, Depends(get_download_service)],
) -> JobService:
    return JobService(
        session=session,
        settings=container.settings,
        queue_service=queue_service,
        download_service=download_service,
    )


def get_history_service(
    session: Annotated[Session, Depends(get_db_session)],
    download_service: Annotated[DownloadService, Depends(get_download_service)],
) -> HistoryService:
    return HistoryService(
        session=session,
        download_service=download_service,
    )


def get_user_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> UserService:
    return UserService(session=session)


def get_billing_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> BillingService:
    return BillingService(session=session)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_service.get_current_user_from_access_token(credentials.credentials)


def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User | None:
    if credentials is None:
        return None
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_service.get_current_user_from_access_token(credentials.credentials)


def require_internal_api_access(
    request: Request,
    container: Annotated[AppContainer, Depends(get_container)],
) -> None:
    expected_secret = container.settings.billing_internal_api_secret
    provided_secret = request.headers.get("X-Internal-API-Secret", "")

    if not expected_secret or not secrets.compare_digest(provided_secret, expected_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Internal API authentication failed.",
        )


def enforce_upload_rate_limit(
    request: Request,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    rate_limiter: Annotated[RedisRateLimiter, Depends(get_rate_limiter)],
) -> None:
    rate_limiter.enforce(scope=RateLimitScope.UPLOADS, request=request, current_user=current_user)


def enforce_job_rate_limit(
    request: Request,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    rate_limiter: Annotated[RedisRateLimiter, Depends(get_rate_limiter)],
) -> None:
    rate_limiter.enforce(scope=RateLimitScope.JOBS, request=request, current_user=current_user)


def enforce_auth_rate_limit(
    request: Request,
    rate_limiter: Annotated[RedisRateLimiter, Depends(get_rate_limiter)],
) -> None:
    rate_limiter.enforce(scope=RateLimitScope.AUTH, request=request, current_user=None)
