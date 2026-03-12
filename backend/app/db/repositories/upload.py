from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.orm import Session

from app.db.repositories.base import SQLAlchemyRepository
from app.models.upload import Upload


class UploadRepository(SQLAlchemyRepository[Upload]):
    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=Upload)

    def get_by_public_id(self, public_id: str) -> Upload | None:
        return self.get_one_by(public_id=public_id)

    def list_by_owner(self, *, owner_id, limit: int, offset: int = 0) -> list[Upload]:
        statement = (
            select(Upload)
            .where(Upload.owner_user_id == owner_id)
            .order_by(Upload.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def count_by_owner(self, *, owner_id) -> int:
        statement = select(func.count()).select_from(Upload).where(Upload.owner_user_id == owner_id)
        return int(self.session.scalar(statement) or 0)

    def list_expired_active(self, *, before: datetime) -> list[Upload]:
        statement = (
            select(Upload)
            .where(Upload.deleted_at.is_(None), Upload.expires_at <= before)
            .order_by(Upload.expires_at.asc())
        )
        return list(self.session.scalars(statement))
