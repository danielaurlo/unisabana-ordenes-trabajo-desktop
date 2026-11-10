"""Download the official LibreOffice runtime for the current Mac ARM host."""

from __future__ import annotations

import hashlib
import platform
import plistlib
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "26.8.2"
DOWNLOAD = (
    "https://download.documentfoundation.org/libreoffice/stable/"
    f"{VERSION}/mac/aarch64/LibreOffice_{VERSION}_MacOS_aarch64.dmg"
)
EXPECTED_SHA256 = "9f24fe83ab1ed5c95eb3df580119f32932f713e577feeac02bf619fb00749b55"


def main() -> None:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit(
            "Este descargador cubre macOS Apple Silicon. "
            "Obtenga el runtime oficial equivalente para Windows, Linux o macOS Intel."
        )

    with tempfile.TemporaryDirectory(prefix="gestor_contratos_lo_") as temp:
        temp_dir = Path(temp)
        image = temp_dir / "LibreOffice.dmg"
        print(f"Descargando LibreOffice {VERSION}…")
        urllib.request.urlretrieve(DOWNLOAD, image)
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if digest != EXPECTED_SHA256:
            raise SystemExit("La suma SHA-256 de LibreOffice no coincide.")

        plist = temp_dir / "attach.plist"
        with plist.open("wb") as output:
            subprocess.run(
                ["hdiutil", "attach", "-nobrowse", "-readonly", "-plist", str(image)],
                check=True,
                stdout=output,
            )
        metadata = plistlib.loads(plist.read_bytes())
        mount_point = next(
            entity["mount-point"]
            for entity in metadata["system-entities"]
            if entity.get("mount-point")
        )
        try:
            destination = ROOT / "runtime" / "LibreOffice.app"
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(
                Path(mount_point) / "LibreOffice.app",
                destination,
            )
        finally:
            subprocess.run(["hdiutil", "detach", mount_point], check=False)

    print(f"Runtime instalado en {ROOT / 'runtime' / 'LibreOffice.app'}")


if __name__ == "__main__":
    main()
