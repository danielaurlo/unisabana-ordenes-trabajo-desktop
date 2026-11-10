"""Configurable mapping from extracted data to the institutional workbook."""

import sys
from dataclasses import dataclass
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[3]
_EXECUTABLE_ROOT = Path(sys.executable).resolve().parent
PROJECT_ROOT = next(
    (
        root
        for root in (
            _SOURCE_ROOT,
            _EXECUTABLE_ROOT / "_internal",
            _EXECUTABLE_ROOT,
            _EXECUTABLE_ROOT.parent,
            _EXECUTABLE_ROOT.parent / "Resources",
            _EXECUTABLE_ROOT.parent.parent,
        )
        if (root / "assets" / "plantilla" / "acta_entrega_vacia.xlsx").is_file()
    ),
    _SOURCE_ROOT,
)
DEFAULT_TEMPLATE_PATH = (
    PROJECT_ROOT / "assets" / "plantilla" / "acta_entrega_vacia.xlsx"
)


@dataclass(frozen=True)
class ExcelCellTarget:
    """Destination cell for a field from the normalized order model."""

    sheet: str
    cell: str


EXCEL_FIELD_MAP: dict[str, tuple[ExcelCellTarget, ...]] = {
    "fecha_acta.day": (ExcelCellTarget("Acta de Entrega Final de Manten", "J7"),),
    "fecha_acta.month": (ExcelCellTarget("Acta de Entrega Final de Manten", "L7"),),
    "fecha_acta.year": (ExcelCellTarget("Acta de Entrega Final de Manten", "N7"),),
    "numero_orden": (
        ExcelCellTarget("Acta de Entrega Final de Manten", "M14"),
        ExcelCellTarget("Acta de Entrega Final de Manten", "AJ22"),
    ),
    "proveedor.nombre": (ExcelCellTarget("Acta de Entrega Final de Manten", "N11"),),
    "proveedor.nit": (ExcelCellTarget("Acta de Entrega Final de Manten", "G12"),),
    "proveedor.direccion": (ExcelCellTarget("Acta de Entrega Final de Manten", "N13"),),
    "proveedor.telefono": (ExcelCellTarget("Acta de Entrega Final de Manten", "AR12"),),
    "fecha_orden": (ExcelCellTarget("Acta de Entrega Final de Manten", "AQ14"),),
    "fecha_vencimiento": (ExcelCellTarget("Acta de Entrega Final de Manten", "Y15"),),
}

CERTIFICATE_SHEET = "Acta de Entrega Final de Manten"
CERTIFICATE_NO_CELL = "N28"
CERTIFICATE_YES_CELL = "S28"
CERTIFICATE_TYPE_CELL = "X28"
ACTUAL_DELIVERY_DATE_CELL = "N16"
DELIVERY_SECTION_DATE_CELLS = ("F21", "N21", "Y21")
