"""
Router CRUD de casos/folios — es el punto de comunicación entre el frontend
de bróker (conducto) y el frontend de suscriptor interno.

Flujo:
  1. El bróker valida su macro con /api/v1/validacion/macro (sin persistir).
  2. Cuando está conforme, la envía a suscripción con POST /api/v1/casos:
     esto vuelve a leer/validar el archivo, guarda el reporte y la macro en
     el volumen de documentos del folio, y crea el registro en el CSV.
  3. El suscriptor consulta la bandeja con GET /api/v1/casos, abre el detalle
     con GET /api/v1/casos/{folio} y lo resuelve con PATCH /api/v1/casos/{folio}
     (tomar el caso, aprobar, rechazar u observar con comentario).
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from ..models.casos_models import CasoActualizar, CasoDetalle, CasoResumen, DocumentoInfo, EstadoCaso
from ..services import casos_store, documentos_store
from ..services.macro_reader import leer_macro
from ..services.validator import validar_macro
from ..utils.logger import get_logger
from .auth_router import requerir_suscriptor, usuario_actual

logger = get_logger()

router = APIRouter(prefix="/api/v1/casos", tags=["casos"])

EXTENSIONES_PERMITIDAS = {".xlsx", ".xls", ".xlsm", ".csv"}
MAX_SIZE_MB = 100


def _detalle_de(caso: CasoResumen) -> CasoDetalle:
    return CasoDetalle(
        **caso.model_dump(),
        reporte=documentos_store.leer_reporte(caso.folio),
        documentos=documentos_store.listar_documentos(caso.folio),
    )


@router.post(
    "",
    response_model=CasoDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Crea un caso/folio a partir de una macro (envío del bróker a suscripción)",
)
async def crear_caso(
    archivo: UploadFile = File(..., description="Macro de emisión"),
    empresa: str = Form(..., description="Contratante / razón social"),
    tipo_accion: Literal["nueva", "renovacion"] = Form("nueva"),
    tipo_producto: Literal["GMM", "AP"] = Form("GMM"),
    usuario: dict = Depends(usuario_actual),
) -> CasoDetalle:
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

    reporte = validar_macro(filename, df, tipo_accion=tipo_accion, tipo_producto=tipo_producto, fila_offset=offset)

    caso = casos_store.crear_caso(
        empresa=empresa,
        tipo_accion=tipo_accion,
        tipo_producto=tipo_producto,
        creado_por=usuario["username"],
        nombre_archivo_macro=filename,
        total_registros=reporte.resumen.total_registros,
        total_titulares=reporte.resumen.total_titulares,
        total_dependientes=reporte.resumen.total_dependientes,
        total_errores=reporte.resumen.total_errores,
        total_advertencias=reporte.resumen.total_advertencias,
        es_valida=reporte.resumen.es_valida,
    )

    documentos_store.guardar_macro(caso.folio, filename, content, subido_por=usuario["username"])
    documentos_store.guardar_reporte(caso.folio, reporte)

    logger.info("Caso %s enviado a suscripción por %s", caso.folio, usuario["username"])
    return _detalle_de(caso)


@router.get("", response_model=list[CasoResumen], summary="Lista casos con filtros opcionales")
async def listar_casos(
    estado: Optional[EstadoCaso] = Query(None),
    tipo_accion: Optional[Literal["nueva", "renovacion"]] = Query(None),
    tipo_producto: Optional[Literal["GMM", "AP"]] = Query(None),
    creado_por: Optional[str] = Query(None, description="Filtra por bróker que creó el caso"),
    asignado_a: Optional[str] = Query(None, description="Filtra por suscriptor asignado"),
    usuario: dict = Depends(usuario_actual),
) -> list[CasoResumen]:
    return casos_store.listar_casos(
        estado=estado.value if estado else None,
        tipo_accion=tipo_accion,
        tipo_producto=tipo_producto,
        creado_por=creado_por,
        asignado_a=asignado_a,
    )


@router.get("/{folio}", response_model=CasoDetalle, summary="Detalle de un caso, incluyendo reporte y documentos")
async def obtener_caso(folio: str, usuario: dict = Depends(usuario_actual)) -> CasoDetalle:
    caso = casos_store.obtener_caso(folio)
    if not caso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folio '{folio}' no encontrado.")
    return _detalle_de(caso)


@router.patch("/{folio}", response_model=CasoDetalle, summary="Actualiza estado/asignación/comentario (suscriptor)")
async def actualizar_caso(
    folio: str,
    cambios: CasoActualizar,
    usuario: dict = Depends(requerir_suscriptor),
) -> CasoDetalle:
    caso_existente = casos_store.obtener_caso(folio)
    if not caso_existente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folio '{folio}' no encontrado.")

    datos = cambios.model_dump(exclude_unset=True)
    if "estado" in datos and datos["estado"] is not None:
        datos["estado"] = EstadoCaso(datos["estado"]).value

    # Si el suscriptor toma el caso sin especificar asignado_a, se autoasigna.
    if "estado" in datos and datos["estado"] == EstadoCaso.EN_REVISION.value and "asignado_a" not in datos:
        datos["asignado_a"] = usuario["username"]

    caso = casos_store.actualizar_caso(folio, datos)
    if not caso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folio '{folio}' no encontrado.")

    logger.info("Caso %s resuelto por %s -> %s", folio, usuario["username"], datos)
    return _detalle_de(caso)


@router.delete("/{folio}", status_code=status.HTTP_204_NO_CONTENT, summary="Elimina un caso (limpieza de PoC)")
async def eliminar_caso(folio: str, usuario: dict = Depends(requerir_suscriptor)):
    # Sin anotación de retorno a propósito: con `-> None` FastAPI infiere un
    # response_model de tipo NoneType (no lo trata como "sin modelo"), y para
    # un status 204 eso hace fallar el arranque con
    # "AssertionError: Status code 204 must not have a response body".
    if not casos_store.eliminar_caso(folio):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folio '{folio}' no encontrado.")
    documentos_store.eliminar_carpeta_caso(folio)


@router.get("/{folio}/documentos", response_model=list[DocumentoInfo], summary="Lista documentos del folio")
async def listar_documentos(folio: str, usuario: dict = Depends(usuario_actual)) -> list[DocumentoInfo]:
    if not casos_store.obtener_caso(folio):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folio '{folio}' no encontrado.")
    return documentos_store.listar_documentos(folio)


@router.post(
    "/{folio}/documentos",
    response_model=DocumentoInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Sube un documento adicional (anexo) al folio",
)
async def subir_documento(
    folio: str,
    archivo: UploadFile = File(...),
    usuario: dict = Depends(usuario_actual),
) -> DocumentoInfo:
    if not casos_store.obtener_caso(folio):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folio '{folio}' no encontrado.")

    filename = archivo.filename or "documento"
    content = await archivo.read()
    if len(content) / (1024 * 1024) > MAX_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite de {MAX_SIZE_MB} MB.",
        )
    return documentos_store.guardar_anexo(folio, filename, content, subido_por=usuario["username"])


@router.get("/{folio}/documentos/{nombre}", summary="Descarga un documento del folio")
async def descargar_documento(folio: str, nombre: str, usuario: dict = Depends(usuario_actual)) -> FileResponse:
    if not casos_store.obtener_caso(folio):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folio '{folio}' no encontrado.")

    ruta = documentos_store.obtener_ruta_documento(folio, nombre)
    if not ruta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Documento '{nombre}' no encontrado.")
    return FileResponse(path=str(ruta), filename=ruta.name)