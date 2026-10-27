# EpiSentinel AI

Detección temprana de brotes epidemiológicos en zonas de difícil acceso.
Proyecto de aula — Inteligencia Artificial, 7.º semestre, Ingeniería de
Sistemas, Universidad Popular del Cesar. Equipo DKK (Diland López, Kevin
Noriega, Kerin Maestre).

## Estado

Esqueleto inicial del repositorio (tarea A1) + generador sintético del panel
(tarea A2). **Todavía no contiene datos reales, ni modelos, ni resultados.**
Ver `docs/ESTADO_DEL_PROYECTO.md` para el estado actualizado.

## Estructura

```
configs/            Configuración versionable (partición, series seleccionadas)
data/                raw/interim/processed/external — NO se versiona el contenido
docs/                ESTADO_DEL_PROYECTO.md, DECISIONES_TECNICAS.md, BITACORA_EXPERIMENTOS.md
notebooks/           Notebooks de EDA y demo
reports/             Reportes generados (JSON/MD), no editados a mano
experiments/runs/    Una carpeta por ejecución: config.json, forecasts.parquet, metrics.json
src/episentinel/     Código fuente instalable (pip install -e .)
  data/              Carga, limpieza, panel, generador sintético
  baselines/         EARS C2, canal endémico, ingenua estacional
  evaluation/        Métricas de pronóstico y de detección
  models/            SARIMA, Prophet
  detection/         Reglas de alerta sobre los pronósticos
tests/               Pruebas unitarias (pytest)
app/                 Demo (Fase 3, no es prioridad de la Fase 2)
```

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

## Contratos entre pistas

Ver `PAQUETE_EQUIPO_EPISENTINEL.md`, sección 2.2, para el formato exacto del
panel, la partición, las series seleccionadas y el formato de pronósticos.
