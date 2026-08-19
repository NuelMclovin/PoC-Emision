from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    # `NoDecode` es necesario porque pydantic-settings, para campos con tipos
    # "complejos" (como list[str]), intenta hacer json.loads() del valor del
    # env var ANTES de pasar por los validators de Pydantic. Como acá el
    # formato esperado es CSV (no JSON), ese json.loads() fallaba y tronaba
    # el arranque con "SettingsError: error parsing value for field
    # 'allowed_origins'" — el validator de abajo nunca llegaba a ejecutarse.
    allowed_origins: Annotated[list[str], NoDecode] = [
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

    # Almacenamiento local de casos/folios (PoC sin base de datos):
    # - data_dir/casos.csv          -> "tabla" de transacciones/consultas de folios.
    # - data_dir/documentos/<folio> -> volumen de archivos por caso (macro, reporte, anexos).
    data_dir: str = "./data"
    casos_csv_filename: str = "casos.csv"
    documentos_subdir: str = "documentos"

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

    @property
    def casos_csv_path(self) -> str:
        return os.path.join(self.data_dir, self.casos_csv_filename)

    @property
    def documentos_dir(self) -> str:
        return os.path.join(self.data_dir, self.documentos_subdir)

    def ensure_data_dirs(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.documentos_dir, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()