from __future__ import annotations
import asyncio
import json
import logging
import os
import re
import threading
import time
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from collections import Counter

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter as PromCounter, Histogram, generate_latest
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

CASE = 'Inventario inteligente de sensores'
RECORDS_NAME = 'items'
RELEASE_VERSION = os.getenv("RELEASE_VERSION", '1.0.0')
INCIDENT_MODE = os.getenv("INCIDENT_MODE", "off")
LAB_FAULTS_ENABLED = os.getenv("LAB_FAULTS_ENABLED", "false").lower() == "true"
LAB_KEY = os.getenv("LAB_KEY", "sin-configurar")
DELAY_SECONDS = 650 / 1000.0
BAD_EVERY = 3
ROOT = Path(__file__).resolve().parent.parent
RECORDS = json.loads((ROOT / "data" / "records.json").read_text(encoding="utf-8"))
TRAIN = json.loads((ROOT / "data" / "train.json").read_text(encoding="utf-8"))
vectorizer = CountVectorizer()
X = vectorizer.fit_transform([row["texto"] for row in TRAIN])
model = MultinomialNB().fit(X, [row["categoria"] for row in TRAIN])

REQUESTS = PromCounter("tsi_http_requests_total", "Respuestas HTTP observadas", ["route", "status", "release"])
DURATION = Histogram("tsi_http_request_duration_seconds", "Duracion de solicitudes", ["route", "release"], buckets=(.01,.025,.05,.1,.2,.4,.7,1,2,5))
logger = logging.getLogger("tsi")
logging.basicConfig(level=logging.INFO, format="%(message)s")
_lock = threading.Lock()
_mode = "normal"
_calls = 0

def reset_state():
    global _mode, _calls
    with _lock:
        _mode, _calls = "normal", 0

def read_mode():
    with _lock:
        return _mode

def update_mode(value):
    global _mode
    with _lock:
        _mode = value

def next_call():
    global _calls
    with _lock:
        _calls += 1
        return _calls

app = FastAPI(title=f"TSI - {CASE}", version=RELEASE_VERSION)

@app.middleware("http")
async def observations(request: Request, call_next):
    start = time.perf_counter()
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())[:12]
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(json.dumps({"event":"unexpected_error","request_id":rid,"path":request.url.path,"release":RELEASE_VERSION}))
        response = JSONResponse(status_code=500, content={"detail":"Error interno"})
    elapsed = time.perf_counter() - start
    route = request.url.path
    if route != "/metrics":
        REQUESTS.labels(route=route, status=str(response.status_code), release=RELEASE_VERSION).inc()
        DURATION.labels(route=route, release=RELEASE_VERSION).observe(elapsed)
        logger.info(json.dumps({"event":"http_request","request_id":rid,"route":route,"status":response.status_code,"duration_ms":round(1000*elapsed,2),"version":RELEASE_VERSION}, ensure_ascii=False))
    response.headers["X-Request-ID"] = rid
    return response

@app.get("/health")
def health():
    return {"status":"ok","version":RELEASE_VERSION,"incident_mode":INCIDENT_MODE,"case":CASE}

@app.get("/health/live")
def live():
    return {"status":"alive","service":CASE}

@app.get("/health/ready")
def ready():
    if read_mode() == "unavailable":
        raise HTTPException(status_code=503, detail="Dependencia simulada no disponible")
    return {"status":"ready","dependency":read_mode()}

async def dependency():
    mode = read_mode()
    if mode == "unavailable":
        raise HTTPException(status_code=503, detail="Dependencia simulada no disponible")
    if mode == "slow":
        await asyncio.sleep(0.8)
    if INCIDENT_MODE == "degraded":
        await asyncio.sleep(DELAY_SECONDS)
        if next_call() % BAD_EVERY == 0:
            raise HTTPException(status_code=503, detail="Fallo simulado en release degradada")

@app.get("/api/items")
async def list_records():
    await dependency()
    return {"items":RECORDS,"total":len(RECORDS),"version":RELEASE_VERSION}

@app.get("/api/items/{record_id}")
async def get_record(record_id: int):
    await dependency()
    found = next((r for r in RECORDS if r["id"] == record_id), None)
    if found is None:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return found

class PredictInput(BaseModel):
    texto: str = Field(min_length=1, max_length=400)

@app.post("/predict")
async def predict(payload: PredictInput):
    await dependency()
    features = vectorizer.transform([payload.texto])
    label = str(model.predict(features)[0])
    # score_no_calibrado: confianza heuristica del modelo didactico, no garantia de probabilidad.
    score = float(max(model.predict_proba(features)[0]))
    return {"categoria": label, "score_no_calibrado":round(score,4), "version":RELEASE_VERSION}

class ModeChange(BaseModel):
    mode: str

@app.post("/admin/mode")
def admin_mode(payload: ModeChange, x_lab_key: str | None = Header(default=None)):
    if not LAB_FAULTS_ENABLED:
        raise HTTPException(status_code=403, detail="Simulacion deshabilitada")
    if x_lab_key != LAB_KEY:
        raise HTTPException(status_code=403, detail="Clave de laboratorio incorrecta")
    if payload.mode not in {"normal", "slow", "unavailable"}:
        raise HTTPException(status_code=422, detail="Modo no soportado")
    update_mode(payload.mode)
    return {"mode":read_mode(),"version":RELEASE_VERSION}

@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
