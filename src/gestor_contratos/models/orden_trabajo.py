"""Pydantic models for normalized work-order data."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProveedorData(BaseModel):
    """Supplier or contractor information."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str | None = None
    nit: str | None = None
    direccion: str | None = None
    persona_contacto: str | None = None
    ciudad: str | None = None
    telefono: str | None = None
    celular: str | None = None
    correo: str | None = None


class DetalleOrden(BaseModel):
    """One line from the work-order detail table."""

    numero: int | None = None
    descripcion: str | None = None
    unidad: str | None = None
    cantidad: Decimal | None = None
    valor_unitario: Decimal | None = None
    valor_total: Decimal | None = None


class OrdenTrabajoData(BaseModel):
    """Normalized data extracted from a SIGA work order."""

    model_config = ConfigDict(str_strip_whitespace=True)

    fecha_orden: date | None = None
    fecha_acta: date | None = None
    fecha_real_entrega: date | None = None
    numero_orden: str | None = None
    numero_orden_original: str | None = None
    tipo_orden: str | None = None
    objeto: str | None = None
    sede: str | None = None
    fecha_inicio: date | None = None
    fecha_vencimiento: date | None = None
    requiere_certificado: bool = False
    tipo_certificado: str | None = None
    proveedor: ProveedorData = Field(default_factory=ProveedorData)
    detalles: list[DetalleOrden] = Field(default_factory=list)
    valor_total_letras: str | None = None
    subtotal: Decimal | None = None
    descuento: Decimal | None = None
    iva: Decimal | None = None
    total: Decimal | None = None
    campos_faltantes: list[str] = Field(default_factory=list)
    campos_ambiguos: list[str] = Field(default_factory=list)
