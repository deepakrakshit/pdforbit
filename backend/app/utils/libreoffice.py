from __future__ import annotations

import shutil
from pathlib import Path

from app.utils.subprocesses import CommandExecutionError, run_command


class LibreOfficeUnavailableError(RuntimeError):
    pass


class LibreOfficeConversionError(RuntimeError):
    pass


LIBREOFFICE_CANDIDATES = ("libreoffice", "soffice", "soffice.com", "soffice.exe")


def find_libreoffice_binary() -> str | None:
    for candidate in LIBREOFFICE_CANDIDATES:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def convert_with_libreoffice(
    source_path: Path,
    *,
    output_dir: Path,
    target_format: str,
    timeout_seconds: int = 120,
) -> Path:
    binary = find_libreoffice_binary()
    if binary is None:
        raise LibreOfficeUnavailableError("LibreOffice is not available on this server.")

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        run_command(
            [
                binary,
                "--headless",
                "--convert-to",
                target_format,
                "--outdir",
                str(output_dir),
                str(source_path),
            ],
            cwd=output_dir,
            timeout_seconds=timeout_seconds,
        )
    except CommandExecutionError as exc:
        raise LibreOfficeConversionError("LibreOffice failed to convert the source document.") from exc

    extension = "." + target_format.split(":", 1)[0].split(";", 1)[0].strip().lower()
    output_path = output_dir / f"{source_path.stem}{extension}"
    if not output_path.exists():
        candidates = sorted(output_dir.glob(f"{source_path.stem}.*"))
        if candidates:
            output_path = candidates[0]
    if not output_path.exists():
        raise LibreOfficeConversionError("LibreOffice did not produce an output file.")
    return output_path