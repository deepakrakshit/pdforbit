from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.repositories.base import SQLAlchemyRepository
from app.models.refresh_token import RefreshToken


class RefreshTokenRepository(SQLAlchemyRepository[RefreshToken]):
    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=RefreshToken)

    def get_active_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        statement = (
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .where(RefreshToken.revoked_at.is_(None))
            .where(RefreshToken.expires_at > datetime.now(timezone.utc))
            .limit(1)
        )
        return self.session.scalar(statement)

    def revoke(self, refresh_token: RefreshToken) -> RefreshToken:
        refresh_token.revoked_at = datetime.now(timezone.utc)
        self.session.add(refresh_token)
        return refresh_token
