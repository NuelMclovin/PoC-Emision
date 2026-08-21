"""
Modelos de dominio para el CRUD de casos/folios.

Un "caso" representa el expediente de emision que un broker envia desde el
frontend de conducto hacia el frontend de suscriptor interno. Se persiste en
almacenamiento local (CSV + volumen de archivos por folio), ver
app/services/casos_store.py y app/services/documentos_store.py.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel

from .macro_models import ReporteValidacion


class EstadoCaso(str, Enum):
    PENDIENTE = "Pendiente"
    EN_REVISION = "En revisión"
    OBSERVADO = "Observado"
    APROBADO = "Aprobado"
    RECHAZADO = "Rechazado"


class RolUsuario(str, Enum):
    BROKER = "broker"
    SUSCRIPTOR = "suscriptor"


# ─── Documentos por folio ──────────────────────────────────────────────────

class DocumentoInfo(BaseModel):
    nombre: str
    tipo: Literal["macro", "reporte", "anexo"]
    tamano_bytes: int
    subido_en: datetime
    subido_por: Optional[str] = None


# ─── Caso / folio ───────────────────────────────────────────────────────────

class CasoResumen(BaseModel):
    folio: str
    empresa: str
    tipo_accion: Literal["nueva", "renovacion"]
    tipo_producto: Literal["GMM", "AP"]
    estado: EstadoCaso
    creado_por: str
    asignado_a: Optional[str] = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    total_registros: int = 0
    total_titulares: int = 0
    total_dependientes: int = 0
    total_errores: int = 0
    total_advertencias: int = 0
    es_valida: bool = False
    comentario_suscriptor: str = ""
    nombre_archivo_macro: str = ""


class CasoDetalle(CasoResumen):
    reporte: Optional[ReporteValidacion] = None
    documentos: list[DocumentoInfo] = []


class CasoActualizar(BaseModel):
    """Body para PATCH /api/v1/casos/{folio} — acciones del suscriptor."""

    estado: Optional[EstadoCaso] = None
    asignado_a: Optional[str] = None
    comentario_suscriptor: Optional[str] = None