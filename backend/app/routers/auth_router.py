"""
Router de autenticación — modo mock para la PoC.

En la PoC, el login es simulado: cualquier usuario/contraseña válidos
retornan un token JWT firmado localmente. Para integrar One Account
en producción, solo hay que reemplazar la lógica de este router.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from jose import jwt

from ..config import get_settings
from ..models.macro_models import LoginRequest, TokenResponse
from ..utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/v1/auth", tags=["autenticación"])

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8

# ─── Usuarios mock para la PoC ────────────────────────────────────────────────
# En producción esto se reemplaza por la integración con One Account / LDAP.
USUARIOS_MOCK: dict[str, str] = {
    "demo": "demo1234",
    "distribucion": "axa2024",
    "admin": "admin1234",
}


def _crear_token(username: str) -> str:
    settings = get_settings()
    expire = datetime.now(tz=timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login de usuario (mock PoC)",
)
async def login(body: LoginRequest) -> TokenResponse:
    settings = get_settings()

    # Modo mock: valida contra diccionario local
    if settings.auth_mock:
        password_esperado = USUARIOS_MOCK.get(body.username)
        if not password_esperado or body.password != password_esperado:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas.",
            )
        token = _crear_token(body.username)
        logger.info("Login mock exitoso: usuario '%s'", body.username)
        return TokenResponse(access_token=token, username=body.username)

    # TODO: integrar One Account aquí para producción
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Integración con One Account pendiente.",
    )


@router.post("/logout", summary="Cierre de sesión")
async def logout() -> dict:
    # Con JWT sin estado, el logout es responsabilidad del cliente (borrar token).
    return {"message": "Sesión cerrada correctamente."}
