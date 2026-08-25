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

# Función existente para validar un solo archivo
def validar_macro(
    filename: str,
    df: pd.DataFrame,
    tipo_accion: str = "nueva",
    tipo_producto: str = "GMM",
    fila_offset: int = 1,
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
    reglas = obtener_reglas(tipo_accion, tipo_producto, fila_offset=fila_offset)

    for regla in reglas:
        try:
            parciales = regla(df)
            resultados.extend(parciales)
        except Exception as exc:
            logger.warning("Regla '%s' lanzó excepción: %s", getattr(regla, '__name__', str(regla)), exc)

    # Calcular resumen
    resumen = _calcular_resumen(df, resultados)

    logger.info(
        "Validación '%s' [%s/%s]: %d registros, %d errores, %d advertencias. Válida: %s",
        filename, tipo_accion, tipo_producto,
        len(df), resumen.total_errores, resumen.total_advertencias, resumen.es_valida,
    )

    encabezados, filas_con_errores = _obtener_datos_para_exportar(df, resultados, fila_offset)

    reporte = ReporteValidacion(
        nombre_archivo=filename,
        resumen=resumen,
        resultados=resultados,
        encabezados=encabezados,
        filas_con_errores=filas_con_errores,
        offset_filas=fila_offset,
    )

    return reporte

# --- NUEVA LÓGICA PARA VALIDACIÓN Y COMPARACIÓN DE RENOVACIÓN ---

def validar_y_comparar_macros(
    filename_nuevo: str,
    df_nuevo: pd.DataFrame,
    fila_offset_nuevo: int,
    filename_base: str,
    df_base: pd.DataFrame,
    fila_offset_base: int,
    tipo_accion: str = "renovacion", # Siempre 'renovacion' para esta función
    tipo_producto: str = "GMM",
) -> ReporteValidacion:
    """
    Orquesta la validación del archivo base, del archivo nuevo y la comparación entre ambos.
    Devuelve un ReporteValidacion consolidado para el archivo nuevo.
    """
    logger.info("Iniciando validación y comparación para renovación: Archivo Nuevo '%s', Archivo Base '%s'", filename_nuevo, filename_base)

    resultados_consolidados: list[ResultadoValidacion] = []
    
    # 1. Validar archivo base
    reporte_base = validar_macro(
        filename_base, df_base, tipo_accion, tipo_producto, fila_offset_base
    )

    if not reporte_base.resumen.es_valida:
        # Si el archivo base tiene errores, no se puede usar para la comparación
        logger.warning("Archivo base '%s' contiene errores. No se puede proceder con la comparación.", filename_base)
        
        # Generar un reporte de error para el archivo nuevo, indicando el problema con la base
        error_base_invalida = ResultadoValidacion(
            tipo=TipoError.ERROR,
            categoria="BASE_INVALIDA",
            mensaje=f"El archivo base '{filename_base}' contiene errores ({reporte_base.resumen.total_errores}) y no puede ser utilizado para la comparación de renovación. Por favor, corrige el archivo base primero.",
        )
        resultados_consolidados.append(error_base_invalida)
        resultados_consolidados.extend(reporte_base.resultados) # Incluir los errores del archivo base en el reporte final

        # Crear un resumen de error para el archivo nuevo
        resumen_final = ResumenValidacion(
            total_registros=len(df_nuevo),
            total_titulares=0, # No podemos calcular esto si la base es invalida
            total_dependientes=0,
            total_errores=1 + reporte_base.resumen.total_errores, # 1 error por la base invalida + los errores de la base
            total_advertencias=reporte_base.resumen.total_advertencias,
            es_valida=False,
        )

        encabezados_final, filas_con_errores_final = _obtener_datos_para_exportar(df_nuevo, resultados_consolidados, fila_offset_nuevo)

        return ReporteValidacion(
            nombre_archivo=filename_nuevo,
            resumen=resumen_final,
            resultados=resultados_consolidados,
            encabezados=encabezados_final,
            filas_con_errores=filas_con_errores_final,
            offset_filas=fila_offset_nuevo,
        )

    # 2. Validar archivo nuevo (reglas de negocio estándar)
    reporte_nuevo = validar_macro(
        filename_nuevo, df_nuevo, tipo_accion, tipo_producto, fila_offset_nuevo
    )
    resultados_consolidados.extend(reporte_nuevo.resultados)

    # 3. Realizar la comparación entre el archivo base y el nuevo
    # Asunción: La columna 'CERTIFICADO' es el identificador único para la comparación.
    # Si no existe, se podría usar una combinación de 'NOMBRE' + 'FECHA_NACIMIENTO' o 'ID_EMPLEADO'.
    # Es crucial que esta columna sea consistente y única.
    identificador_clave = "CERTIFICADO" # <-- Ajustar según el layout real

    # NOTA: La validación de 'identificador_clave' individual aquí ya no es tan crítica
    # porque la lógica de `_realizar_comparacion` ahora usa una clave compuesta
    # y valida la existencia de esas columnas. Sin embargo, se mantiene por si
    # hubiera algún escenario donde 'CERTIFICADO' se usara solo.
    if identificador_clave not in df_base.columns or identificador_clave not in df_nuevo.columns:
        logger.error("Columna identificadora clave '%s' no encontrada en uno o ambos DataFrames para comparación.", identificador_clave)
        resultados_consolidados.append(
            ResultadoValidacion(
                tipo=TipoError.ERROR,
                categoria="COMPARACION_KEY_MISSING",
                mensaje=f"No se pudo realizar la comparación: La columna identificadora '{identificador_clave}' no fue encontrada en el archivo base o en el nuevo. Asegúrate de que el layout la incluya.",
            )
        )
    else:
        resultados_comparacion = _realizar_comparacion(
            df_base=df_base,
            df_nuevo=df_nuevo,
            identificador_clave=identificador_clave,
            fila_offset_base=fila_offset_base,
            fila_offset_nuevo=fila_offset_nuevo
        )
        resultados_consolidados.extend(resultados_comparacion)

    # 4. Consolidar el reporte final
    final_df = df_nuevo # El reporte final se basa en el archivo nuevo
    resumen_final = _calcular_resumen(final_df, resultados_consolidados)
    
    encabezados_final, filas_con_errores_final = _obtener_datos_para_exportar(final_df, resultados_consolidados, fila_offset_nuevo)

    logger.info(
        "Comparación de Renovación '%s' vs '%s': %d registros, %d errores, %d advertencias (incl. comparación). Válida: %s",
        filename_nuevo, filename_base,
        len(final_df), resumen_final.total_errores, resumen_final.total_advertencias, resumen_final.es_valida,
    )

    return ReporteValidacion(
        nombre_archivo=filename_nuevo,
        resumen=resumen_final,
        resultados=resultados_consolidados,
        encabezados=encabezados_final,
        filas_con_errores=filas_con_errores_final,
        offset_filas=fila_offset_nuevo,
    )

# --- Funciones auxiliares movidas/creadas ---

def _calcular_resumen(df: pd.DataFrame, resultados: list[ResultadoValidacion]) -> ResumenValidacion:
    """Calcula el resumen de validación a partir del DataFrame y los resultados."""
    col_map = {c.upper(): c for c in df.columns}
    col_parentesco = col_map.get("PARENTESCO")

    total_titulares = 0
    total_dependientes = 0
    if col_parentesco:
        total_titulares = int((df[col_parentesco].str.strip().str.lower() == "titular").sum())
        total_dependientes = len(df) - total_titulares

    errores = [r for r in resultados if r.tipo == TipoError.ERROR]
    advertencias = [r for r in resultados if r.tipo == TipoError.ADVERTENCIA]

    return ResumenValidacion(
        total_registros=len(df),
        total_titulares=total_titulares,
        total_dependientes=total_dependientes,
        total_errores=len(errores),
        total_advertencias=len(advertencias),
        es_valida=len(errores) == 0,
    )

def _obtener_datos_para_exportar(df: pd.DataFrame, resultados: list[ResultadoValidacion], fila_offset: int) -> tuple[list[str] | None, list[dict]]:
    """Extrae encabezados y filas con errores para la exportación."""
    try:
        encabezados = list(df.columns.tolist())
    except Exception:
        encabezados = None

    filas_con_errores: list[dict] = []
    filas_con_indices = set()
    for r in resultados:
        if r.tipo == TipoError.ERROR and r.fila is not None:
            filas_con_indices.add(int(r.fila))

    if filas_con_indices:
        offset = int(fila_offset) if fila_offset is not None else 0
        base = offset + 1
        for fila_excel in sorted(filas_con_indices):
            data_index = int(fila_excel) - base
            if 0 <= data_index < len(df):
                row = df.iloc[data_index].to_dict()
                filas_con_errores.append({str(k): v for k, v in row.items()})
    else:
        filas_con_errores = []
    
    return encabezados, filas_con_errores


def _compare_values_robustly(val1, val2, is_numeric_col: bool = False) -> bool:
    """
    Compara dos valores de manera robusta, manejando NaN, cadenas y opcionalmente
    comparación numérica para columnas específicas.

    Args:
        val1: Primer valor a comparar.
        val2: Segundo valor a comparar.
        is_numeric_col: Si es True, intenta comparar numéricamente si ambos son convertibles a float.

    Returns:
        True si los valores se consideran iguales, False en caso contrario.
    """
    # Normalizar a string para una comparación básica y manejo de NaN/None/empty
    str_val1 = str(val1).strip().lower() if pd.notna(val1) else ""
    str_val2 = str(val2).strip().lower() if pd.notna(val2) else ""

    # Si las representaciones de cadena normalizadas son idénticas, son iguales
    if str_val1 == str_val2:
        return True

    # Si es una columna numérica, intentar comparación numérica
    if is_numeric_col:
        try:
            # Intentar convertir a float. Si falla, no son números comparables de esta forma.
            num1 = float(val1) if pd.notna(val1) else None
            num2 = float(val2) if pd.notna(val2) else None
            
            # Si ambos son None (o no numéricos y manejados por pd.notna), ya se habrían igualado arriba.
            # Si ambos son números convertibles, compararlos.
            if num1 is not None and num2 is not None:
                return num1 == num2
        except (ValueError, TypeError):
            # Si la conversión a float falla para alguno, no son números puros.
            # En este caso, ya habríamos caído en el `str_val1 == str_val2` si fueran iguales como string.
            # Si llegamos aquí y no son iguales por string, entonces son diferentes.
            pass
    
    # Si no son iguales por string normalizado ni por comparación numérica (si aplica), son diferentes.
    return False


def _realizar_comparacion(
    df_base: pd.DataFrame,
    df_nuevo: pd.DataFrame,
    identificador_clave: str, # Este ya no será la única clave, pero lo mantenemos como parte de la compuesta
    fila_offset_base: int,
    fila_offset_nuevo: int
) -> list[ResultadoValidacion]:
    """
    Realiza la comparación entre el DataFrame base y el nuevo, identificando altas, bajas y modificaciones.
    Ahora utiliza una clave compuesta para identificar a las personas de forma única.
    """
    resultados_comparacion: list[ResultadoValidacion] = []

    # --- Definir la clave compuesta para identificar a cada persona ---
    # Asume que estas columnas existen y son relevantes para identificar a una persona.
    # Es crucial que estas columnas sean consistentes y no se modifiquen entre renovaciones
    # si se espera que la persona sea la misma.
    claves_compuestas = [
        "CERTIFICADO",
        "NOMBRE",
        "APELLIDO_PATERNO",
        "APELLIDO_MATERNO",
        # "FECHA_NACIMIENTO",  # Eliminado de la clave de identificación para que cambios sean MODIFICACION
        "PARENTESCO" 
    ]

    # Asegurarse de que todas las columnas de la clave compuesta existan en ambos DataFrames
    missing_cols_base = [col for col in claves_compuestas if col not in df_base.columns]
    missing_cols_nuevo = [col for col in claves_compuestas if col not in df_nuevo.columns]

    if missing_cols_base or missing_cols_nuevo:
        missing_str = ", ".join(set(missing_cols_base + missing_cols_nuevo))
        
        resultados_comparacion.append(
            ResultadoValidacion(
                tipo=TipoError.ERROR,
                categoria="COMPARACION_KEY_MISSING",
                mensaje=f"No se pudo realizar la comparación: Faltan columnas clave ({missing_str}) en el archivo base o en el nuevo. Asegúrate de que el layout las incluya y estén normalizadas correctamente.",
            )
        )
        return resultados_comparacion # Salir si faltan claves

    # Crear la clave compuesta normalizando los valores para una comparación robusta
    def generar_clave_persona(row):
        return "_".join([
            str(row[col]).strip().lower() if pd.notna(row[col]) else ""
            for col in claves_compuestas
        ])

    df_base['__clave_persona__'] = df_base.apply(generar_clave_persona, axis=1)
    df_nuevo['__clave_persona__'] = df_nuevo.apply(generar_clave_persona, axis=1)

    # Merge para encontrar altas, bajas y cambios usando la clave compuesta
    merged_df = pd.merge(
        df_base,
        df_nuevo,
        on='__clave_persona__', # ¡Ahora mergeamos por la clave compuesta!
        how='outer',
        suffixes=('_base', '_nuevo'),
        indicator=True
    )

    # Columnas a comparar para modificaciones (excluyendo las claves compuestas y la clave interna)
    # Solo comparamos las columnas que no forman parte de la clave compuesta y que no son la clave interna
    cols_a_comparar = [col for col in df_base.columns if col not in claves_compuestas and col != '__clave_persona__']

    # Identificar Altas (en _nuevo pero no en _base)
    altas_df = merged_df[merged_df['_merge'] == 'right_only']
    for index, row in altas_df.iterrows():
        # Obtener la fila real en el archivo nuevo
        original_row_index = df_nuevo[df_nuevo['__clave_persona__'] == row['__clave_persona__']].index[0]
        real_fila = original_row_index + fila_offset_nuevo + 1
        
        # Intentar obtener el nombre completo para el mensaje
        nombre_completo = f"{row.get('NOMBRE_nuevo', '')} {row.get('APELLIDO_PATERNO_nuevo', '')} {row.get('APELLIDO_MATERNO_nuevo', '')}".strip()
        if not nombre_completo: # Si no hay nombre, usar la clave de certificado
            nombre_completo = f"Certificado {row.get('CERTIFICADO_nuevo', 'N/A')}"

        resultados_comparacion.append(
            ResultadoValidacion(
                tipo=TipoError.ADVERTENCIA,
                categoria="COMPARACION_ALTA",
                mensaje=f"Nuevo registro detectado en la renovación: '{nombre_completo}'.",
                fila=real_fila,
                columna=None, # La modificación afecta a todo el registro, no a una columna específica
                valor=nombre_completo
            )
        )
    if not altas_df.empty:
        logger.info("Detectadas %d altas en la comparación.", len(altas_df))


    # Identificar Bajas (en _base pero no en _nuevo)
    bajas_df = merged_df[merged_df['_merge'] == 'left_only']
    for index, row in bajas_df.iterrows():
        # Obtener la fila real en el archivo base (para referencia)
        original_row_index = df_base[df_base['__clave_persona__'] == row['__clave_persona__']].index[0]
        real_fila = original_row_index + fila_offset_base + 1

        # Intentar obtener el nombre completo para el mensaje
        nombre_completo = f"{row.get('NOMBRE_base', '')} {row.get('APELLIDO_PATERNO_base', '')} {row.get('APELLIDO_MATERNO_base', '')}".strip()
        if not nombre_completo:
            nombre_completo = f"Certificado {row.get('CERTIFICADO_base', 'N/A')}"

        resultados_comparacion.append(
            ResultadoValidacion(
                tipo=TipoError.ADVERTENCIA,
                categoria="COMPARACION_BAJA",
                mensaje=f"Registro no encontrado en la renovación (posible baja): '{nombre_completo}'. Estaba en la fila {real_fila} del archivo base.",
                fila=None, # No hay fila en el archivo nuevo
                columna=None,
                valor=nombre_completo
            )
        )
    if not bajas_df.empty:
        logger.info("Detectadas %d bajas en la comparación.", len(bajas_df))


    # Identificar Modificaciones (en ambos y con cambios en otras columnas)
    modificaciones_df = merged_df[merged_df['_merge'] == 'both']

    # lISTA DE COLUMNAS QUE SE COMPARAN COMO NUMÉRICAS (para comparación robusta)
    NUMERIC_COMPARISON_COLS = ["SUBGRUPO"] 
    
    for index, row in modificaciones_df.iterrows():
        has_changes = False
        cambios_detectados = []
        
        # Obtener la fila real en el archivo nuevo
        original_row_index = df_nuevo[df_nuevo['__clave_persona__'] == row['__clave_persona__']].index[0]
        real_fila_nuevo = original_row_index + fila_offset_nuevo + 1

        # Intentar obtener el nombre completo para el mensaje
        nombre_completo = f"{row.get('NOMBRE_nuevo', '')} {row.get('APELLIDO_PATERNO_nuevo', '')} {row.get('APELLIDO_MATERNO_nuevo', '')}".strip()
        if not nombre_completo:
            nombre_completo = f"Certificado {row.get('CERTIFICADO_nuevo', 'N/A')}"

        for col in cols_a_comparar:
            col_base = f"{col}_base"
            col_nuevo = f"{col}_nuevo"

            valor_base_raw = row.get(col_base) # Usar .get para manejar columnas que puedan faltar
            valor_nuevo_raw = row.get(col_nuevo)

            # Determinar si la columna debe ser comparada numéricamente
            is_numeric = col.upper() in NUMERIC_COMPARISON_COLS

            # Usar la función de comparación robusta
            if not _compare_values_robustly(valor_base_raw, valor_nuevo_raw, is_numeric_col=is_numeric):
                has_changes = True
                
                # Para el mensaje, usamos los valores raw para que sean exactamente como aparecen en el archivo
                resultados_comparacion.append(
                    ResultadoValidacion(
                        tipo=TipoError.ADVERTENCIA, # Esto se puede ajustar a ERROR si el cambio de fecha es crítico
                        categoria="COMPARACION_MODIFICACION",
                        mensaje=f"Cambio en '{col}' para '{nombre_completo}': de '{valor_base_raw}' a '{valor_nuevo_raw}'.",
                        fila=real_fila_nuevo,
                        columna=col,
                        valor=str(valor_nuevo_raw) if pd.notna(valor_nuevo_raw) else ""
                    )
                )
    if not modificaciones_df.empty:
        logger.info("Detectadas %d posibles modificaciones en la comparación.", len(modificaciones_df))

    # Eliminar la columna temporal de clave compuesta
    df_base = df_base.drop(columns=['__clave_persona__'], errors='ignore')
    df_nuevo = df_nuevo.drop(columns=['__clave_persona__'], errors='ignore')
    
    return resultados_comparacion
