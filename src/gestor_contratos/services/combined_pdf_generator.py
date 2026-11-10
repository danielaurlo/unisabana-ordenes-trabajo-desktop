"""Generate a single PDF containing the work order and completed acta."""

from dataclasses import dataclass

import pymupdf

from gestor_contratos.services.excel_preview import ExcelPreviewRenderer


class CombinedPDFGenerationError(Exception):
    """Raised when the source order and generated acta cannot be combined."""


@dataclass(frozen=True)
class CombinedPDFResult:
    """Generated acta PDF and final combined document."""

    acta_pdf_bytes: bytes
    combined_pdf_bytes: bytes


class CombinedPDFGenerator:
    """Convert the completed Excel acta and append it to the source order."""

    def __init__(self, renderer: ExcelPreviewRenderer | None = None) -> None:
        self.renderer = renderer or ExcelPreviewRenderer()

    def generate(self, order_pdf_bytes: bytes, excel_bytes: bytes) -> CombinedPDFResult:
        """Return the acta PDF and an order-first combined PDF."""
        acta_pdf_bytes = self.renderer.render(excel_bytes)
        combined_pdf_bytes = self._merge(order_pdf_bytes, acta_pdf_bytes)
        return CombinedPDFResult(
            acta_pdf_bytes=acta_pdf_bytes,
            combined_pdf_bytes=combined_pdf_bytes,
        )

    @staticmethod
    def _merge(order_pdf_bytes: bytes, acta_pdf_bytes: bytes) -> bytes:
        if not order_pdf_bytes:
            raise CombinedPDFGenerationError(
                "No se encontró el PDF de la orden para generar el documento final."
            )

        try:
            with (
                pymupdf.open(stream=order_pdf_bytes, filetype="pdf") as order,
                pymupdf.open(stream=acta_pdf_bytes, filetype="pdf") as acta,
                pymupdf.open() as combined,
            ):
                if order.page_count == 0 or acta.page_count == 0:
                    raise CombinedPDFGenerationError(
                        "La orden o el acta no contiene páginas para combinar."
                    )
                combined.insert_pdf(order)
                combined.insert_pdf(acta)
                return combined.tobytes(garbage=4, deflate=True)
        except CombinedPDFGenerationError:
            raise
        except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
            raise CombinedPDFGenerationError(
                "No fue posible unir la orden y el acta en un solo PDF."
            ) from exc
