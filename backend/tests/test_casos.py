"""
Pruebas de integración del CRUD de casos/folios (backend/app/routers/casos_router.py)
y del storage local (CSV + volumen de documentos por folio).

Cada test recibe un `client` con almacenamiento aislado en un directorio
temporal, para no tocar backend/data ni interferir entre pruebas.
"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

CSV_VALIDO = (
    "NOMBRE,APELLIDO_PATERNO,APELLIDO_MATERNO,FECHA_NACIMIENTO,FECHA_ANTIGUEDAD,PARENTESCO,CERTIFICADO\n"
    "Juan,Garcia,Lopez,01/01/1985,01/01/2010,Titular,CERT-001\n"
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("data_dir", str(tmp_path / "data"))
    monkeypatch.setenv("upload_dir", str(tmp_path / "uploads"))

    from app import config as config_module

    config_module.get_settings.cache_clear()

    from app.main import app

    with TestClient(app) as c:
        yield c

    config_module.get_settings.cache_clear()


def _token(client: TestClient, username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _crear_caso(client: TestClient, token: str, empresa: str = "Grupo Industrial Alfa") -> dict:
    resp = client.post(
        "/api/v1/casos",
        headers=_auth(token),
        data={"empresa": empresa, "tipo_accion": "nueva", "tipo_producto": "GMM"},
        files={"archivo": ("censo.csv", io.BytesIO(CSV_VALIDO.encode("utf-8")), "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_login_incluye_rol(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={"username": "broker", "password": "broker1234"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["rol"] == "broker"

    resp2 = client.post("/api/v1/auth/login", json={"username": "suscriptor", "password": "suscriptor1234"})
    assert resp2.json()["rol"] == "suscriptor"


def test_crear_caso_genera_folio_y_persiste_documentos(client: TestClient):
    token = _token(client, "broker", "broker1234")
    caso = _crear_caso(client, token)

    assert caso["folio"].startswith("FOL-")
    assert caso["estado"] == "Pendiente"
    assert caso["creado_por"] == "broker"
    assert caso["empresa"] == "Grupo Industrial Alfa"
    assert caso["total_registros"] == 1
    assert caso["reporte"] is not None
    nombres_documentos = {d["nombre"] for d in caso["documentos"]}
    assert "censo.csv" in nombres_documentos
    assert "reporte_validacion.json" in nombres_documentos


def test_listar_y_obtener_caso(client: TestClient):
    token = _token(client, "broker", "broker1234")
    creado = _crear_caso(client, token)

    resp = client.get("/api/v1/casos", headers=_auth(token))
    assert resp.status_code == 200
    folios = [c["folio"] for c in resp.json()]
    assert creado["folio"] in folios

    resp_detalle = client.get(f"/api/v1/casos/{creado['folio']}", headers=_auth(token))
    assert resp_detalle.status_code == 200
    assert resp_detalle.json()["folio"] == creado["folio"]


def test_broker_no_puede_resolver_caso(client: TestClient):
    token_broker = _token(client, "broker", "broker1234")
    caso = _crear_caso(client, token_broker)

    resp = client.patch(
        f"/api/v1/casos/{caso['folio']}",
        headers=_auth(token_broker),
        json={"estado": "Aprobado"},
    )
    assert resp.status_code == 403


def test_suscriptor_toma_y_aprueba_caso(client: TestClient):
    token_broker = _token(client, "broker", "broker1234")
    token_suscriptor = _token(client, "suscriptor", "suscriptor1234")
    caso = _crear_caso(client, token_broker)

    tomar = client.patch(
        f"/api/v1/casos/{caso['folio']}",
        headers=_auth(token_suscriptor),
        json={"estado": "En revisión"},
    )
    assert tomar.status_code == 200
    assert tomar.json()["asignado_a"] == "suscriptor"
    assert tomar.json()["estado"] == "En revisión"

    resolver = client.patch(
        f"/api/v1/casos/{caso['folio']}",
        headers=_auth(token_suscriptor),
        json={"estado": "Aprobado", "comentario_suscriptor": "Todo en orden."},
    )
    assert resolver.status_code == 200
    body = resolver.json()
    assert body["estado"] == "Aprobado"
    assert body["comentario_suscriptor"] == "Todo en orden."


def test_descarga_documento(client: TestClient):
    token = _token(client, "broker", "broker1234")
    caso = _crear_caso(client, token)

    resp = client.get(f"/api/v1/casos/{caso['folio']}/documentos/censo.csv", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.content.decode("utf-8") == CSV_VALIDO


def test_caso_inexistente_404(client: TestClient):
    token = _token(client, "broker", "broker1234")
    resp = client.get("/api/v1/casos/FOL-2099-9999", headers=_auth(token))
    assert resp.status_code == 404