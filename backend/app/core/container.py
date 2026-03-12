from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging

from app.core.config import AppSettings
from app.core.security import SecurityManager
from app.db.session import DatabaseManager
from app.db.repositories.user import UserRepository
from app.models.user import User
from app.services.credit_service import CreditService
from app.services.queue_service import QueueService
from app.services.storage_service import StorageService
from app.services.system_service import SystemService


@dataclass(slots=True)
class AppContainer:
    settings: AppSettings
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    database_manager: DatabaseManager = field(init=False)
    queue_service: QueueService = field(init=False)
    storage_service: StorageService = field(init=False)
    system_service: SystemService = field(init=False)

    def __post_init__(self) -> None:
        self.database_manager = DatabaseManager(settings=self.settings)
        self.queue_service = QueueService(settings=self.settings)
        self.storage_service = StorageService(settings=self.settings)
        self.system_service = SystemService(
            settings=self.settings,
            started_at=self.started_at,
            database_manager=self.database_manager,
            queue_service=self.queue_service,
            storage_service=self.storage_service,
        )

    def dispose(self) -> None:
        self.database_manager.dispose()

    def provision_internal_admin(self) -> None:
        if not self.settings.internal_admin_enabled:
            return

        logger = logging.getLogger("app.auth")
        security = SecurityManager(self.settings)
        credits = CreditService()
        legacy_admin_email = "admin@pdforbit.dev"

        with self.database_manager.session_scope() as session:
            users = UserRepository(session)
            user = users.get_by_email(self.settings.internal_admin_email or "")
            if user is None and self.settings.internal_admin_email and self.settings.internal_admin_email != legacy_admin_email:
                legacy_user = users.get_by_email(legacy_admin_email)
                if legacy_user is not None and legacy_user.is_admin:
                    legacy_user.email = self.settings.internal_admin_email
                    session.add(legacy_user)
                    user = legacy_user
                    logger.info(
                        "internal_admin.renamed",
                        extra={"from_email": legacy_admin_email, "to_email": user.email},
                    )

            if user is None:
                user = User(
                    email=self.settings.internal_admin_email or "",
                    password_hash=security.hash_password(self.settings.internal_admin_password or ""),
                    is_active=True,
                    is_verified=True,
                    is_admin=True,
                )
                credits.initialize_user(user)
                users.add(user)
                logger.info("internal_admin.created", extra={"email": user.email})
                return

            user.password_hash = security.hash_password(self.settings.internal_admin_password or "")
            user.is_active = True
            user.is_verified = True
            user.is_admin = True
            credits.initialize_user(user)
            user.credits_remaining = credits.ADMIN_CREDIT_LIMIT
            session.add(user)
            logger.info("internal_admin.updated", extra={"email": user.email})
