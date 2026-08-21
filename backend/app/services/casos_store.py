"""
Almacenamiento local de casos/folios en un archivo CSV.

Esta PoC no cuenta con base de datos: el CSV configurado en
`settings.casos_csv_path` funciona como la "tabla" de transacciones y
consultas de folios que conecta al frontend de bróker (que crea los casos)
con el frontend de suscriptor interno (que los revisa y resuelve).

Los archivos y el reporte de validación de cada folio se guardan aparte,
en el volumen de documentos gestionado por `app.services.documentos_store`.
"""
from __future__ import annotations

import csv
import os
import threading
from datetime import datetime, timezone
from typing import Optional

from ..config import get_settings
from ..models.casos_models import CasoResumen, EstadoCaso
from ..utils.logger import get_logger

logger = get_logger()

_LOCK = threading.Lock()

CSV_FIELDS: list[str] = [
    "folio",
    "empresa",
    "tipo_accion",
    "tipo_producto",
    "estado",
    "creado_por",
    "asignado_a",
    "fecha_creacion",
    "fecha_actualizacion",
    "total_registros",
    "total_titulares",
    "total_dependientes",
    "total_errores",
    "total_advertencias",
    "es_valida",
    "comentario_suscriptor",
    "nombre_archivo_macro",
]


def _csv_path() -> str:
    return get_settings().casos_csv_path


def _ensure_csv() -> None:
    ruta = _csv_path()
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    if not os.path.exists(ruta):
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()


def _leer_filas() -> list[dict[str, str]]:
    _ensure_csv()
    with open(_csv_path(), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _escribir_filas(filas: list[dict[str, str]]) -> None:
    _ensure_csv()
    with open(_csv_path(), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(filas)


def _fila_a_caso(fila: dict[str, str]) -> CasoResumen:
    return CasoResumen(
        folio=fila["folio"],
        empresa=fila["empresa"],
        tipo_accion=fila["tipo_accion"],  # type: ignore[arg-type]
        tipo_producto=fila["tipo_producto"],  # type: ignore[arg-type]
        estado=fila["estado"],  # type: ignore[arg-type]
        creado_por=fila["creado_por"],
        asignado_a=fila["asignado_a"] or None,
        fecha_creacion=datetime.fromisoformat(fila["fecha_creacion"]),
        fecha_actualizacion=datetime.fromisoformat(fila["fecha_actualizacion"]),
        total_registros=int(fila.get("total_registros") or 0),
        total_titulares=int(fila.get("total_titulares") or 0),
        total_dependientes=int(fila.get("total_dependientes") or 0),
        total_errores=int(fila.get("total_errores") or 0),
        total_advertencias=int(fila.get("total_advertencias") or 0),
        es_valida=(fila.get("es_valida") or "").strip().lower() == "true",
        comentario_suscriptor=fila.get("comentario_suscriptor") or "",
        nombre_archivo_macro=fila.get("nombre_archivo_macro") or "",
    )


def _caso_a_fila(caso: CasoResumen) -> dict[str, str]:
    return {
        "folio": caso.folio,
        "empresa": caso.empresa,
        "tipo_accion": caso.tipo_accion,
        "tipo_producto": caso.tipo_producto,
        "estado": caso.estado.value if isinstance(caso.estado, EstadoCaso) else caso.estado,
        "creado_por": caso.creado_por,
        "asignado_a": caso.asignado_a or "",
        "fecha_creacion": caso.fecha_creacion.isoformat(),
        "fecha_actualizacion": caso.fecha_actualizacion.isoformat(),
        "total_registros": str(caso.total_registros),
        "total_titulares": str(caso.total_titulares),
        "total_dependientes": str(caso.total_dependientes),
        "total_errores": str(caso.total_errores),
        "total_advertencias": str(caso.total_advertencias),
        "es_valida": "True" if caso.es_valida else "False",
        "comentario_suscriptor": caso.comentario_suscriptor or "",
        "nombre_archivo_macro": caso.nombre_archivo_macro or "",
    }


def generar_folio() -> str:
    """Genera un folio secuencial tipo FOL-<anio>-<consecutivo>."""
    anio = datetime.now(tz=timezone.utc).year
    filas = _leer_filas()
    consecutivo = len(filas) + 1
    folio = f"FOL-{anio}-{consecutivo:04d}"
    # Evita colisiones si hubo folios eliminados manualmente del CSV.
    existentes = {f["folio"] for f in filas}
    while folio in existentes:
        consecutivo += 1
        folio = f"FOL-{anio}-{consecutivo:04d}"
    return folio


def crear_caso(
    *,
    empresa: str,
    tipo_accion: str,
    tipo_producto: str,
    creado_por: str,
    nombre_archivo_macro: str,
    total_registros: int = 0,
    total_titulares: int = 0,
    total_dependientes: int = 0,
    total_errores: int = 0,
    total_advertencias: int = 0,
    es_valida: bool = False,
) -> CasoResumen:
    with _LOCK:
        ahora = datetime.now(tz=timezone.utc)
        caso = CasoResumen(
            folio=generar_folio(),
            empresa=empresa,
            tipo_accion=tipo_accion,  # type: ignore[arg-type]
            tipo_producto=tipo_producto,  # type: ignore[arg-type]
            estado=EstadoCaso.PENDIENTE,
            creado_por=creado_por,
            asignado_a=None,
            fecha_creacion=ahora,
            fecha_actualizacion=ahora,
            total_registros=total_registros,
            total_titulares=total_titulares,
            total_dependientes=total_dependientes,
            total_errores=total_errores,
            total_advertencias=total_advertencias,
            es_valida=es_valida,
            comentario_suscriptor="",
            nombre_archivo_macro=nombre_archivo_macro,
        )
        filas = _leer_filas()
        filas.append(_caso_a_fila(caso))
        _escribir_filas(filas)
        logger.info("Caso creado: %s (%s) por %s", caso.folio, caso.empresa, creado_por)
        return caso


def listar_casos(
    *,
    estado: Optional[str] = None,
    tipo_accion: Optional[str] = None,
    tipo_producto: Optional[str] = None,
    creado_por: Optional[str] = None,
    asignado_a: Optional[str] = None,
) -> list[CasoResumen]:
    casos = [_fila_a_caso(f) for f in _leer_filas()]

    if estado:
        casos = [c for c in casos if c.estado.value == estado]
    if tipo_accion:
        casos = [c for c in casos if c.tipo_accion == tipo_accion]
    if tipo_producto:
        casos = [c for c in casos if c.tipo_producto == tipo_producto]
    if creado_por:
        casos = [c for c in casos if c.creado_por == creado_por]
    if asignado_a:
        casos = [c for c in casos if c.asignado_a == asignado_a]

    casos.sort(key=lambda c: c.fecha_creacion, reverse=True)
    return casos


def obtener_caso(folio: str) -> Optional[CasoResumen]:
    for fila in _leer_filas():
        if fila["folio"] == folio:
            return _fila_a_caso(fila)
    return None


def actualizar_caso(folio: str, cambios: dict) -> Optional[CasoResumen]:
    """Aplica cambios parciales (estado, asignado_a, comentario_suscriptor) a un folio."""
    with _LOCK:
        filas = _leer_filas()
        actualizado: Optional[CasoResumen] = None

        for fila in filas:
            if fila["folio"] != folio:
                continue

            caso = _fila_a_caso(fila)
            data = caso.model_dump()
            for clave, valor in cambios.items():
                if valor is not None and clave in data:
                    data[clave] = valor
            data["fecha_actualizacion"] = datetime.now(tz=timezone.utc)
            actualizado = CasoResumen(**data)
            fila.clear()
            fila.update(_caso_a_fila(actualizado))
            break

        if actualizado is not None:
            _escribir_filas(filas)
            logger.info("Caso actualizado: %s -> %s", folio, cambios)

        return actualizado


def eliminar_caso(folio: str) -> bool:
    with _LOCK:
        filas = _leer_filas()
        nuevas = [f for f in filas if f["folio"] != folio]
        if len(nuevas) == len(filas):
            return False
        _escribir_filas(nuevas)
        logger.info("Caso eliminado: %s", folio)
        return True