# TSI - EC3 - Práctica A | Inventario de sensores

Caso: API local de inventario de sensores basada en FastAPI.

**Leer primero `GUIA_ESTUDIANTE_EVIDENCIAS_Y_TIPS.docx` (ubicada fuera de esta carpeta).**

## Preparación del entorno
- Windows 10/11, VS Code, Python >= 3.12, `uv` instalados y probados.
- Desde la carpeta `proyecto`, ejecutar `uv sync --extra lab` antes de la práctica.
- No se requiere Docker, Prometheus, Grafana ni Locust para esta modalidad corta.

## Ejecución
En la carpeta `proyecto`, sigue la consigna general de la guía y utiliza estos comandos de referencia.

Terminal de pruebas:
```powershell
uv run pytest -q
```

Terminal para ejecutar el servicio:
```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 18000
```

Desde otra terminal:
```powershell
uv run python scripts/capturar.py --etapa base
uv run python scripts/fault.py unavailable
uv run python scripts/capturar.py --etapa incidente
uv run python scripts/fault.py normal
uv run python scripts/capturar.py --etapa recuperacion
```

Evidencias: `evidencias/base.json`, `evidencias/incidente.json`, `evidencias/recuperacion.json`, `evidencias/RESPUESTAS.md` y las cinco capturas PNG descritas en la guía (`evidencias/capturas/`). No envíes claves reales, información personal ni archivos `.venv`.

## Notas
- Es normal que exista un test fallido al comenzar; se espera diagnóstico y corrección del estudiante.
- No sobrescribas las capturas después de generarlas.
- Las métricas y estados se obtienen desde el servicio **local**; no se necesita nube.
- El control de modo es didáctico y no debe exponerse en redes públicas.
