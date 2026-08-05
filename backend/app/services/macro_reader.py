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

# ─── Mapa de layouts: (tipo_accion, tipo_producto) → (nombre_hoja, fila_header)
LAYOUT_MAP: dict[tuple[str, str], tuple[str, int]] = {
    ("nueva",      "GMM"): ("Layout Poliza Nueva",    7),
    ("renovacion", "GMM"): ("Layout Renovaciones",    7),
    ("nueva",      "AP"):  ("Layout PN AP",            1),
    ("renovacion", "AP"):  ("Layout Renovaciones AP", 1),
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
) -> pd.DataFrame:
    """
    Lee la macro y devuelve un DataFrame con columnas normalizadas.

    Args:
        filename:      Nombre original del archivo.
        content:       Bytes del archivo.
        tipo_accion:   "nueva" o "renovacion".
        tipo_producto: "GMM" o "AP".

    Returns:
        pd.DataFrame con columnas canonicas sin acentos.
    """
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    if ext in {".xlsx", ".xls", ".xlsm"}:
        df = _leer_excel(filename, content, tipo_accion, tipo_producto)
    elif ext == ".csv":
        df = _leer_csv(content)
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
    return df


def _leer_excel(
    filename: str,
    content: bytes,
    tipo_accion: TipoAccion,
    tipo_producto: TipoProducto,
) -> pd.DataFrame:
    clave = (tipo_accion, tipo_producto)
    nombre_hoja, fila_header = LAYOUT_MAP.get(clave, (None, 7))

    try:
        excel = pd.ExcelFile(io.BytesIO(content))

        if nombre_hoja and nombre_hoja in excel.sheet_names:
            logger.info(
                "Leyendo hoja oficial '%s' (header en fila %d)",
                nombre_hoja, fila_header,
            )
            df = pd.read_excel(
                excel,
                sheet_name=nombre_hoja,
                header=fila_header - 1,  # pandas usa 0-based
                dtype=str,
            )
        else:
            hoja_fallback = excel.sheet_names[0]
            logger.warning(
                "Hoja '%s' no encontrada. Usando primera hoja: '%s'",
                nombre_hoja, hoja_fallback,
            )
            df = pd.read_excel(excel, sheet_name=hoja_fallback, dtype=str)

        df = df.dropna(how="all")
        df = df.loc[:, df.columns.notna()]
        df = df[df.columns[~df.columns.astype(str).str.startswith("Unnamed")]]
        return df

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
