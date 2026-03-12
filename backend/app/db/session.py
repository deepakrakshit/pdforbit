from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import AppSettings


def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class DatabaseManager:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._url = make_url(settings.database_url)
        connect_args: dict[str, object] = {}

        if self._url.get_backend_name() == "sqlite":
            connect_args["check_same_thread"] = False

        self.engine: Engine = create_engine(
            self._url.render_as_string(hide_password=False),
            echo=settings.database_echo,
            pool_pre_ping=self._url.get_backend_name() != "sqlite",
            connect_args=connect_args,
        )

        if self._url.get_backend_name() == "sqlite":
            event.listen(self.engine, "connect", _set_sqlite_pragma)

        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )

    @property
    def url(self) -> URL:
        return self._url

    def ping(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        self.engine.dispose()
