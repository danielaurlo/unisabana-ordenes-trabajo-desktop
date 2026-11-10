"""Build the desktop distribution with PyInstaller."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "GestorContratos"
DIST = ROOT / "dist"
WORK = ROOT / "build"


def run() -> Path:
    prepare_runtime()
    separator = os.pathsep
    command = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name",
        NAME,
        "--paths",
        str(ROOT / "src"),
        "--add-data",
        f"{ROOT / 'assets'}{separator}assets",
        "--hidden-import",
        "PySide6.QtPdf",
        "--hidden-import",
        "PySide6.QtPdfWidgets",
        str(ROOT / "main.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)

    if sys.platform == "darwin":
        bundle = DIST / f"{NAME}.app"
        resource_root = bundle / "Contents" / "Resources"
    else:
        bundle = DIST / NAME
        resource_root = bundle
    if not bundle.exists():
        raise SystemExit(f"PyInstaller no generó la distribución: {bundle}")

    copy_runtime(resource_root)
    if sys.platform == "darwin":
        dmg = ROOT / f"{NAME}-macos-arm64.dmg"
        subprocess.run(
            [
                "hdiutil",
                "create",
                "-volname",
                NAME,
                "-srcfolder",
                str(bundle),
                "-ov",
                "-format",
                "UDZO",
                str(dmg),
            ],
            check=True,
        )
        print(f"DMG generado: {dmg}")
    else:
        archive = shutil.make_archive(str(ROOT / f"{NAME}-windows-x64"), "zip", bundle)
        print(f"ZIP portable generado: {archive}")
    return bundle


def copy_runtime(resource_root: Path) -> None:
    source_app = ROOT / "runtime" / "LibreOffice.app"
    source_directory = ROOT / "runtime" / "libreoffice"
    if source_app.is_dir():
        destination = resource_root / "runtime" / "LibreOffice.app"
        shutil.copytree(source_app, destination, dirs_exist_ok=True)
        return
    if source_directory.is_dir():
        destination = resource_root / "runtime" / "libreoffice"
        shutil.copytree(source_directory, destination, dirs_exist_ok=True)
        return
    print(
        "ADVERTENCIA: no se encontró runtime de LibreOffice. "
        "El Excel funcionará, pero no el PDF combinado."
    )


def prepare_runtime() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "packaging" / "prepare_runtime.py")],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    run()
