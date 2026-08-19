"""
Volumen local de documentos por caso/folio.

Cada folio tiene su propia carpeta dentro de `settings.documentos_dir` con la
siguiente estructura:

    <documentos_dir>/<folio>/
        macro/<archivo original de censo>
        anexos/<otros documentos subidos por broker o suscriptor>
        reporte_validacion.json   (snapshot del ReporteValidacion del backend)

Esto sustituye a una base de datos documental: el "volumen" es simplemente
el filesystem local montado para la PoC.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import get_settings
from ..models.casos_models import DocumentoInfo
from ..models.macro_models import ReporteValidacion
from ..utils.logger import get_logger

logger = get_logger()

_NOMBRE_SEGURO = re.compile(r"^[\w\-. ]+$", re.UNICODE)

REPORTE_FILENAME = "reporte_validacion.json"


class NombreInvalidoError(ValueError):
    """Se lanza cuando un folio o nombre de archivo no es seguro para el filesystem."""


def _validar_componente(valor: str, etiqueta: str) -> str:
    if not valor or "/" in valor or "\\" in valor or valor in {".", ".."} or not _NOMBRE_SEGURO.match(valor):
        raise NombreInvalidoError(f"{etiqueta} inválido: '{valor}'")
    return valor


def carpeta_caso(folio: str) -> Path:
    _validar_componente(folio, "folio")
    ruta = Path(get_settings().documentos_dir) / folio
    ruta.mkdir(parents=True, exist_ok=True)
    (ruta / "macro").mkdir(exist_ok=True)
    (ruta / "anexos").mkdir(exist_ok=True)
    return ruta


def guardar_macro(folio: str, filename: str, content: bytes, subido_por: Optional[str] = None) -> DocumentoInfo:
    _validar_componente(filename, "nombre de archivo")
    carpeta = carpeta_caso(folio) / "macro"
    ruta = carpeta / filename
    ruta.write_bytes(content)
    logger.info("Macro guardada para folio %s: %s (%d bytes)", folio, filename, len(content))
    return DocumentoInfo(
        nombre=filename,
        tipo="macro",
        tamano_bytes=len(content),
        subido_en=datetime.now(tz=timezone.utc),
        subido_por=subido_por,
    )


def guardar_anexo(folio: str, filename: str, content: bytes, subido_por: Optional[str] = None) -> DocumentoInfo:
    _validar_componente(filename, "nombre de archivo")
    carpeta = carpeta_caso(folio) / "anexos"
    ruta = carpeta / filename
    ruta.write_bytes(content)
    logger.info("Anexo guardado para folio %s: %s (%d bytes)", folio, filename, len(content))
    return DocumentoInfo(
        nombre=filename,
        tipo="anexo",
        tamano_bytes=len(content),
        subido_en=datetime.now(tz=timezone.utc),
        subido_por=subido_por,
    )


def guardar_reporte(folio: str, reporte: ReporteValidacion) -> None:
    carpeta = carpeta_caso(folio)
    ruta = carpeta / REPORTE_FILENAME
    ruta.write_text(reporte.model_dump_json(indent=2), encoding="utf-8")


def leer_reporte(folio: str) -> Optional[ReporteValidacion]:
    carpeta = carpeta_caso(folio)
    ruta = carpeta / REPORTE_FILENAME
    if not ruta.exists():
        return None
    data = json.loads(ruta.read_text(encoding="utf-8"))
    return ReporteValidacion(**data)


def listar_documentos(folio: str) -> list[DocumentoInfo]:
    carpeta = carpeta_caso(folio)
    documentos: list[DocumentoInfo] = []

    for tipo, subcarpeta in (("macro", "macro"), ("anexo", "anexos")):
        directorio = carpeta / subcarpeta
        if not directorio.exists():
            continue
        for archivo in sorted(directorio.iterdir()):
            if archivo.is_file():
                stat = archivo.stat()
                documentos.append(
                    DocumentoInfo(
                        nombre=archivo.name,
                        tipo=tipo,  # type: ignore[arg-type]
                        tamano_bytes=stat.st_size,
                        subido_en=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    )
                )

    reporte_path = carpeta / REPORTE_FILENAME
    if reporte_path.exists():
        stat = reporte_path.stat()
        documentos.append(
            DocumentoInfo(
                nombre=REPORTE_FILENAME,
                tipo="reporte",
                tamano_bytes=stat.st_size,
                subido_en=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            )
        )

    return documentos


def obtener_ruta_documento(folio: str, nombre: str) -> Optional[Path]:
    """Busca un documento por nombre dentro de macro/, anexos/ o el reporte del folio."""
    _validar_componente(nombre, "nombre de archivo")
    carpeta = carpeta_caso(folio)

    candidatos = [
        carpeta / "macro" / nombre,
        carpeta / "anexos" / nombre,
    ]
    if nombre == REPORTE_FILENAME:
        candidatos.append(carpeta / REPORTE_FILENAME)

    for candidato in candidatos:
        if candidato.exists() and candidato.is_file():
            return candidato
    return None


def eliminar_carpeta_caso(folio: str) -> None:
    import shutil

    carpeta = carpeta_caso(folio)
    shutil.rmtree(carpeta, ignore_errors=True)