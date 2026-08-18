"""
Orquestador de validación: aplica las reglas de negocio según
tipo_accion (nueva | renovacion) y tipo_producto (GMM | AP).
"""
from __future__ import annotations

import pandas as pd

from ..core.reglas_negocio import obtener_reglas
from ..models.macro_models import (
    ReporteValidacion,
    ResumenValidacion,
    ResultadoValidacion,
    TipoError,
)
from ..utils.logger import get_logger

logger = get_logger()


def validar_macro(
    filename: str,
    df: pd.DataFrame,
    tipo_accion: str = "nueva",
    tipo_producto: str = "GMM",
    fila_offset: int = 1,  # ← Nuevo parámetro
) -> ReporteValidacion:
    """
    Ejecuta las reglas de negocio correspondientes al tipo de macro
    y devuelve un ReporteValidacion completo.
    
    Args:
        filename: Nombre del archivo
        df: DataFrame con los datos
        tipo_accion: "nueva" o "renovacion"
        tipo_producto: "GMM" o "AP"
        fila_offset: Número de filas saltadas para calcular fila real del Excel
    """
    resultados: list[ResultadoValidacion] = []
    reglas = obtener_reglas(tipo_accion, tipo_producto, fila_offset=fila_offset)  # ✅ Pasar fila_offset

    for regla in reglas:
        try:
            parciales = regla(df)
            resultados.extend(parciales)
        except Exception as exc:
            logger.warning("Regla '%s' lanzó excepción: %s", getattr(regla, '__name__', str(regla)), exc)

    # Calcular resumen
    col_map = {c.upper(): c for c in df.columns}
    col_parentesco = col_map.get("PARENTESCO")

    total_titulares = 0
    total_dependientes = 0
    if col_parentesco:
        total_titulares = int((df[col_parentesco].str.strip().str.lower() == "titular").sum())
        total_dependientes = len(df) - total_titulares

    errores = [r for r in resultados if r.tipo == TipoError.ERROR]
    advertencias = [r for r in resultados if r.tipo == TipoError.ADVERTENCIA]

    resumen = ResumenValidacion(
        total_registros=len(df),
        total_titulares=total_titulares,
        total_dependientes=total_dependientes,
        total_errores=len(errores),
        total_advertencias=len(advertencias),
        es_valida=len(errores) == 0,
    )

    logger.info(
        "Validación '%s' [%s/%s]: %d registros, %d errores, %d advertencias. Válida: %s",
        filename, tipo_accion, tipo_producto,
        len(df), len(errores), len(advertencias), resumen.es_valida,
    )

    # Construir encabezados y filas con errores (si df está disponible)
    try:
        encabezados = list(df.columns.tolist())
    except Exception:
        encabezados = None

        # Filas con errores: recolecta filas donde exista al menos un ResultadoValidacion tipo ERROR
    filas_con_errores: list[dict] = []
    filas_con_indices = set()
    for r in resultados:
        if r.tipo == TipoError.ERROR and r.fila is not None:
            filas_con_indices.add(int(r.fila))

    # Mapear filas de df a diccionarios (si el índice existe)
    if filas_con_indices:
        offset = int(fila_offset) if fila_offset is not None else 0
        # El mapeo intenta convertir el número de fila del Excel a índice de DataFrame
        base = offset + 1  # asume header en 1, datos empiezan en 2 cuando offset=1
        for fila_excel in sorted(filas_con_indices):
            data_index = int(fila_excel) - base
            if 0 <= data_index < len(df):
                row = df.iloc[data_index].to_dict()
                filas_con_errores.append({str(k): v for k, v in row.items()})
    else:
        filas_con_errores = []

    reporte = ReporteValidacion(
        nombre_archivo=filename,
        resumen=resumen,
        resultados=resultados,
        encabezados=encabezados,
        filas_con_errores=filas_con_errores,
        offset_filas=fila_offset,
    )

    return reporte
