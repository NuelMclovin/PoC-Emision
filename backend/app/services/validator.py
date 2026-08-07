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

    return ReporteValidacion(
        nombre_archivo=filename,
        resumen=resumen,
        resultados=resultados,
    )
