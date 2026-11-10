"""PDF validation and text extraction services."""

from dataclasses import dataclass

import pymupdf

DEFAULT_MAX_SIZE_BYTES = 10 * 1024 * 1024


class PDFExtractionError(Exception):
    """Base error for expected PDF extraction failures."""


class PDFEmptyError(PDFExtractionError):
    """Raised when no PDF bytes were provided."""


class PDFTooLargeError(PDFExtractionError):
    """Raised when a PDF exceeds the configured maximum size."""


class InvalidPDFError(PDFExtractionError):
    """Raised when the provided bytes are not a valid PDF."""


class ProtectedPDFError(PDFExtractionError):
    """Raised when the PDF requires a password."""


class PDFWithoutTextError(PDFExtractionError):
    """Raised when the PDF has no text that can be extracted."""


@dataclass(frozen=True)
class PDFExtractionResult:
    """Text and metadata extracted from a PDF document."""

    text: str
    page_count: int


class PDFExtractor:
    """Validate a PDF held in memory and extract its text."""

    def __init__(self, max_size_bytes: int = DEFAULT_MAX_SIZE_BYTES) -> None:
        if max_size_bytes <= 0:
            raise ValueError("El tamaño máximo debe ser mayor que cero.")
        self.max_size_bytes = max_size_bytes

    def extract(self, pdf_bytes: bytes) -> PDFExtractionResult:
        """Extract text from every page without writing the document to disk."""
        self._validate_bytes(pdf_bytes)

        try:
            with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
                if document.is_encrypted:
                    raise ProtectedPDFError(
                        "El PDF está protegido con contraseña y no puede procesarse."
                    )

                page_texts = [page.get_text("text") for page in document]
                page_count = document.page_count
        except ProtectedPDFError:
            raise
        except (pymupdf.FileDataError, ValueError, RuntimeError) as exc:
            raise InvalidPDFError(
                "El PDF está dañado o no tiene un formato válido."
            ) from exc

        text = "\n\n".join(
            f"--- Página {page_number} ---\n{page_text.strip()}"
            for page_number, page_text in enumerate(page_texts, start=1)
            if page_text.strip()
        ).strip()

        if not text:
            raise PDFWithoutTextError(
                "El PDF no contiene texto extraíble. Puede ser un documento escaneado."
            )

        return PDFExtractionResult(text=text, page_count=page_count)

    def _validate_bytes(self, pdf_bytes: bytes) -> None:
        if not pdf_bytes:
            raise PDFEmptyError("No se recibió ningún documento PDF.")
        if len(pdf_bytes) > self.max_size_bytes:
            max_size_mb = self.max_size_bytes / (1024 * 1024)
            raise PDFTooLargeError(
                f"El PDF supera el tamaño máximo permitido de {max_size_mb:g} MB."
            )
        if not pdf_bytes.startswith(b"%PDF-"):
            raise InvalidPDFError("El archivo seleccionado no es un PDF válido.")
