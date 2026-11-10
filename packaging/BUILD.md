# Construcción de distribuciones

Construir en cada plataforma objetivo:

1. Ejecutar `uv sync`.
2. En macOS Apple Silicon, ejecutar `uv run python packaging/fetch_libreoffice.py`.
   En las demás plataformas, obtener el runtime oficial equivalente.
3. Descomprimirlo como `runtime/libreoffice/` conservando su estructura de
   aplicación (`program/soffice` en Windows/Linux). En macOS debe conservarse
   como `runtime/LibreOffice.app/Contents/MacOS/soffice`.
4. Ejecutar `uv run python packaging/build_pyinstaller.py`.
5. Probar en un equipo sin Python, uv, PySide6 ni LibreOffice instalados.

El paquete final debe incluir el ejecutable generado, `assets/` y
`runtime/libreoffice/`. No incluir documentos reales ni la carpeta de desarrollo.

El comando debe ejecutarse en el sistema que se va a distribuir. Produce una
carpeta independiente (`*.dist` en Windows/Linux o una aplicación en macOS).
Para entregar un instalador visual, esa carpeta puede envolverse con la
herramienta nativa de cada plataforma (MSIX/installer de Windows, DMG/PKG en
macOS o AppImage/deb en Linux).
