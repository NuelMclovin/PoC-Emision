"""
Lectura y normalizacion de macros Excel (.xlsx / .xls / .xlsm / .csv).

Soporta los 4 layouts oficiales de AXA:
  - GMM Poliza Nueva     -> hoja "Layout Poliza Nueva",    header fila 7
  - GMM Renovacion       -> hoja "Layout Renovaciones",    header fila 7
  - AP  Poliza Nueva     -> hoja "Layout PN AP",           header fila 1
  - AP  Renovacion       -> hoja "Layout Renovaciones AP", header fila 1
"""
from __future__ import annotations

import io
import unicodedata
from typing import Literal

import chardet
import pandas as pd

from ..utils.logger import get_logger

logger = get_logger()

# ─── Tipos validos ────────────────────────────────────────────────────────────

TipoAccion = Literal["nueva", "renovacion"]
TipoProducto = Literal["GMM", "AP"]

# Mapa de layouts: (tipo_accion, tipo_producto) → (nombre_hoja, fila_header, filas_a_saltar)
LAYOUT_MAP: dict[tuple[str, str], tuple[str, int, list]] = {
    ("nueva",      "GMM"): ("Layout Poliza Nueva",    7, [7]),        # Salta fila 8 (subtítulos)
    ("renovacion", "GMM"): ("Layout Renovaciones",    7, [7, 8, 9]), # Salta filas 8, 9, 10
    ("nueva",      "AP"):  ("Layout PN AP",            1, []),        # No salta nada
    ("renovacion", "AP"):  ("Layout Renovaciones AP", 1, []),        # No salta nada
}


# ─── Normalizacion de nombres de columna ──────────────────────────────────────
# Todas las claves estan en ASCII MAYUSCULAS sin acentos.
# La funcion _quitar_acentos convierte primero el nombre antes del lookup.

ALIAS_COLUMNAS: dict[str, str] = {
    "APELLIDO PATERNO":      "APELLIDO_PATERNO",
    "APELLIDO MATERNO":      "APELLIDO_MATERNO",
    "NOMBRE (S)":            "NOMBRE",
    "NOMBRE(S)":             "NOMBRE",
    "NOMBRES":               "NOMBRE",
    "FECHA DE NACIMIENTO":   "FECHA_NACIMIENTO",
    "FECHA DE ANTIGUEDAD":   "FECHA_ANTIGUEDAD",
    "FECHA ANTIGUEDAD":      "FECHA_ANTIGUEDAD",
    "FECHA_DE_ANTIGUEDAD":   "FECHA_ANTIGUEDAD",
    "ANTIGUEDAD":            "FECHA_ANTIGUEDAD",
    "RESIDE EN MEXICO":      "RESIDE_EN_MEXICO",
    "ESTADO DE NACIMIENTO":  "ESTADO_NACIMIENTO",
    "TIPO DE MOVIMIENTO":    "TIPO_MOVIMIENTO",
    "FECHA DE MOVIMIENTO":   "FECHA_MOVIMIENTO",
    "NUMERO POLIZA":         "NUMERO_POLIZA",
    "NUMERO DE POLIZA":      "NUMERO_POLIZA",
    "POLIZA":                "NUMERO_POLIZA",
    "GENERO":                "GENERO",
    "CURP":                  "CURP",
    "SUBGRUPO":              "SUBGRUPO",
    "CERTIFICADO":           "CERTIFICADO",
    "PARENTESCO":            "PARENTESCO",
    "NACIONALIDAD":          "NACIONALIDAD",
    "DEBE DECIR":            "DEBE_DECIR",
    "DICE":                  "DICE",
}


def _quitar_acentos(texto: str) -> str:
    """Elimina diacriticos convirtiendo a ASCII puro (NFD + remove Mn category)."""
    normalizado = unicodedata.normalize("NFD", texto)
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn")


def _normalizar_nombre_col(nombre: str) -> str:
    """
    1. Mayusculas + strip.
    2. Quitar acentos (ASCII puro).
    3. Buscar en ALIAS_COLUMNAS; si no hay, reemplazar espacios por _.
    """
    limpio = _quitar_acentos(str(nombre).strip().upper())
    if limpio in ALIAS_COLUMNAS:
        return ALIAS_COLUMNAS[limpio]
    return (
        limpio
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .replace(".", "")
    )


def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [_normalizar_nombre_col(c) for c in df.columns]

    # NUEVO
    if "PARENTESCO" in df.columns:
        df["PARENTESCO"] =  df["PARENTESCO"].str.strip().str.capitalize()
    return df


def _detectar_encoding(data: bytes) -> str:
    resultado = chardet.detect(data)
    enc = resultado.get("encoding") or "utf-8"
    logger.debug(
        "Encoding detectado: %s (confianza %.1f%%)",
        enc,
        (resultado.get("confidence") or 0) * 100,
    )
    return enc


# ─── API publica ──────────────────────────────────────────────────────────────

def leer_macro(
    filename: str,
    content: bytes,
    tipo_accion: TipoAccion = "nueva",
    tipo_producto: TipoProducto = "GMM",
) -> tuple[pd.DataFrame, int]:  # ← Retorna también offset
    """
    Lee la macro y devuelve un DataFrame con columnas normalizadas.
    
    Returns:
        (DataFrame, offset_filas)
    """
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    if ext in {".xlsx", ".xls", ".xlsm"}:
        df, offset = _leer_excel(filename, content, tipo_accion, tipo_producto)
    elif ext == ".csv":
        df = _leer_csv(content)
        offset = 1  # CSV no tiene filas saltadas
    else:
        raise ValueError(
            f"Formato '{ext}' no soportado. Use .xlsx, .xls, .xlsm o .csv"
        )

    if df.empty:
        raise ValueError("El archivo no contiene registros.")

    df = _normalizar_columnas(df)
    df = df.reset_index(drop=True)
    logger.info(
        "Macro '%s' leida [%s/%s]: %d filas, columnas: %s",
        filename, tipo_accion, tipo_producto, len(df), list(df.columns),
    )
    return df, offset


def _leer_excel(
    filename: str,
    content: bytes,
    tipo_accion: TipoAccion,
    tipo_producto: TipoProducto,
) -> tuple[pd.DataFrame, int]:  # ← Retorna también el offset
    clave = (tipo_accion, tipo_producto)
    layout_info = LAYOUT_MAP.get(clave, (None, 7, []))
    nombre_hoja, fila_header, filas_saltar = layout_info

    try:
        excel = pd.ExcelFile(io.BytesIO(content))

        if nombre_hoja and nombre_hoja in excel.sheet_names:
            logger.info(
                "Leyendo hoja oficial '%s' (header en fila %d, saltando filas %s)",
                nombre_hoja, fila_header, filas_saltar,
            )
            
            df = pd.read_excel(
                excel,
                sheet_name=nombre_hoja,
                header=fila_header - 1,
                skiprows=filas_saltar,
            )
        else:
            hoja_fallback = excel.sheet_names[0]
            logger.warning(
                "Hoja '%s' no encontrada. Usando primera hoja: '%s'",
                nombre_hoja, hoja_fallback,
            )
            df = pd.read_excel(excel, sheet_name=hoja_fallback)

        df = df.dropna(how="all")
        df = df.loc[:, df.columns.notna()]
        df = df[df.columns[~df.columns.astype(str).str.startswith("Unnamed")]]
        
        # ✅ Calcular offset: fila_header + cantidad de filas saltadas
        offset = fila_header + len(filas_saltar)
        
        return df, offset

    except Exception as exc:
        raise ValueError(
            f"Error al leer el archivo Excel '{filename}': {exc}"
        ) from exc


def _leer_csv(content: bytes) -> pd.DataFrame:
    encoding = _detectar_encoding(content)
    for enc in dict.fromkeys(
        [encoding, "utf-8-sig", "iso-8859-1", "cp1252", "latin-1"]
    ):
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=enc, dtype=str)
            return df.dropna(how="all")
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError("No se pudo leer el CSV con ningun encoding conocido.")
