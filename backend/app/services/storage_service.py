from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import AppSettings


class StorageService:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._root = settings.files_root
        self._uploads_root = self._root / "uploads"
        self._artifacts_root = self._root / "artifacts"
        self._tmp_root = self._root / "tmp"
        self.ensure_directories()

    @property
    def root(self) -> Path:
        return self._root

    def ensure_directories(self) -> None:
        for path in (self._root, self._uploads_root, self._artifacts_root, self._tmp_root):
            path.mkdir(parents=True, exist_ok=True)

    def ping(self) -> None:
        self.ensure_directories()
        probe = self._tmp_root / f".probe-{uuid4().hex}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)

    def create_temporary_upload_path(self, suffix: str = ".upload") -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return self._tmp_root / f"{timestamp}-{uuid4().hex}{suffix}"

    def create_job_workspace(self, *, job_public_id: str) -> Path:
        workspace = self._tmp_root / "jobs" / job_public_id / uuid4().hex
        workspace.mkdir(parents=True, exist_ok=False)
        return workspace

    def build_upload_relative_path(
        self,
        *,
        public_id: str,
        extension: str,
        created_at: datetime,
    ) -> str:
        normalized_extension = extension if extension.startswith(".") else f".{extension}"
        relative_path = (
            Path("uploads")
            / created_at.strftime("%Y")
            / created_at.strftime("%m")
            / created_at.strftime("%d")
            / f"{public_id}{normalized_extension}"
        )
        return relative_path.as_posix()

    def build_artifact_relative_path(
        self,
        *,
        job_public_id: str,
        filename: str,
        created_at: datetime,
    ) -> str:
        relative_path = (
            Path("artifacts")
            / created_at.strftime("%Y")
            / created_at.strftime("%m")
            / created_at.strftime("%d")
            / job_public_id
            / filename
        )
        return relative_path.as_posix()

    def commit_temp_file(self, *, temp_path: Path, relative_path: str) -> Path:
        destination = self._root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temp_path, destination)
        return destination

    def resolve_path(self, *, relative_path: str) -> Path:
        return self._root / relative_path

    def delete(self, *, relative_path: str) -> None:
        target = self._root / relative_path
        target.unlink(missing_ok=True)

    def delete_tree(self, *, target: Path) -> None:
        shutil.rmtree(target, ignore_errors=True)
