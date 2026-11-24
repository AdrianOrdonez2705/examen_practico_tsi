import os
os.environ.setdefault("LAB_FAULTS_ENABLED", "true")
os.environ.setdefault("LAB_KEY", "demo-tsi-a-no-produccion")
from fastapi.testclient import TestClient
from app import main
import pytest

@pytest.fixture(autouse=True)
def clean_state():
    main.reset_state()
    yield
    main.reset_state()

client = TestClient(main.app)

def test_liveness_y_readiness():
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200

def test_listado_sintetico():
    r = client.get("/api/items")
    assert r.status_code == 200 and r.json()["total"] == 3

def test_recurso_inexistente_debe_dar_404():
    assert client.get("/api/items/99999").status_code == 404

def test_predict_del_modelo_didactico():
    r = client.post("/predict", json={"texto":'sensor no responde urgente'})
    assert r.status_code == 200
    data = r.json()
    assert data["categoria"] in ("critico", "normal")
    assert "score_no_calibrado" in data

def test_admin_nega_clave_incorrecta():
    r = client.post("/admin/mode", headers={"X-Lab-Key":"clave-invalida"}, json={"mode":"slow"})
    assert r.status_code == 403

def test_incidencia_y_recuperacion_de_dependencia():
    key = {"X-Lab-Key":'demo-tsi-a-no-produccion'}
    assert client.post("/admin/mode",headers=key,json={"mode":"unavailable"}).status_code == 200
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 503
    assert client.get("/api/items").status_code == 503
    assert client.post("/admin/mode",headers=key,json={"mode":"normal"}).status_code == 200
    assert client.get("/health/ready").status_code == 200
