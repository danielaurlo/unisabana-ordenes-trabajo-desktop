"""Extract normalized work-order data from SIGA PDFs."""

import re
from datetime import date

import pymupdf

from gestor_contratos.config import extraction_patterns as patterns
from gestor_contratos.models.orden_trabajo import OrdenTrabajoData, ProveedorData
from gestor_contratos.services.pdf_extractor import PDFExtractor


class OrdenTrabajoExtractor:
    """Extract fields from the order pages of a SIGA PDF."""

    def __init__(self, pdf_extractor: PDFExtractor | None = None) -> None:
        self.pdf_extractor = pdf_extractor or PDFExtractor()

    def extract(self, pdf_bytes: bytes) -> OrdenTrabajoData:
        """Extract order data while preserving missing and ambiguous fields."""
        self.pdf_extractor.extract(pdf_bytes)

        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            pages = [page.get_text("text") for page in document]
            acta_words = (
                document[-1].get_text("words") if document.page_count >= 1 else []
            )

        order_text = pages[0] if pages else ""
        acta_text = pages[-1] if len(pages) > 1 else ""
        missing: list[str] = []
        ambiguous: list[str] = []

        fecha_orden = self._date_field(
            order_text,
            patterns.ORDER_DATE,
            "fecha_orden",
            missing,
            ambiguous,
        )
        numero_original = self._field(
            order_text,
            patterns.ORDER_NUMBER,
            "numero_orden",
            missing,
            ambiguous,
        )
        numero_orden = self._normalize_order_number(numero_original)
        has_acta = "ACTA DE ENTREGA FINAL" in acta_text.upper()
        if has_acta:
            fecha_acta = self._extract_acta_date(acta_words, missing, ambiguous)
        else:
            fecha_acta = date.today()

        if (
            fecha_acta is not None
            and fecha_orden is not None
            and fecha_acta < fecha_orden
            and "fecha_acta" not in ambiguous
        ):
            ambiguous.append("fecha_acta")

        fecha_vencimiento = self._date_field(
            order_text,
            patterns.END_DATE,
            "fecha_vencimiento",
            missing,
            ambiguous,
        )

        proveedor = ProveedorData(
            nombre=self._field(
                order_text,
                patterns.PROVIDER_NAME,
                "proveedor.nombre",
                missing,
                ambiguous,
            ),
            nit=self._normalize_nit(
                self._field(
                    order_text,
                    patterns.PROVIDER_NIT,
                    "proveedor.nit",
                    missing,
                    ambiguous,
                )
            ),
            direccion=self._field(
                order_text,
                patterns.PROVIDER_ADDRESS,
                "proveedor.direccion",
                missing,
                ambiguous,
            ),
            telefono=self._field(
                order_text, patterns.PHONE, "proveedor.telefono", missing, ambiguous
            ),
        )

        missing = list(dict.fromkeys(missing))
        ambiguous = list(dict.fromkeys(ambiguous))
        missing = [field for field in missing if field not in ambiguous]

        result = OrdenTrabajoData(
            fecha_orden=fecha_orden,
            fecha_acta=fecha_acta,
            numero_orden=numero_orden,
            numero_orden_original=numero_original,
            fecha_vencimiento=fecha_vencimiento,
            proveedor=proveedor,
            campos_faltantes=missing,
            campos_ambiguos=ambiguous,
        )
        return result

    @staticmethod
    def _field(
        text: str,
        pattern: str,
        field_name: str,
        missing: list[str],
        ambiguous: list[str],
    ) -> str | None:
        matches = [
            OrdenTrabajoExtractor._normalize_text(match.group("value"))
            for match in re.finditer(pattern, text)
            if OrdenTrabajoExtractor._normalize_text(match.group("value"))
        ]
        unique_matches = list(dict.fromkeys(matches))
        if not unique_matches:
            missing.append(field_name)
            return None
        if len(unique_matches) > 1:
            ambiguous.append(field_name)
            return None
        return unique_matches[0]

    @classmethod
    def _date_field(
        cls,
        text: str,
        pattern: str,
        field_name: str,
        missing: list[str],
        ambiguous: list[str],
    ) -> date | None:
        value = cls._field(text, pattern, field_name, missing, ambiguous)
        if value is None:
            return None
        try:
            return cls._parse_date(value)
        except ValueError:
            ambiguous.append(field_name)
            return None

    @staticmethod
    def _parse_date(value: str) -> date:
        parts = [int(part) for part in re.findall(r"\d+", value)]
        if len(parts) != 3:
            raise ValueError("Formato de fecha no reconocido")
        first, second, year = parts
        if first > 12:
            day, month = first, second
        elif second > 12:
            month, day = first, second
        else:
            day, month = first, second
        return date(year, month, day)

    @classmethod
    def _extract_acta_date(
        cls,
        words: list[tuple],
        missing: list[str],
        ambiguous: list[str],
    ) -> date | None:
        """Extract the date printed below the DD/MM/AAAA markers on the acta."""
        date_marker = next(
            (
                word
                for word in words
                if word[4].strip().upper() == "DD" and 50 <= word[1] <= 120
            ),
            None,
        )
        if date_marker is None:
            missing.append("fecha_acta")
            return None

        candidate_numbers = sorted(
            (
                word
                for word in words
                if date_marker[1] < word[1] <= date_marker[1] + 30
                and date_marker[0] - 20 <= word[0] <= date_marker[0] + 110
                and re.fullmatch(r"\d{1,4}", word[4].strip())
            ),
            key=lambda word: word[0],
        )
        values = [int(word[4]) for word in candidate_numbers[:3]]
        if len(values) != 3:
            missing.append("fecha_acta")
            return None
        try:
            return date(values[2], values[1], values[0])
        except ValueError:
            ambiguous.append("fecha_acta")
            return None

    @staticmethod
    def _normalize_order_number(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.lstrip("0")
        return normalized or "0"

    @staticmethod
    def _normalize_nit(value: str | None) -> str | None:
        if value is None:
            return None
        return re.sub(r"\D", "", value) or None

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()
