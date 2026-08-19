from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import auth_router, casos_router, validacion_router
from .utils.logger import get_logger

logger = get_logger()
settings = get_settings()


def create_app() -> FastAPI:
    settings.ensure_upload_dir()
    settings.ensure_data_dirs()

    app = FastAPI(
        title="Portal de Validación de Emisión — AXA PoC",
        version="0.1.0",
        description=(
            "API para validación de macros de emisión de pólizas colectivas GMM/AP. "
            "Permite cargar una macro Excel y obtener un reporte detallado de errores "
            "conforme a las reglas de negocio de distribución."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router.router)
    app.include_router(validacion_router.router)
    app.include_router(casos_router.router)

    @app.get("/health", tags=["sistema"])
    async def health():
        return {"status": "ok", "environment": settings.app_environment}

    logger.info("Aplicación inicializada — entorno: %s", settings.app_environment)
    return app


app = create_app()