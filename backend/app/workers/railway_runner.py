from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
from collections.abc import Sequence

from app.core.config import build_settings
from app.core.logging import configure_logging


def run_release_command() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def spawn_process(command: Sequence[str]) -> subprocess.Popen[str]:
    return subprocess.Popen(command)


def terminate_processes(processes: list[subprocess.Popen[str]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main() -> None:
    settings = build_settings()
    configure_logging(settings)
    logger = logging.getLogger("app.railway")

    run_release_command()

    port = str(os.getenv("PORT", settings.port))
    commands = [
        [sys.executable, "-m", "app.workers.rq_app"],
        [sys.executable, "-m", "app.workers.cleanup"],
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
    ]
    processes = [spawn_process(command) for command in commands]

    def handle_shutdown(signum: int, _frame: object) -> None:
        logger.info("railway.shutdown", extra={"signal": signum})
        terminate_processes(processes)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    while True:
        for index, process in enumerate(processes):
            return_code = process.poll()
            if return_code is None:
                continue

            logger.error(
                "railway.process_exited",
                extra={
                    "command": " ".join(commands[index]),
                    "return_code": return_code,
                },
            )
            terminate_processes(processes)
            raise SystemExit(return_code)


if __name__ == "__main__":
    main()