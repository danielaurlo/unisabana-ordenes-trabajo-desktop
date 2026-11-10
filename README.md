# Gestor de Contratos — aplicación de escritorio

Migración local de la aplicación Streamlit. Esta versión usa Qt/PySide6, procesa los documentos en el equipo del usuario y no inicia ningún servidor web.

## Desarrollo

Requiere Python 3.11–3.13 y `uv`:

```bash
uv sync
uv run python main.py
```

La lógica de extracción, validación, generación de Excel y combinación PDF se comparte con el proyecto original. La interfaz permite seleccionar una orden, procesarla, revisar/corregir datos y guardar el Excel y el PDF final.

## Distribución

La aplicación debe construirse en cada sistema operativo objetivo (Windows, macOS y Linux). El resultado es un paquete independiente para ese sistema; no se debe copiar un ejecutable de Windows a macOS o Linux.

Con PyInstaller instalado se puede generar el paquete con:

```bash
uv run python packaging/build_pyinstaller.py
```

El script prepara automáticamente el runtime de LibreOffice desde la instalación
local del sistema antes de compilar. Por eso cada compilación debe hacerse en el
sistema operativo destino: macOS genera un `.dmg` y Windows un `.zip` portable.

En macOS genera `GestorContratos-macos-arm64.dmg`. En Windows genera la
carpeta `dist/GestorContratos` y un ZIP portable; el instalador `.exe` puede
crearse a partir de esa carpeta con Inno Setup o WiX en un equipo Windows.

Se recomienda ejecutar el empaquetado en una máquina limpia y probar el resultado antes de entregarlo.

### Conversión Excel a PDF

La plantilla Excel se genera sin dependencias externas. Para generar la previsualización del acta y el PDF combinado, la distribución debe incluir el motor LibreOffice portable en:

```text
runtime/LibreOffice.app/
```

El ejecutable esperado es `runtime/libreoffice/program/soffice` en Windows/Linux
(`soffice.exe` en Windows) o
`runtime/LibreOffice.app/Contents/MacOS/soffice` en macOS. En macOS se debe
conservar el bundle completo `.app`; no se deben copiar solamente sus archivos
internos. Si no se encuentra, la aplicación aún puede generar el Excel, pero
mostrará un error al generar el PDF final. El motor debe distribuirse
respetando su licencia y empaquetarse por separado para cada sistema operativo.

En desarrollo también puede indicarse una instalación local mediante `LIBREOFFICE_PATH`:

```bash
export LIBREOFFICE_PATH="/Applications/LibreOffice.app/Contents/MacOS/soffice"
uv run python main.py
```

## Estructura

- `main.py`: punto de entrada de escritorio.
- `src/gestor_contratos/desktop.py`: interfaz Qt y coordinación del flujo.
- `src/gestor_contratos/services/`: lógica reutilizada del proyecto original.
- `assets/`: plantilla y branding institucional.
- `runtime/`: ubicación reservada para runtimes portables incluidos en la distribución.
