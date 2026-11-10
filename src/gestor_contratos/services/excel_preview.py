"""Render generated Excel workbooks for visual preview."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class ExcelPreviewError(Exception):
    """Raised when an Excel workbook cannot be rendered for preview."""


class ExcelPreviewRenderer:
    """Convert an in-memory workbook to a temporary PDF using LibreOffice."""

    def __init__(self, office_command: str | None = None) -> None:
        self.office_command = office_command or self._find_office_command()

    @staticmethod
    def _find_office_command() -> str | None:
        source_root = Path(__file__).resolve().parents[3]
        executable_root = Path(sys.executable).resolve().parent
        bundled_roots = (
            source_root / "runtime" / "LibreOffice.app" / "Contents",
            source_root / "runtime" / "libreoffice",
            executable_root / "runtime" / "libreoffice",
            executable_root / "runtime" / "LibreOffice.app" / "Contents",
            executable_root.parent / "runtime" / "libreoffice",
            executable_root.parent / "runtime" / "LibreOffice.app" / "Contents",
            executable_root.parent / "Resources" / "runtime" / "libreoffice",
            executable_root.parent
            / "Resources"
            / "runtime"
            / "LibreOffice.app"
            / "Contents",
            executable_root.parent.parent / "runtime" / "libreoffice",
            executable_root.parent.parent / "runtime" / "LibreOffice.app" / "Contents",
        )
        bundled_commands = tuple(
            command
            for root in bundled_roots
            for command in (
                root / "program" / "soffice",
                root / "program" / "soffice.exe",
                root / "MacOS" / "soffice",
            )
            if command.is_file()
        )
        candidates = (
            *(str(command) for command in bundled_commands),
            os.environ.get("LIBREOFFICE_PATH"),
            shutil.which("soffice"),
            shutil.which("libreoffice"),
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            "/opt/homebrew/bin/soffice",
            "/usr/local/bin/soffice",
        )
        return next(
            (
                candidate
                for candidate in candidates
                if candidate and Path(candidate).is_file()
            ),
            None,
        )

    def render(self, excel_bytes: bytes) -> bytes:
        """Return a PDF preview without persisting files in the project."""
        if self.office_command is None:
            raise ExcelPreviewError(
                "No se encontró LibreOffice. Instálelo para previsualizar el Excel."
            )

        with tempfile.TemporaryDirectory(
            prefix="gestor_contratos_preview_"
        ) as directory:
            temporary_dir = Path(directory)
            source = temporary_dir / "acta_entrega_preview.xlsx"
            profile = temporary_dir / "libreoffice_profile"
            source.write_bytes(excel_bytes)
            try:
                subprocess.run(
                    [
                        self.office_command,
                        f"-env:UserInstallation={profile.as_uri()}",
                        "--headless",
                        "--invisible",
                        "--nodefault",
                        "--norestore",
                        "--nolockcheck",
                        "--convert-to",
                        "pdf:calc_pdf_Export",
                        "--outdir",
                        str(temporary_dir),
                        str(source),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=60,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise ExcelPreviewError(
                    "No fue posible convertir el Excel para previsualización. "
                    "Verifique que LibreOffice esté instalado y que "
                    "LIBREOFFICE_PATH apunte a su ejecutable."
                ) from exc

            pdf_path = source.with_suffix(".pdf")
            if not pdf_path.is_file():
                raise ExcelPreviewError(
                    "LibreOffice no generó el PDF de previsualización."
                )
            return pdf_path.read_bytes()
