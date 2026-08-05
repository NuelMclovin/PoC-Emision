from __future__ import annotations

import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Entorno
    app_environment: str = "development"
    logging_level: str = "INFO"

    # CORS — acepta lista JSON o string CSV: "http://a,http://b"
    allowed_origins: list[str] = [
        "http://localhost:4200",
        "http://localhost:4201",
    ]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _parse_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v  # type: ignore[return-value]

    # Almacenamiento
    upload_dir: str = "./tmp/uploads"

    # Auth mock
    auth_mock: bool = True
    secret_key: str = "cambia_esto_antes_de_produccion"

    # Azure Document Intelligence (OCR)
    azure_endpoint: str | None = None
    azure_key: str | None = None
    azure_region: str | None = None

    # Azure Service Principal
    azure_client_id: str | None = None
    azure_client_secret: str | None = None
    azure_tenant_id: str | None = None

    def ensure_upload_dir(self) -> None:
        os.makedirs(self.upload_dir, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
