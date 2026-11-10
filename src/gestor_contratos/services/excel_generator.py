"""Generate a completed institutional Excel workbook in memory."""

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import load_workbook
from openpyxl.utils.datetime import to_excel

from gestor_contratos.config.excel_mapping import (
    ACTUAL_DELIVERY_DATE_CELL,
    CERTIFICATE_NO_CELL,
    CERTIFICATE_SHEET,
    CERTIFICATE_TYPE_CELL,
    CERTIFICATE_YES_CELL,
    DEFAULT_TEMPLATE_PATH,
    DELIVERY_SECTION_DATE_CELLS,
    EXCEL_FIELD_MAP,
    ExcelCellTarget,
)
from gestor_contratos.models.orden_trabajo import OrdenTrabajoData


class ExcelGenerationError(Exception):
    """Raised when the workbook cannot be generated safely."""


class ExcelGenerator:
    """Fill the institutional workbook without modifying its source file."""

    def __init__(
        self,
        template_path: Path | str = DEFAULT_TEMPLATE_PATH,
        field_map: dict[str, tuple[ExcelCellTarget, ...]] = EXCEL_FIELD_MAP,
    ) -> None:
        self.template_path = Path(template_path)
        self.field_map = field_map

    def generate(self, data: OrdenTrabajoData) -> bytes:
        """Return a completed workbook as bytes."""
        if data.campos_ambiguos:
            raise ExcelGenerationError(
                "No se puede generar el Excel: hay campos ambiguos por revisar."
            )
        if not self.template_path.is_file():
            raise ExcelGenerationError(
                f"No se encontró la plantilla Excel: {self.template_path}"
            )

        try:
            load_workbook(self.template_path, data_only=False)
            updates: dict[ExcelCellTarget, Any] = {}
            for field_path, targets in self.field_map.items():
                value = self._resolve_field(data, field_path)
                for target in targets:
                    updates[target] = value
            updates[ExcelCellTarget(CERTIFICATE_SHEET, CERTIFICATE_NO_CELL)] = None
            updates[ExcelCellTarget(CERTIFICATE_SHEET, CERTIFICATE_YES_CELL)] = None
            updates[ExcelCellTarget(CERTIFICATE_SHEET, CERTIFICATE_TYPE_CELL)] = None
            updates[
                ExcelCellTarget(CERTIFICATE_SHEET, ACTUAL_DELIVERY_DATE_CELL)
            ] = None
            for cell in DELIVERY_SECTION_DATE_CELLS:
                updates[ExcelCellTarget(CERTIFICATE_SHEET, cell)] = None
            return self._apply_updates_preserving_template(updates)
        except ExcelGenerationError:
            raise
        except (KeyError, OSError, ValueError) as exc:
            raise ExcelGenerationError(
                "No fue posible completar la plantilla Excel."
            ) from exc

    def _apply_updates_preserving_template(
        self, updates: dict[ExcelCellTarget, Any]
    ) -> bytes:
        """Edit mapped cells without rebuilding or altering the template."""
        main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        relationships = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        namespaces = {"main": main}

        with ZipFile(self.template_path) as source:
            files = {name: source.read(name) for name in source.namelist()}

        workbook = ElementTree.fromstring(files["xl/workbook.xml"])
        rels = ElementTree.fromstring(files["xl/_rels/workbook.xml.rels"])
        targets = {
            relation.attrib["Id"]: relation.attrib["Target"]
            for relation in rels
        }
        sheet_paths: dict[str, str] = {}
        for sheet in workbook.findall("main:sheets/main:sheet", namespaces):
            relation_id = sheet.attrib[f"{{{relationships}}}id"]
            target = targets[relation_id]
            sheet_paths[sheet.attrib["name"]] = (
                target.lstrip("/")
                if target.startswith("/")
                else f"xl/{target}"
            )

        grouped: dict[str, list[tuple[str, Any]]] = {}
        for target, value in updates.items():
            if target.sheet not in sheet_paths:
                raise ExcelGenerationError(
                    f"No existe la hoja configurada: {target.sheet}"
                )
            grouped.setdefault(sheet_paths[target.sheet], []).append(
                (target.cell, value)
            )

        for sheet_path, values in grouped.items():
            sheet = ElementTree.fromstring(files[sheet_path])
            cells = {
                cell.attrib["r"]: cell
                for cell in sheet.findall(".//main:c", namespaces)
            }
            for coordinate, value in values:
                if coordinate not in cells:
                    raise ExcelGenerationError(
                        f"No existe la celda configurada: {coordinate}"
                    )
                self._set_cell_value(cells[coordinate], value, main)
            files[sheet_path] = ElementTree.tostring(
                sheet, encoding="utf-8", xml_declaration=True
            )

        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as destination:
            for name, content in files.items():
                destination.writestr(name, content)
        return output.getvalue()

    @staticmethod
    def _set_cell_value(cell: Any, value: Any, namespace: str) -> None:
        value_tags = {f"{{{namespace}}}v", f"{{{namespace}}}is"}
        for child in list(cell):
            if child.tag in value_tags:
                cell.remove(child)
        cell.attrib.pop("t", None)
        if value is None:
            return
        if isinstance(value, str):
            cell.set("t", "inlineStr")
            inline = ElementTree.SubElement(cell, f"{{{namespace}}}is")
            text = ElementTree.SubElement(inline, f"{{{namespace}}}t")
            text.text = value
            if value != value.strip():
                text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            return
        numeric = to_excel(value) if isinstance(value, (date, datetime)) else value
        value_node = ElementTree.SubElement(cell, f"{{{namespace}}}v")
        value_node.text = str(numeric)

    @staticmethod
    def _resolve_field(data: OrdenTrabajoData, field_path: str) -> Any:
        value: Any = data
        for part in field_path.split("."):
            if value is None:
                return None
            value = getattr(value, part)
        return value

    def _clear_mapped_cells(self, workbook: Any) -> None:
        """Clear template values before writing current acta data."""
        for targets in self.field_map.values():
            for target in targets:
                if target.sheet not in workbook.sheetnames:
                    raise ExcelGenerationError(
                        f"No existe la hoja configurada: {target.sheet}"
                    )
                workbook[target.sheet][target.cell] = None

    @staticmethod
    def _write_value(workbook: Any, target: ExcelCellTarget, value: Any) -> None:
        if value is None:
            return
        if target.sheet not in workbook.sheetnames:
            raise ExcelGenerationError(f"No existe la hoja configurada: {target.sheet}")
        cell = workbook[target.sheet][target.cell]
        cell.value = value
        if isinstance(value, str):
            cell.data_type = "s"

    @staticmethod
    def _clear_certificate_requirement(workbook: Any) -> None:
        """Leave all certificate fields blank on the generated acta."""
        if CERTIFICATE_SHEET not in workbook.sheetnames:
            raise ExcelGenerationError(
                f"No existe la hoja configurada: {CERTIFICATE_SHEET}"
            )

        sheet = workbook[CERTIFICATE_SHEET]
        sheet[CERTIFICATE_NO_CELL] = None
        sheet[CERTIFICATE_YES_CELL] = None
        sheet[CERTIFICATE_TYPE_CELL] = None
