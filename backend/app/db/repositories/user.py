from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.repositories.base import SQLAlchemyRepository
from app.models.user import User


class UserRepository(SQLAlchemyRepository[User]):
    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=User)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(func.lower(User.email) == email.strip().lower()).limit(1)
        return self.session.scalar(statement)

