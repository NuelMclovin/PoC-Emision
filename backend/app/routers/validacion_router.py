"""
Router de validación de macros.

Endpoints:
  POST /api/v1/validacion/macro  — Sube un archivo y devuelve el reporte de validación.
  POST /api/v1/validacion/renovacion-con-base — Sube dos archivos (base y nuevo) y devuelve el reporte de validación y comparación.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from fastapi.responses import Response
from typing import Any, Dict, List

from ..services.exporter import exportar_errores
from ..models.macro_models import ReporteValidacion # Importar ReporteValidacion
from ..services.macro_reader import leer_macro
from ..services.validator import validar_macro, validar_y_comparar_macros # <-- Importar la nueva función de validación y comparación
from ..utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/v1/validacion", tags=["validación"])

EXTENSIONES_PERMITIDAS = {".xlsx", ".xls", ".xlsm", ".csv"}
MAX_SIZE_MB = 20

# Helper para validar extensiones y tamaño de archivos
async def _validar_archivo_general(archivo: UploadFile, field_name: str) -> bytes:
    filename = archivo.filename or field_name
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Formato '{ext}' no soportado para {field_name}. Permitidos: {', '.join(sorted(EXTENSIONES_PERMITIDAS))}",
        )

    content = await archivo.read()
    if len(content) / (1024 * 1024) > MAX_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo {field_name} supera el límite de {MAX_SIZE_MB} MB.",
        )
    return content


@router.post(
    "/macro",
    response_model=ReporteValidacion,
    summary="Valida una macro de emisión",
    description=(
        "Recibe un archivo Excel (.xlsx/.xls/.xlsm) o CSV, el tipo de acción "
        "(nueva | renovacion) y el tipo de producto (GMM | AP). "
        "Aplica las reglas de negocio correspondientes y devuelve un reporte detallado."
    ),
)
async def validar_macro_endpoint(
    archivo: UploadFile = File(..., description="Macro de emisión"),
    tipo_accion: Literal["nueva", "renovacion"] = Form(
        "nueva", description="Tipo de acción: 'nueva' o 'renovacion'"
    ),
    tipo_producto: Literal["GMM", "AP"] = Form(
        "GMM", description="Tipo de producto: 'GMM' o 'AP'"
    ),
) -> ReporteValidacion:

    content = await _validar_archivo_general(archivo, "archivo")
    filename = archivo.filename or "archivo"

    try:
        df, offset = leer_macro(filename, content, tipo_accion=tipo_accion, tipo_producto=tipo_producto)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return validar_macro(filename, df, tipo_accion=tipo_accion, tipo_producto=tipo_producto, fila_offset=offset)


@router.post(
    "/renovacion-con-base", # <-- NUEVO ENDPOINT
    response_model=ReporteValidacion,
    summary="Valida y compara una macro de renovación con un archivo base",
    description=(
        "Recibe dos archivos (el archivo base de la póliza anterior y el nuevo archivo de renovación), "
        "el tipo de acción ('renovacion') y el tipo de producto (GMM | AP). "
        "Valida ambos archivos y luego realiza una comparación entre ellos, devolviendo un reporte detallado "
        "que incluye hallazgos de validación y de comparación (altas, bajas, modificaciones)."
    ),
)
async def renovacion_con_base_endpoint(
    archivo_nuevo: UploadFile = File(..., description="Nuevo archivo de renovación"),
    archivo_base: UploadFile = File(..., description="Archivo base de la póliza anterior"),
    tipo_accion: Literal["renovacion"] = Form(..., description="Tipo de acción: 'renovacion'"), # Forzamos a 'renovacion'
    tipo_producto: Literal["GMM", "AP"] = Form(
        "GMM", description="Tipo de producto: 'GMM' o 'AP'"
    ),
) -> ReporteValidacion:

    # Validar y leer ambos archivos
    content_nuevo = await _validar_archivo_general(archivo_nuevo, "archivo_nuevo")
    filename_nuevo = archivo_nuevo.filename or "archivo_nuevo"

    content_base = await _validar_archivo_general(archivo_base, "archivo_base")
    filename_base = archivo_base.filename or "archivo_base"

    try:
        df_nuevo, offset_nuevo = leer_macro(filename_nuevo, content_nuevo, tipo_accion=tipo_accion, tipo_producto=tipo_producto)
        df_base, offset_base = leer_macro(filename_base, content_base, tipo_accion=tipo_accion, tipo_producto=tipo_producto)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    # Llamar a la nueva función de validación y comparación
    return validar_y_comparar_macros(
        filename_nuevo=filename_nuevo,
        df_nuevo=df_nuevo,
        fila_offset_nuevo=offset_nuevo,
        filename_base=filename_base,
        df_base=df_base,
        fila_offset_base=offset_base,
        tipo_accion=tipo_accion,
        tipo_producto=tipo_producto,
    )


@router.post("/export-errores")
async def exportar_errores_endpoint(payload: Dict[str, Any]) -> Response:
    """
    payload expected:
    {
      "headers": ["col1","col2",...],
      "filas": [ { "col1": val1, "col2": val2, ... }, ... ],
      "format": "csv" | "xlsx",
      "nombre_archivo": "nombre_origen.ext"
    }
    """
    headers = payload.get("headers", [])
    filas = payload.get("filas", [])
    formato = payload.get("format", "csv")
    nombre_archivo = payload.get("nombre_archivo", "errores")

    if not headers or not filas:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Headers or rows missing for export.")

    data, mime, filename = exportar_errores(headers, filas, formato)

    return Response(content=data, media_type=mime, headers={
        "Content-Disposition": f'attachment; filename="{filename if filename else nombre_archivo}_errores.{("csv" if formato=="csv" else "xlsx")}"'
    })
