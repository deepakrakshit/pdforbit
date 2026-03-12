from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class CommandExecutionError(RuntimeError):
    def __init__(self, *, command: list[str], message: str, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.command = tuple(command)
        self.stdout = stdout
        self.stderr = stderr


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: int = 60,
) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CommandExecutionError(command=command, message=f"Command not found: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise CommandExecutionError(
            command=command,
            message=f"Command timed out after {timeout_seconds} seconds.",
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
        ) from exc

    result = CommandResult(
        command=tuple(command),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if completed.returncode != 0:
        raise CommandExecutionError(
            command=command,
            message=f"Command exited with status {completed.returncode}.",
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    return result
