from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.orm import Session, selectinload

from app.db.repositories.base import SQLAlchemyRepository
from app.models.job import Job
from app.models.job_input import JobInput
from app.models.user import User


class JobRepository(SQLAlchemyRepository[Job]):
    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=Job)

    def get_by_public_id(self, public_id: str) -> Job | None:
        statement = (
            select(Job)
            .where(Job.public_id == public_id)
            .options(
                selectinload(Job.inputs).selectinload(JobInput.upload),
                selectinload(Job.artifacts),
                selectinload(Job.events),
            )
            .limit(1)
        )
        return self.session.scalar(statement)

    def list_by_owner(self, *, owner_id, limit: int, offset: int = 0) -> list[Job]:
        statement = (
            select(Job)
            .where(Job.owner_user_id == owner_id)
            .options(
                selectinload(Job.inputs).selectinload(JobInput.upload),
                selectinload(Job.artifacts),
                selectinload(Job.events),
            )
            .order_by(Job.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def count_by_owner(self, *, owner_id) -> int:
        statement = select(func.count()).select_from(Job).where(Job.owner_user_id == owner_id)
        return int(self.session.scalar(statement) or 0)

    def count_completed_by_owner(self, *, owner_id) -> int:
        statement = select(func.count()).select_from(Job).where(
            Job.owner_user_id == owner_id,
            Job.status == "completed",
        )
        return int(self.session.scalar(statement) or 0)

    def list_stale_pending(self, *, before: datetime) -> list[Job]:
        statement = (
            select(Job)
            .where(Job.status == "pending", Job.created_at <= before)
            .options(
                selectinload(Job.inputs).selectinload(JobInput.upload),
                selectinload(Job.artifacts),
                selectinload(Job.events),
            )
            .order_by(Job.created_at.asc())
        )
        return list(self.session.scalars(statement))

    def list_stale_processing(self, *, before: datetime) -> list[Job]:
        statement = (
            select(Job)
            .where(Job.status == "processing", Job.started_at.is_not(None), Job.started_at <= before)
            .options(
                selectinload(Job.inputs).selectinload(JobInput.upload),
                selectinload(Job.artifacts),
                selectinload(Job.events),
            )
            .order_by(Job.started_at.asc())
        )
        return list(self.session.scalars(statement))
