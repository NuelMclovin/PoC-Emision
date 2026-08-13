"""
Tests de las reglas de negocio — PoC Validación de Macros de Emisión AXA.
Ejecutar con: poetry run pytest  (o .venv\\Scripts\\python -m pytest)
"""
from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import pytest

from app.core.reglas_negocio import (
    regla_antiguedad_vs_nacimiento,
    regla_certificado_sin_titular,
    regla_columnas_requeridas,
    regla_conyuge_unico,
    regla_duplicados_persona,
    regla_edad_limite,
    regla_fecha_nacimiento,
    regla_titular_unico,
)
from app.models.macro_models import TipoError
from app.services.macro_reader import leer_macro


# ─── Helper para construir DataFrames de prueba ───────────────────────────────

def _fila(**kwargs) -> dict:
    """Fila base válida. Se puede sobreescribir cualquier campo."""
    base = {
        "NOMBRE": "Juan",
        "APELLIDO_PATERNO": "García",
        "APELLIDO_MATERNO": "López",
        "FECHA_NACIMIENTO": "01/01/1985",
        "FECHA_ANTIGUEDAD": "01/01/2010",
        "PARENTESCO": "Titular",
        "CERTIFICADO": "CERT-001",
    }
    base.update(kwargs)
    return base


def _df(*filas: dict) -> pd.DataFrame:
    return pd.DataFrame(list(filas))


def _csv_bytes(*filas: list[str]) -> bytes:
    texto = "\n".join(",".join(fila) for fila in filas)
    return texto.encode("utf-8")


# ─── RN-00: columnas requeridas ───────────────────────────────────────────────

def test_columnas_requeridas_ok():
    assert regla_columnas_requeridas(_df(_fila())) == []


def test_columnas_requeridas_falta_certificado():
    df = _df(_fila()).drop(columns=["CERTIFICADO"])
    resultados = regla_columnas_requeridas(df)
    assert any("CERTIFICADO" in r.mensaje for r in resultados)


def test_columnas_antiguedad_alias():
    """ANTIGUEDAD es alias válido de FECHA_ANTIGUEDAD."""
    df = _df(_fila()).rename(columns={"FECHA_ANTIGUEDAD": "ANTIGUEDAD"})
    assert regla_columnas_requeridas(df) == []


# ─── RN-01: duplicados por clave de persona ───────────────────────────────────

def test_duplicado_detectado():
    df = _df(_fila(), _fila())   # misma persona, mismo certificado
    resultados = regla_duplicados_persona(df)
    assert any(r.tipo == TipoError.ERROR for r in resultados)


def test_sin_duplicado():
    df = _df(_fila(CERTIFICADO="CERT-001"), _fila(NOMBRE="María", CERTIFICADO="CERT-002"))
    assert regla_duplicados_persona(df) == []


# ─── RN-02: fecha de nacimiento ───────────────────────────────────────────────

def test_fecha_nacimiento_futura():
    futura = (date.today() + timedelta(days=10)).strftime("%d/%m/%Y")
    df = _df(_fila(FECHA_NACIMIENTO=futura))
    resultados = regla_fecha_nacimiento(df)
    assert any(r.tipo == TipoError.ERROR for r in resultados)


def test_fecha_nacimiento_formato_invalido():
    df = _df(_fila(FECHA_NACIMIENTO="32/13/1990"))
    resultados = regla_fecha_nacimiento(df)
    assert any(r.tipo == TipoError.ERROR for r in resultados)


def test_fecha_nacimiento_valida():
    assert regla_fecha_nacimiento(_df(_fila())) == []


# ─── RN-03: antigüedad vs nacimiento ─────────────────────────────────────────

def test_antiguedad_anterior_a_nacimiento():
    df = _df(_fila(FECHA_NACIMIENTO="01/01/1990", FECHA_ANTIGUEDAD="01/01/1985"))
    resultados = regla_antiguedad_vs_nacimiento(df)
    assert any(r.tipo == TipoError.ERROR for r in resultados)


def test_antiguedad_valida():
    df = _df(_fila(FECHA_NACIMIENTO="01/01/1985", FECHA_ANTIGUEDAD="01/01/2010"))
    assert regla_antiguedad_vs_nacimiento(df) == []


# ─── RN-04: certificado sin titular ──────────────────────────────────────────

def test_certificado_sin_titular():
    df = _df(_fila(PARENTESCO="Cónyuge"))
    resultados = regla_certificado_sin_titular(df)
    assert any(r.tipo == TipoError.ERROR for r in resultados)


def test_certificado_con_titular():
    df = _df(_fila(PARENTESCO="Titular"), _fila(PARENTESCO="Cónyuge"))
    assert regla_certificado_sin_titular(df) == []


# ─── RN-05: cónyuge único ────────────────────────────────────────────────────

def test_dos_conyuges_mismo_certificado():
    df = _df(
        _fila(PARENTESCO="Titular", NOMBRE="Juan"),
        _fila(PARENTESCO="Cónyuge", NOMBRE="Ana", CERTIFICADO="CERT-001"),
        _fila(PARENTESCO="Cónyuge", NOMBRE="Laura", CERTIFICADO="CERT-001"),
    )
    resultados = regla_conyuge_unico(df)
    assert any(r.tipo == TipoError.ERROR for r in resultados)


def test_conyuge_unico_ok():
    df = _df(_fila(PARENTESCO="Titular"), _fila(PARENTESCO="Cónyuge", NOMBRE="Ana"))
    assert regla_conyuge_unico(df) == []


# ─── RN-06: titular único ────────────────────────────────────────────────────

def test_dos_titulares_mismo_certificado():
    df = _df(_fila(NOMBRE="Juan"), _fila(NOMBRE="Pedro"))  # ambos Titular
    resultados = regla_titular_unico(df)
    assert any(r.tipo == TipoError.ERROR for r in resultados)


def test_titular_unico_ok():
    df = _df(_fila(PARENTESCO="Titular"), _fila(PARENTESCO="Hijo", NOMBRE="Ana"))
    assert regla_titular_unico(df) == []


# ─── RN-07: edad límite ───────────────────────────────────────────────────────

def test_titular_mayor_64_sin_endoso():
    nac = date(date.today().year - 66, 1, 1).strftime("%d/%m/%Y")
    df = _df(_fila(FECHA_NACIMIENTO=nac, PARENTESCO="Titular"))
    resultados = regla_edad_limite(df)
    assert any(r.tipo == TipoError.ERROR for r in resultados)


def test_beneficiario_mayor_24():
    nac = date(date.today().year - 26, 1, 1).strftime("%d/%m/%Y")
    df = _df(_fila(FECHA_NACIMIENTO=nac, PARENTESCO="Hijo"))
    resultados = regla_edad_limite(df)
    assert any(r.tipo == TipoError.ERROR for r in resultados)


def test_beneficiario_menor_o_igual_24_ok():
    nac = date(date.today().year - 22, 1, 1).strftime("%d/%m/%Y")
    df = _df(_fila(FECHA_NACIMIENTO=nac, PARENTESCO="Hijo"))
    assert regla_edad_limite(df) == []


# ─── RN-08: excepción de renovación ──────────────────────────────────────────

def test_titular_65_con_endoso_y_comentario_es_advertencia():
    nac = date(date.today().year - 68, 1, 1).strftime("%d/%m/%Y")
    df = _df(_fila(
        FECHA_NACIMIENTO=nac,
        PARENTESCO="Titular",
        TIENE_ENDOSO="SI",
        COMENTARIO="Renovación autorizada por gerencia, expediente 12345",
    ))
    resultados = regla_edad_limite(df)
    # No debe haber errores, solo advertencia
    errores = [r for r in resultados if r.tipo == TipoError.ERROR]
    advertencias = [r for r in resultados if r.tipo == TipoError.ADVERTENCIA]
    assert len(errores) == 0
    assert len(advertencias) == 1


def test_titular_mayor_75_con_endoso_siempre_error():
    nac = date(date.today().year - 76, 1, 1).strftime("%d/%m/%Y")
    df = _df(_fila(
        FECHA_NACIMIENTO=nac,
        PARENTESCO="Titular",
        TIENE_ENDOSO="SI",
        COMENTARIO="Renovación especial autorizada",
    ))
    resultados = regla_edad_limite(df)
    assert any(r.tipo == TipoError.ERROR for r in resultados)


def test_fecha_nacimiento_futura_reporta_mensaje_correcto():
    df = _df(_fila(FECHA_NACIMIENTO="2040-01-01"))
    resultados = regla_fecha_nacimiento(df)
    assert any("en el futuro" in r.mensaje.lower() for r in resultados)


# ─── CSV crudo sin encabezados ────────────────────────────────────────────────

def test_leer_csv_crudo_nueva_gmm_sin_encabezados():
    content = _csv_bytes(
        ["Juan", "García", "López", "01/01/1985", "01/01/2010", "Titular", "CERT-001"],
        ["Ana", "García", "López", "01/02/1987", "01/01/2010", "Cónyuge", "CERT-001"],
    )

    df, offset = leer_macro("prueba.csv", content, tipo_accion="nueva", tipo_producto="GMM")

    assert offset == 1
    assert list(df.columns) == [
        "NOMBRE",
        "APELLIDO_PATERNO",
        "APELLIDO_MATERNO",
        "FECHA_NACIMIENTO",
        "FECHA_ANTIGUEDAD",
        "PARENTESCO",
        "CERTIFICADO",
    ]
    assert df.iloc[0]["NOMBRE"] == "Juan"
    assert df.iloc[1]["PARENTESCO"] == "Cónyuge"


def test_leer_csv_crudo_renovacion_gmm_sin_encabezados():
    content = _csv_bytes(
        [
            "Juan", "García", "López", "01/01/1985", "01/01/2010",
            "Titular", "CERT-001", "ALTA", "POL-123"
        ],
    )

    df, offset = leer_macro("prueba.csv", content, tipo_accion="renovacion", tipo_producto="GMM")

    assert offset == 1
    assert list(df.columns) == [
        "NOMBRE",
        "APELLIDO_PATERNO",
        "APELLIDO_MATERNO",
        "FECHA_NACIMIENTO",
        "FECHA_ANTIGUEDAD",
        "PARENTESCO",
        "CERTIFICADO",
        "TIPO_MOVIMIENTO",
        "NUMERO_POLIZA",
    ]
    assert df.iloc[0]["TIPO_MOVIMIENTO"] == "ALTA"
    assert df.iloc[0]["NUMERO_POLIZA"] == "POL-123"


def test_leer_csv_crudo_nueva_gmm_con_fechas_guion_sin_corrimiento():
    content = _csv_bytes(
        ["FERNANDO", "PEREZ", "LOPEZ", "198-06-15", "2010-01-01", "Titular", "001"],
        ["MARIA", "PEREZ", "LOPEZ", "2040-01-01", "2010-01-01", "Hijo", "002"],
    )

    df, _ = leer_macro("prueba.csv", content, tipo_accion="nueva", tipo_producto="GMM")

    assert df.iloc[0]["FECHA_NACIMIENTO"] == "198-06-15"
    assert df.iloc[0]["FECHA_ANTIGUEDAD"] == "2010-01-01"
    assert df.iloc[1]["FECHA_NACIMIENTO"] == "2040-01-01"


def test_fecha_csv_acepta_guion_y_diagonal():
    df = _df(
        _fila(FECHA_NACIMIENTO="1985-01-01", FECHA_ANTIGUEDAD="2010/01/01"),
        _fila(FECHA_NACIMIENTO="01/02/1987", FECHA_ANTIGUEDAD="2011-02-01", CERTIFICADO="CERT-002"),
    )
    resultados = regla_fecha_nacimiento(df)
    assert resultados == []


def test_antiguedad_csv_acepta_guion_y_diagonal():
    df = _df(
        _fila(FECHA_NACIMIENTO="1985/01/01", FECHA_ANTIGUEDAD="2010-01-01"),
        _fila(FECHA_NACIMIENTO="1980-05-10", FECHA_ANTIGUEDAD="2012/06/01", CERTIFICADO="CERT-003"),
    )
    resultados = regla_antiguedad_vs_nacimiento(df)
    assert resultados == []
