from __future__ import annotations

from enum import Enum
from typing import Literal, Optional, List, Dict

from pydantic import BaseModel


# ─── Enumeraciones de dominio ──────────────────────────────────────────────────

class Parentesco(str, Enum):
    TITULAR = "Titular"
    CONYUGE = "Cónyuge"
    HIJO = "Hijo"
    PADRE = "Padre"
    MADRE = "Madre"


class Genero(str, Enum):
    MASCULINO = "M"
    FEMENINO = "F"
    # Alias aceptados en la macro
    MASCULINO_LARGO = "Masculino"
    FEMENINO_LARGO = "Femenino"
    H = "H"  # algunos layouts usan H de Hombre


class TipoError(str, Enum):
    ERROR = "error"
    ADVERTENCIA = "advertencia"
    INFO = "info"


# ─── Resultado de una validación ──────────────────────────────────────────────

class ResultadoValidacion(BaseModel):
    tipo: TipoError
    categoria: str
    mensaje: str
    fila: Optional[int] = None          # número de fila en el Excel (1-based header)
    columna: Optional[str] = None       # nombre de la columna afectada
    valor: Optional[str] = None         # valor que causó el problema


# ─── Resumen del reporte de validación ────────────────────────────────────────

class ResumenValidacion(BaseModel):
    total_registros: int
    total_titulares: int
    total_dependientes: int
    total_errores: int
    total_advertencias: int
    es_valida: bool                     # True solo si total_errores == 0


# ─── Respuesta completa de una validación ─────────────────────────────────────

class ReporteValidacion(BaseModel):
    nombre_archivo: str
    resumen: ResumenValidacion
    resultados: list[ResultadoValidacion]

    # Nuevos campos opcional para exportar errores con encabezados originales
    encabezados: Optional[List[str]] = None
    filas_con_errores: Optional[List[Dict[str, object]]] = None
    offset_filas: Optional[int] = None



# ─── Request/Response de auth mock ────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    username: str
