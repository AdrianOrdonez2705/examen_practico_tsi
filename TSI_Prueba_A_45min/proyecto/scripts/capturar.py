"""Captura verificable del estado de la API local para la prueba de 45 minutos."""
from __future__ import annotations
import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--etapa', choices=['base', 'incidente', 'recuperacion'], required=True)
parser.add_argument('--base', default='http://127.0.0.1:18000')
args = parser.parse_args()


def solicitar(path: str):
    start = time.perf_counter()
    url = args.base + path
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode('utf-8', 'replace')
            return {'http': response.status, 'ms': round((time.perf_counter() - start) * 1000, 1), 'contenido': body[:300]}
    except urllib.error.HTTPError as err:
        body = err.read().decode('utf-8', 'replace')
        return {'http': err.code, 'ms': round((time.perf_counter() - start) * 1000, 1), 'contenido': body[:300]}
    except Exception as exc:
        return {'http': None, 'ms': round((time.perf_counter() - start) * 1000, 1), 'error': str(exc)}

paths = ['/health', '/health/live', '/health/ready', '/api/items', '/api/items/99999']
results = {path: solicitar(path) for path in paths}
metrics_response = solicitar('/metrics')
text = metrics_response.get('contenido', '')
output = {'etapa': args.etapa, 'capturado_utc': datetime.now(timezone.utc).isoformat(), 'base_local': args.base, 'endpoints': results, 'metricas': {'http': metrics_response.get('http'), 'muestra': text[:140]}}
out = Path(__file__).resolve().parent.parent / 'evidencias' / f'{args.etapa}.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')
print('Etapa:', args.etapa)
for path, value in results.items():
    print(f'{path:20} HTTP={value["http"]} {value["ms"]} ms')
print('Métricas /metrics:', metrics_response.get('http'))
print('Evidencia:', out)
if any(value['http'] is None for value in results.values()):
    raise SystemExit('ERROR: uno o más endpoints inaccesibles. Confirma que uvicorn esté ejecutándose.')
