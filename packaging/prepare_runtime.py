"""Prepare the platform-specific LibreOffice runtime for packaging."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"


def runtime_source() -> tuple[Path | None, Path]:
    if sys.platform == "darwin":
        return Path("/Applications/LibreOffice.app"), RUNTIME / "LibreOffice.app"
    if sys.platform == "win32":
        candidates = (
            Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
            / "LibreOffice",
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Programs"
            / "LibreOffice",
        )
        return next((path for path in candidates if path.is_dir()), None), (
            RUNTIME / "libreoffice"
        )
    return None, RUNTIME / "libreoffice"


def main() -> None:
    source, destination = runtime_source()
    if source is None or not source.is_dir():
        if sys.platform == "darwin":
            instructions = "Instale LibreOffice en /Applications/LibreOffice.app."
        elif sys.platform == "win32":
            instructions = "Instale LibreOffice en Program Files."
        else:
            instructions = "Instale LibreOffice en el sistema."
        raise SystemExit(f"No se encontró LibreOffice. {instructions}")

    executable = (
        destination / "Contents" / "MacOS" / "soffice"
        if sys.platform == "darwin"
        else destination / "program" / "soffice.exe"
    )
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    if not executable.is_file():
        shutil.rmtree(destination)
        raise SystemExit(f"El runtime no contiene el ejecutable esperado: {executable}")
    print(f"Runtime preparado: {destination}")


if __name__ == "__main__":
    main()
