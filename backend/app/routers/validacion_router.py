"""
Router de validación de macros.

Endpoints:
  POST /api/v1/validacion/macro  — Sube un archivo y devuelve el reporte de validación.
"""


from __future__ import annotations # ESTA DEBE SER LA PRIMERA LÍNEA EJECUTABLE

import json # <-- Esta y las siguientes pueden ir después
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from starlette.responses import StreamingResponse

from ..models.macro_models import ReporteValidacion
from ..services.macro_reader import leer_macro
from ..services.validator import validar_macro
from ..services.report_exporter import exportar_df_a_archivo
from ..utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/v1/validacion", tags=["validación"])

EXTENSIONES_PERMITIDAS = {".xlsx", ".xls", ".xlsm", ".csv"}
MAX_SIZE_MB = 100


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


@router.post(
    "/descargar-errores",
    summary="Descarga un archivo (CSV/Excel) con las filas del censo que contienen errores",
    response_class=StreamingResponse, # Indica que la respuesta será un stream de archivo
)
async def descargar_errores_endpoint(
    archivo: UploadFile = File(..., description="Archivo original de la macro de emisión"),
    tipo_accion: Literal["nueva", "renovacion"] = Form("nueva", description="Tipo de acción"),
    tipo_producto: Literal["GMM", "AP"] = Form("GMM", description="Tipo de producto"),
    filas_con_error: str = Form(..., description="JSON string con los números de fila (1-based) a incluir"),
    formato: Literal["csv", "excel"] = Form(..., description="Formato de salida: 'csv' o 'excel'"),
) -> StreamingResponse:
    filename = archivo.filename or "archivo"
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    
    # Validación de extensión (similar a validar_macro_endpoint)
    if ext not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Formato '{ext}' no soportado. Permitidos: {', '.join(sorted(EXTENSIONES_PERMITIDAS))}",
        )

    content = await archivo.read()
    
    # Validación de tamaño (similar a validar_macro_endpoint)
    if len(content) / (1024 * 1024) > MAX_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite de {MAX_SIZE_MB} MB.",
        )

    try:
        # Parsear las filas con error del JSON string a una lista de enteros
        filas_a_filtrar_frontend = json.loads(filas_con_error)
        if not isinstance(filas_a_filtrar_frontend, list) or not all(isinstance(f, int) for f in filas_a_filtrar_frontend):
            raise ValueError("El parámetro 'filas_con_error' debe ser una lista de números enteros.")
        
        # Leer el archivo original para obtener el DataFrame y el offset
        df_original, offset = leer_macro(filename, content, tipo_accion=tipo_accion, tipo_producto=tipo_producto)
        
        # Ajustar los números de fila del frontend (1-based) a índices de DataFrame (0-based)
        # y considerar el offset de filas saltadas antes del header
        # Las filas del frontend son 1-based, y el offset es la cantidad de filas antes del data + header
        # df.iloc[0] corresponde a la fila (offset + 1) del excel original
        # Por lo tanto, para obtener el índice de df, es: fila_frontend - (offset + 1)
        indices_df_filtrado = [f_num - (offset + 1) for f_num in filas_a_filtrar_frontend if f_num > offset]
        
        # Filtrar el DataFrame para incluir solo las filas con errores
        # Asegurarse de que los índices sean válidos para el df
        valid_indices = [idx for idx in indices_df_filtrado if 0 <= idx < len(df_original)]
        df_filtrado = df_original.iloc[valid_indices]

        # Exportar el DataFrame filtrado al formato deseado
        file_buffer, media_type, filename_export = exportar_df_a_archivo(df_filtrado, filename, formato)

        # Devolver el archivo como StreamingResponse
        return StreamingResponse(
            file_buffer,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename=\"{filename_export}\""}
        )

    except ValueError as exc:
        logger.error(f"Error al procesar la descarga de errores: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Error inesperado al descargar el reporte de errores: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor al generar el archivo.") from exc
