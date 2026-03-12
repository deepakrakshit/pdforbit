from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class SQLAlchemyRepository(Generic[ModelT]):
    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        return instance

    def get(self, entity_id: Any) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def get_one_by(self, **filters: Any) -> ModelT | None:
        statement = select(self.model).filter_by(**filters).limit(1)
        return self.session.scalar(statement)

    def list(
        self,
        *criteria: Any,
        order_by: Any | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ModelT]:
        statement: Select[tuple[ModelT]] = select(self.model)
        if criteria:
            statement = statement.where(*criteria)
        if order_by is not None:
            statement = statement.order_by(order_by)
        if offset:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.session.scalars(statement))

    def remove(self, instance: ModelT) -> None:
        self.session.delete(instance)

