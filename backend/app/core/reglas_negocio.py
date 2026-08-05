"""
Reglas de negocio para la validación de macros de emisión AXA — PoC Distribución.

Reglas obligatorias implementadas:
  RN-01  Duplicados por clave (apellidos + nombre + fecha_nac + certificado)
  RN-02  Fecha de nacimiento inválida o futura
  RN-03  Fecha de antigüedad anterior a fecha de nacimiento
  RN-04  Certificado sin titular
  RN-05  Más de un cónyuge por certificado
  RN-06  Más de un titular por certificado
  RN-07  Edad límite: Titular/Cónyuge > 64 años (error); Beneficiario > 24 años (error)
  RN-08  Excepción de renovación: permite Titular/Cónyuge hasta 75 años
          si TIENE_ENDOSO=true y COMENTARIO no está vacío

Agregar nuevas reglas:
  1. Define una función  def regla_xxx(df) -> list[ResultadoValidacion]
  2. Agrégala a REGLAS_ACTIVAS al final del archivo.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Callable

import pandas as pd

from ..models.macro_models import ResultadoValidacion, TipoError

# ─── Constantes ───────────────────────────────────────────────────────────────

# Columnas mínimas que debe tener la macro GMM
COLUMNAS_REQUERIDAS: set[str] = {
    "NOMBRE",
    "APELLIDO_PATERNO",
    "APELLIDO_MATERNO",
    "FECHA_NACIMIENTO",
    "FECHA_ANTIGUEDAD",
    "PARENTESCO",
    "CERTIFICADO",
}

# Columnas mínimas para AP (sin parentesco ni antigüedad)
COLUMNAS_REQUERIDAS_AP: set[str] = {
    "NOMBRE",
    "APELLIDO_PATERNO",
    "APELLIDO_MATERNO",
    "FECHA_NACIMIENTO",
    "CERTIFICADO",
}

# Columnas adicionales requeridas en Renovación GMM
COLUMNAS_EXTRA_RENOVACION_GMM: set[str] = {
    "TIPO_MOVIMIENTO",
    "NUMERO_POLIZA",
}

# Parentescos válidos del catálogo AXA
PARENTESCOS_VALIDOS = {"Titular", "Cónyuge", "Conyuge", "Hijo", "Padre", "Madre", "Beneficiario"}
PARENTESCOS_CONYUGE = {"Cónyuge", "Conyuge"}
PARENTESCOS_TITULAR = {"Titular"}
PARENTESCOS_BENEFICIARIO = {"Hijo", "Padre", "Madre", "Beneficiario"}

# Tipos de movimiento válidos en renovación
TIPOS_MOVIMIENTO_VALIDOS = {"ALTA", "BAJA", "CAMBIO", "MODIFICACION", "MODIFICACIÓN", "REACTIVACION", "REACTIVACIÓN"}

# Límites de edad (RN-07)
EDAD_LIMITE_TITULAR_CONYUGE_NUEVA = 64        # Póliza nueva
EDAD_LIMITE_TITULAR_CONYUGE_RENOVACION = 70   # Renovación
EDAD_LIMITE_BENEFICIARIO = 24
EDAD_LIMITE_RENOVACION = 75                   # excepción con endoso (RN-08)

# Valores "verdadero" para la columna TIENE_ENDOSO
VALORES_ENDOSO_TRUE = {"true", "si", "sí", "1", "yes", "x", "s"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _err(categoria: str, mensaje: str, fila: int | None = None,
         columna: str | None = None, valor: str | None = None) -> ResultadoValidacion:
    return ResultadoValidacion(
        tipo=TipoError.ERROR, categoria=categoria,
        mensaje=mensaje, fila=fila, columna=columna, valor=valor,
    )


def _warn(categoria: str, mensaje: str, fila: int | None = None,
          columna: str | None = None, valor: str | None = None) -> ResultadoValidacion:
    return ResultadoValidacion(
        tipo=TipoError.ADVERTENCIA, categoria=categoria,
        mensaje=mensaje, fila=fila, columna=columna, valor=valor,
    )


def _col(df: pd.DataFrame, *candidatos: str) -> str | None:
    """Devuelve el primer candidato que exista como columna (case-insensitive)."""
    col_map = {c.upper(): c for c in df.columns}
    for c in candidatos:
        if c.upper() in col_map:
            return col_map[c.upper()]
    return None


def _parse_fecha(valor: object) -> date | None:
    """Parsea fecha desde múltiples formatos comunes."""
    if isinstance(valor, (datetime, pd.Timestamp)):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%y"):
            try:
                return datetime.strptime(valor.strip(), fmt).date()
            except ValueError:
                continue
    return None


def _edad(fecha_nac: date) -> int:
    hoy = date.today()
    return hoy.year - fecha_nac.year - (
        (hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day)
    )


def _tiene_endoso(row: pd.Series, col_endoso: str | None, col_comentario: str | None) -> bool:
    """Devuelve True si la fila tiene endoso autorizado con comentario."""
    if not col_endoso:
        return False
    val_endoso = str(row.get(col_endoso, "")).strip().lower()
    if val_endoso not in VALORES_ENDOSO_TRUE:
        return False
    if col_comentario:
        comentario = str(row.get(col_comentario, "")).strip()
        return len(comentario) >= 5   # debe tener texto real
    return False


# ─── Regla RN-00: columnas requeridas ────────────────────────────────────────

def regla_columnas_requeridas(
    df: pd.DataFrame,
    tipo_accion: str = "nueva",
    tipo_producto: str = "GMM",
) -> list[ResultadoValidacion]:
    """Verifica que todas las columnas obligatorias estén presentes."""
    col_map_upper = set(df.columns.str.upper())

    # Seleccionar conjunto base según producto
    base = COLUMNAS_REQUERIDAS if tipo_producto == "GMM" else COLUMNAS_REQUERIDAS_AP
    faltantes: set[str] = set(base) - col_map_upper

    # Alias: FECHA_ANTIGUEDAD ↔ ANTIGUEDAD (solo GMM)
    if "FECHA_ANTIGUEDAD" in faltantes and "ANTIGUEDAD" in col_map_upper:
        faltantes.discard("FECHA_ANTIGUEDAD")

    # Renovación GMM necesita columnas extra
    if tipo_accion == "renovacion" and tipo_producto == "GMM":
        faltantes |= COLUMNAS_EXTRA_RENOVACION_GMM - col_map_upper

    return [
        _err("Estructura", f"Columna requerida ausente en la macro: '{col}'", columna=col)
        for col in sorted(faltantes)
    ]


# ─── Regla RN-01: duplicados por clave de persona ────────────────────────────

def regla_duplicados_persona(df: pd.DataFrame) -> list[ResultadoValidacion]:
    """
    RN-01 — Duplicados por clave compuesta:
    APELLIDO_PATERNO + APELLIDO_MATERNO + NOMBRE + FECHA_NACIMIENTO + CERTIFICADO.
    """
    resultados: list[ResultadoValidacion] = []
    cols_clave = ["APELLIDO_PATERNO", "APELLIDO_MATERNO", "NOMBRE", "FECHA_NACIMIENTO", "CERTIFICADO"]
    col_map = {c.upper(): c for c in df.columns}

    cols_presentes = [col_map[c] for c in cols_clave if c in col_map]
    if len(cols_presentes) < 3:   # mínimo para que tenga sentido
        return resultados

    claves: dict[tuple, list[int]] = defaultdict(list)
    for idx, row in df.iterrows():
        clave = tuple(str(row.get(c, "")).strip().upper() for c in cols_presentes)
        claves[clave].append(int(idx))

    for clave, filas in claves.items():
        if len(filas) > 1:
            for idx in filas:
                resultados.append(_err(
                    "Duplicados",
                    f"Persona duplicada (misma clave en filas {[f+2 for f in filas]}): "
                    f"{' | '.join(str(v) for v in clave if v)}",
                    fila=idx + 2,
                    columna="CERTIFICADO + NOMBRE + APELLIDOS + FECHA_NACIMIENTO",
                ))
    return resultados


# ─── Regla RN-02: fecha de nacimiento inválida o futura ──────────────────────

def regla_fecha_nacimiento(df: pd.DataFrame) -> list[ResultadoValidacion]:
    """RN-02 — Fecha de nacimiento inválida o futura."""
    resultados: list[ResultadoValidacion] = []
    col = _col(df, "FECHA_NACIMIENTO")
    if not col:
        return resultados

    hoy = date.today()
    for idx, val in df[col].items():
        if pd.isna(val) or str(val).strip() == "":
            continue
        fecha = _parse_fecha(val)
        if fecha is None:
            resultados.append(_err(
                "Fecha de nacimiento",
                f"Formato de fecha inválido: '{val}'. Use DD/MM/YYYY.",
                fila=int(idx) + 2, columna=col, valor=str(val),
            ))
        elif fecha > hoy:
            resultados.append(_err(
                "Fecha de nacimiento",
                f"Fecha de nacimiento en el futuro: '{val}'.",
                fila=int(idx) + 2, columna=col, valor=str(val),
            ))
    return resultados


# ─── Regla RN-03: antigüedad anterior a fecha de nacimiento ──────────────────

def regla_antiguedad_vs_nacimiento(df: pd.DataFrame) -> list[ResultadoValidacion]:
    """RN-03 — La fecha de antigüedad no puede ser anterior a la fecha de nacimiento."""
    resultados: list[ResultadoValidacion] = []
    col_nac = _col(df, "FECHA_NACIMIENTO")
    col_ant = _col(df, "FECHA_ANTIGUEDAD", "ANTIGUEDAD")
    if not col_nac or not col_ant:
        return resultados

    for idx, row in df.iterrows():
        fecha_nac = _parse_fecha(row.get(col_nac))
        fecha_ant = _parse_fecha(row.get(col_ant))
        if fecha_nac and fecha_ant and fecha_ant < fecha_nac:
            resultados.append(_err(
                "Antigüedad inválida",
                f"Fecha de antigüedad ({row.get(col_ant)}) anterior a fecha de nacimiento ({row.get(col_nac)}).",
                fila=int(idx) + 2, columna=col_ant,
                valor=str(row.get(col_ant)),
            ))
    return resultados


# ─── Regla RN-04: certificado sin titular ────────────────────────────────────

def regla_certificado_sin_titular(df: pd.DataFrame) -> list[ResultadoValidacion]:
    """RN-04 — Cada certificado debe tener exactamente un titular."""
    resultados: list[ResultadoValidacion] = []
    col_cert = _col(df, "CERTIFICADO")
    col_par = _col(df, "PARENTESCO")
    if not col_cert or not col_par:
        return resultados

    for cert, grupo in df.groupby(col_cert):
        titulares = grupo[grupo[col_par].str.strip().isin(PARENTESCOS_TITULAR)]
        if titulares.empty:
            # Reportar en la primera fila del certificado
            primera_fila = int(grupo.index[0]) + 2
            resultados.append(_err(
                "Certificado sin titular",
                f"El certificado '{cert}' no tiene ningún registro con parentesco 'Titular'.",
                fila=primera_fila, columna=col_cert, valor=str(cert),
            ))
    return resultados


# ─── Regla RN-05: más de un cónyuge por certificado ─────────────────────────

def regla_conyuge_unico(df: pd.DataFrame) -> list[ResultadoValidacion]:
    """RN-05 — Solo se permite un cónyuge por certificado."""
    resultados: list[ResultadoValidacion] = []
    col_cert = _col(df, "CERTIFICADO")
    col_par = _col(df, "PARENTESCO")
    if not col_cert or not col_par:
        return resultados

    for cert, grupo in df.groupby(col_cert):
        conyuges = grupo[grupo[col_par].str.strip().isin(PARENTESCOS_CONYUGE)]
        if len(conyuges) > 1:
            for idx in conyuges.index:
                resultados.append(_err(
                    "Cónyuge duplicado",
                    f"El certificado '{cert}' tiene {len(conyuges)} cónyuge(s). Solo se permite uno.",
                    fila=int(idx) + 2, columna=col_par, valor=str(cert),
                ))
    return resultados


# ─── Regla RN-06: más de un titular por certificado ─────────────────────────

def regla_titular_unico(df: pd.DataFrame) -> list[ResultadoValidacion]:
    """RN-06 — Solo se permite un titular por certificado."""
    resultados: list[ResultadoValidacion] = []
    col_cert = _col(df, "CERTIFICADO")
    col_par = _col(df, "PARENTESCO")
    if not col_cert or not col_par:
        return resultados

    for cert, grupo in df.groupby(col_cert):
        titulares = grupo[grupo[col_par].str.strip().isin(PARENTESCOS_TITULAR)]
        if len(titulares) > 1:
            for idx in titulares.index:
                resultados.append(_err(
                    "Titular duplicado",
                    f"El certificado '{cert}' tiene {len(titulares)} titulares. Solo se permite uno.",
                    fila=int(idx) + 2, columna=col_par, valor=str(cert),
                ))
    return resultados


# ─── Regla RN-07 + RN-08: edad límite con excepción de renovación ────────────

def regla_edad_limite(
    df: pd.DataFrame,
    tipo_accion: str = "nueva",
) -> list[ResultadoValidacion]:
    """
    RN-07 — Titular/Cónyuge > límite: error.
             Beneficiario > 24 años: error.
    RN-08 — Excepción: Titular/Cónyuge hasta 75 con TIENE_ENDOSO=SI + COMENTARIO.
             Por encima de 75 → siempre error.

    Límite edad Titular/Cónyuge:
      - Póliza nueva:   64 años
      - Renovación:     70 años
    """
    resultados: list[ResultadoValidacion] = []
    limite = (
        EDAD_LIMITE_TITULAR_CONYUGE_RENOVACION
        if tipo_accion == "renovacion"
        else EDAD_LIMITE_TITULAR_CONYUGE_NUEVA
    )

    col_nac = _col(df, "FECHA_NACIMIENTO")
    col_par = _col(df, "PARENTESCO")
    col_endoso = _col(df, "TIENE_ENDOSO", "ENDOSO", "EXCEPCION")
    col_comentario = _col(df, "COMENTARIO", "COMENTARIO_ENDOSO", "OBSERVACIONES")

    if not col_nac or not col_par:
        return resultados

    for idx, row in df.iterrows():
        fecha_nac = _parse_fecha(row.get(col_nac))
        parentesco = str(row.get(col_par, "")).strip()
        if not fecha_nac or not parentesco:
            continue

        edad = _edad(fecha_nac)
        fila = int(idx) + 2
        val_fecha = str(row.get(col_nac))

        es_titular_conyuge = parentesco in (PARENTESCOS_TITULAR | PARENTESCOS_CONYUGE)
        es_beneficiario = parentesco in PARENTESCOS_BENEFICIARIO

        if es_titular_conyuge and edad > limite:
            con_endoso = _tiene_endoso(row, col_endoso, col_comentario)

            if edad > EDAD_LIMITE_RENOVACION:
                resultados.append(_err(
                    "Edad fuera de límite",
                    f"{parentesco} con {edad} años supera el máximo absoluto "
                    f"({EDAD_LIMITE_RENOVACION} años). No se puede incluir.",
                    fila=fila, columna=col_nac, valor=val_fecha,
                ))
            elif con_endoso:
                resultados.append(_warn(
                    "Excepción de renovación",
                    f"{parentesco} con {edad} años (> {limite}). "
                    f"Incluido por excepción con endoso autorizado.",
                    fila=fila, columna=col_nac, valor=val_fecha,
                ))
            else:
                hint = (
                    f" Para incluirlo, complete '{col_endoso}' y '{col_comentario}'."
                    if col_endoso
                    else " Agregue columna 'TIENE_ENDOSO'=SI y 'COMENTARIO' con justificación."
                )
                resultados.append(_err(
                    "Edad fuera de límite",
                    f"{parentesco} con {edad} años supera el límite de {limite} años.{hint}",
                    fila=fila, columna=col_nac, valor=val_fecha,
                ))

        elif es_beneficiario and edad > EDAD_LIMITE_BENEFICIARIO:
            resultados.append(_err(
                "Edad fuera de límite",
                f"{parentesco} con {edad} años supera el límite de "
                f"{EDAD_LIMITE_BENEFICIARIO} años para beneficiarios.",
                fila=fila, columna=col_nac, valor=val_fecha,
            ))

    return resultados


# ─── Regla RN-09 (Renovación): tipo de movimiento válido ─────────────────────

def regla_tipo_movimiento(df: pd.DataFrame) -> list[ResultadoValidacion]:
    """RN-09 (solo Renovación GMM) — TIPO_MOVIMIENTO debe ser un valor del catálogo."""
    resultados: list[ResultadoValidacion] = []
    col = _col(df, "TIPO_MOVIMIENTO")
    if not col:
        return resultados

    for idx, val in df[col].items():
        if pd.isna(val) or str(val).strip() == "":
            resultados.append(_err(
                "Tipo de movimiento",
                "El campo TIPO_MOVIMIENTO está vacío. Valores válidos: "
                f"{', '.join(sorted(TIPOS_MOVIMIENTO_VALIDOS))}.",
                fila=int(idx) + 2, columna=col,
            ))
        elif str(val).strip().upper() not in TIPOS_MOVIMIENTO_VALIDOS:
            resultados.append(_err(
                "Tipo de movimiento",
                f"Valor inválido en TIPO_MOVIMIENTO: '{val}'. Valores válidos: "
                f"{', '.join(sorted(TIPOS_MOVIMIENTO_VALIDOS))}.",
                fila=int(idx) + 2, columna=col, valor=str(val),
            ))
    return resultados


# ─── Función principal: obtener reglas según tipo ────────────────────────────

def obtener_reglas(tipo_accion: str, tipo_producto: str) -> list[Callable]:
    """
    Devuelve la lista de funciones de validación apropiadas para la combinación
    tipo_accion (nueva | renovacion) × tipo_producto (GMM | AP).
    """
    # Reglas base aplicables a todos
    reglas_base: list[Callable] = [
        lambda df: regla_columnas_requeridas(df, tipo_accion, tipo_producto),  # RN-00
        regla_duplicados_persona,                                               # RN-01
        regla_fecha_nacimiento,                                                 # RN-02
    ]

    # Reglas exclusivas de GMM (tiene PARENTESCO, ANTIGÜEDAD)
    reglas_gmm: list[Callable] = [
        regla_antiguedad_vs_nacimiento,     # RN-03
        regla_certificado_sin_titular,      # RN-04
        regla_conyuge_unico,                # RN-05
        regla_titular_unico,               # RN-06
        lambda df: regla_edad_limite(df, tipo_accion),  # RN-07 + RN-08
    ]

    # Reglas exclusivas de AP (sin parentesco)
    reglas_ap: list[Callable] = [
        lambda df: regla_edad_limite(df, tipo_accion),  # RN-07 + RN-08 (sin parentesco → no aplica edad, se omite)
    ]

    # Reglas exclusivas de Renovación
    reglas_renovacion: list[Callable] = [
        regla_tipo_movimiento,              # RN-09
    ]

    if tipo_producto == "GMM":
        reglas = reglas_base + reglas_gmm
    else:
        reglas = reglas_base + reglas_ap

    if tipo_accion == "renovacion":
        reglas += reglas_renovacion

    return reglas


# ─── Registro de reglas activas (compatibilidad hacia atrás) ─────────────────
REGLAS_ACTIVAS: list[Callable[[pd.DataFrame], list[ResultadoValidacion]]] = [
    regla_columnas_requeridas,      # RN-00
    regla_duplicados_persona,       # RN-01
    regla_fecha_nacimiento,         # RN-02
    regla_antiguedad_vs_nacimiento, # RN-03
    regla_certificado_sin_titular,  # RN-04
    regla_conyuge_unico,            # RN-05
    regla_titular_unico,            # RN-06
    regla_edad_limite,              # RN-07 + RN-08
]
