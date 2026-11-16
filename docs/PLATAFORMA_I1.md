# Plataforma I1 — integración de ambientes

## Arranque

Desde `C:\Proyecto IA\episentinel-ai`:

```powershell
.\.venv\Scripts\python.exe -B -m streamlit run app/platform_app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true --browser.gatherUsageStats false
```

Instalación nueva: `pip install -e ".[dev,app]"`.

## Arquitectura y alcance

- Observatorio Epidemiológico: B08 conserva Datos → Territorio → Análisis, estado e invalidación. La navegación interna B08 continúa disponible.
- Laboratorio de Machine Learning: cinco vistas históricas extraídas a `app/historical_app.py`; navegación secundaria superior. `app/streamlit_app.py` sigue disponible como entrada histórica independiente.
- Evidencia y metodología: ejecución vigente de B08, comparación histórica independiente y documentos descargables.
- `app/analysis_app.py` conserva su entrada independiente. `main(embedded=True)` permite integrarla sin repetir configuración de página o cabecera.
- `app/analysis_presenter.py` no cambia. La evidencia compartida comprueba vigencia contra los perfiles antes de mostrar el resultado.

Pronósticos y señales históricos requieren pulsar sus botones de cálculo. Navegar, seleccionar un método o cambiar ambiente no entrena. Los resultados calculados se conservan en claves de sesión `epi_lab_*`, separadas de `epi_work`. Solo se muestran si coincide la identidad de artefactos/territorio/configuración. Los selectores históricos pueden volver a sus valores iniciales al salir de una vista; esto no borra la carga B08 ni calcula de nuevo.

La extracción conserva gráficos, módulos científicos y reglas existentes. No genera nuevos experimentos científicos ni completa las doce fases.

## Dependencias locales y ausencia de artefactos

Para Panorama, Territorio, Pronósticos y Señales se necesita `data/processed/panel_casos.parquet`. El catálogo `data/processed/municipios.csv` es opcional (sin él se usan códigos); `configs/split.json` y los reportes mantienen las alternativas heredadas.

La comparación se lee de `reports/comparacion_fase2.csv`, incluso si falta el panel. Si falta el CSV, se informa sin inventar resultados. Las otras secciones y documentos permanecen accesibles. Las salidas ignoradas y originales no se incorporan a Git. No se reconstruye ni escribe ningún panel/reporte desde la navegación.

Los datos de demostración B08 requieren `data/processed/b08_demo.csv` y su manifiesto local; ver `DEMO_B08.md`. El perfil `configs/ui_period_grids.json` declara tres periodos y calendario no verificado; no permite analizar arbitrariamente cualquier ventana ni habilita modelos.

## Reglas heredadas y servicios

El histórico suma 210+220, completa ausencias con cero y pliega S53 a S52 sobre una malla técnica de 52 semanas. La evaluación nacional incluye Exterior y el Panorama lo excluye. La selección histórica de municipios usa totales de todo el periodo. La comparación es preliminar; no demuestra superioridad de SARIMA ni generalización amplia.

B03/B04/B05/B06/B07 permanecen intactos. B06-I1 acepta `pd.Series` con fechas cada siete días, corte inclusivo y dos baselines (`ultimo_valor`, `ingenua_estacional`), sin intervalos ni SARIMA. B03 devuelve periodos explícitos sin fechas: no se añade un puente ficticio. B07 acepta `SeriesBundle` y distingue `signal`, `no_signal`, `not_evaluable`; EARS tiene requisitos de calendario/cobertura y canal/SARIMA un paso permanecen pendientes. El Observatorio no llama B06/B07. Las señales históricas no se presentan como B07 ni como brotes validados.

## Protección Git

Respaldo B08: commit `5c801a8` en `feat/b08-streamlit-csv`, diez archivos explícitos, sin datos o derivados ignorados. Rama `feat/platform-i1` creada desde `origin/main` (`8fe8e93`); el respaldo se incorporó con cherry-pick `8afc916`, sin conflictos. Se conservaron las exportaciones remotas de `services/__init__.py`. No se actualizó main, no se realizó merge ni se publicó.

## Verificación

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_platform_app.py tests/test_analysis_app.py tests/test_analysis_presenter.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
git diff --check
```

Los tests de plataforma generan artefactos sintéticos en directorios temporales; no alteran los archivos históricos. Prueban navegación, ausencia de artefactos, cinco vistas, preservación B08, rechazos y ejecución explícita de pronósticos. No validan eficacia epidemiológica ni sustituyen revisión visual real.

## Plataforma I2

Organizar las doce fases y su matriz de evidencia, registrar ejecuciones reproducibles, corregir selección temporal y conciliar universos mediante nuevas versiones de resultados. Resolver calendario/cobertura antes de conectar B06/B07 al Observatorio. No sobrescribir resultados históricos para aparentar estas mejoras.

## Evidencia ejecutada — 16 de noviembre de 2026

- Base conciliada antes de integrar la interfaz: 430 pruebas aprobadas.
- Plataforma + B08: 32 pruebas específicas aprobadas.
- Suite completa con Plataforma I1: 441 aprobadas, ninguna omitida.
- Servidor local iniciado en 127.0.0.1:8503, conservando la demo previa de 8502.
- Navegador real: carga de b08_demo.csv; 76001/220; perfil de tres periodos; resultado 2/3. Se recorrieron las cinco vistas históricas, se calcularon SARIMA y señales por botón explícito y se volvió a B08 conservando su resultado. La sección compartida mostró el archivo y su huella vigentes.
- Las pruebas automatizadas verificaron ausencia del panel, catálogo y comparación usando directorios temporales, sin retirar los artefactos reales.
- SHA-256 antes/después idénticos para los 13 archivos de data/raw, data/processed y reports, incluidos sus marcadores.
- Sin cambios en los módulos B03/B04/B05/B06/B07, configuraciones o scripts científicos.
- Pendiente fuera de I1: accesibilidad exhaustiva, despliegue público y conexiones analíticas condicionadas por calendario/cobertura.

La publicación de Plataforma I1 se prepara desde feat/platform-i1 contra main, con los archivos B08 e I1 seleccionados explícitamente y Refs #8. Los commits de respaldo e incorporación B08 se describen arriba. El merge y el cierre de Issues quedan fuera de esta entrega.
