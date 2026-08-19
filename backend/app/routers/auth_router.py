"""
Router de autenticación — modo mock para la PoC.

En la PoC, el login es simulado: usuarios/contraseñas predefinidos retornan
un token JWT firmado localmente que incluye el rol (broker | suscriptor).
Ambos frontends (conducto/bróker y suscriptor interno) usan este mismo
backend, por lo que el rol es lo que determina qué puede hacer cada usuario
sobre el CRUD de casos (ver routers/casos_router.py).

Para integrar One Account en producción, solo hay que reemplazar la lógica
de este router.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError, jwt

from ..config import get_settings
from ..models.macro_models import LoginRequest, TokenResponse
from ..utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/v1/auth", tags=["autenticación"])

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8

# ─── Usuarios mock para la PoC ────────────────────────────────────────────────
# En producción esto se reemplaza por la integración con One Account / LDAP.
# rol determina el frontend/permisos: "broker" (conducto) o "suscriptor" (interno).
USUARIOS_MOCK: dict[str, dict] = {
    "demo": {"password": "demo1234", "rol": "broker", "nombre": "Bróker Demo"},
    "distribucion": {"password": "axa2024", "rol": "broker", "nombre": "Distribución"},
    "broker": {"password": "broker1234", "rol": "broker", "nombre": "Bróker AXA"},
    "suscriptor": {"password": "suscriptor1234", "rol": "suscriptor", "nombre": "Suscriptor AXA"},
    "admin": {"password": "admin1234", "rol": "suscriptor", "nombre": "Administrador"},
}


def _crear_token(username: str, rol: str) -> str:
    settings = get_settings()
    expire = datetime.now(tz=timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": username,
        "rol": rol,
        "exp": expire,
        "iat": datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decodificar_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
        ) from exc
    return payload


def usuario_actual(authorization: Optional[str] = Header(None)) -> dict:
    """Dependencia de FastAPI: extrae {username, rol} del Bearer token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta encabezado Authorization Bearer.",
        )
    token = authorization.split(" ", 1)[1].strip()
    payload = decodificar_token(token)
    return {"username": payload.get("sub"), "rol": payload.get("rol", "broker")}


def requerir_suscriptor(usuario: dict = Depends(usuario_actual)) -> dict:
    """Dependencia de FastAPI: exige que el usuario autenticado tenga rol 'suscriptor'."""
    if usuario.get("rol") != "suscriptor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere rol de suscriptor.",
        )
    return usuario


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login de usuario (mock PoC)",
)
async def login(body: LoginRequest) -> TokenResponse:
    settings = get_settings()

    # Modo mock: valida contra diccionario local
    if settings.auth_mock:
        usuario = USUARIOS_MOCK.get(body.username)
        if not usuario or body.password != usuario["password"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas.",
            )
        token = _crear_token(body.username, usuario["rol"])
        logger.info("Login mock exitoso: usuario '%s' (rol=%s)", body.username, usuario["rol"])
        return TokenResponse(
            access_token=token,
            username=body.username,
            rol=usuario["rol"],
            nombre=usuario.get("nombre", body.username),
        )

    # TODO: integrar One Account aquí para producción
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Integración con One Account pendiente.",
    )


@router.post("/logout", summary="Cierre de sesión")
async def logout() -> dict:
    # Con JWT sin estado, el logout es responsabilidad del cliente (borrar token).
    return {"message": "Sesión cerrada correctamente."}


@router.get("/me", summary="Información del usuario autenticado")
async def me(authorization: Optional[str] = Header(None)) -> dict:
    usuario = usuario_actual(authorization)
    datos = USUARIOS_MOCK.get(usuario["username"], {})
    return {
        "username": usuario["username"],
        "rol": usuario["rol"],
        "nombre": datos.get("nombre", usuario["username"]),
    }