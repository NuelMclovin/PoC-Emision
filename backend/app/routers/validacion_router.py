"""
Router de validación de macros.

Endpoints:
  POST /api/v1/validacion/macro  — Sube un archivo y devuelve el reporte de validación.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from fastapi.responses import Response

from starlette.responses import StreamingResponse
from typing import Any, Dict, List

from ..services.exporter import exportar_errores

from ..models.macro_models import ReporteValidacion
from ..services.macro_reader import leer_macro
from ..services.validator import validar_macro
from ..utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/v1/validacion", tags=["validación"])

EXTENSIONES_PERMITIDAS = {".xlsx", ".xls", ".xlsm", ".csv"}
MAX_SIZE_MB = 20


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

    filename = archivo.filename or "archivo"
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Formato '{ext}' no soportado. Permitidos: {', '.join(sorted(EXTENSIONES_PERMITIDAS))}",
        )

    content = await archivo.read()
    if len(content) / (1024 * 1024) > MAX_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite de {MAX_SIZE_MB} MB.",
        )

    try:
        df, offset = leer_macro(filename, content, tipo_accion=tipo_accion, tipo_producto=tipo_producto)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    # ✅ Pasar offset a validar_macro
    return validar_macro(filename, df, tipo_accion=tipo_accion, tipo_producto=tipo_producto, fila_offset=offset)


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
        return Response(status_code=400, content=b'Headers or rows missing')

    data, mime, filename = exportar_errores(headers, filas, formato)

    return Response(content=data, media_type=mime, headers={
        "Content-Disposition": f'attachment; filename="{filename if filename else nombre_archivo}_errores.{("csv" if formato=="csv" else "xlsx")}"'
    })