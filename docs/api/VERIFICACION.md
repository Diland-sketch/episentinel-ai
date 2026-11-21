# Verificación REST — 21 de noviembre de 2026

Base: `origin/main` actualizado, commit `b0ded49`. Rama `feat/v2-api`. Entorno Windows, Python 3.13.4; versiones reproducibles en `requirements-api-repro.txt`.

Resultados ejecutados localmente:

- Regresión completa: **837 passed, 4 skipped**, 119.83 s.
- Tras el ajuste final del manejo HTTP/CORS de errores: **23 passed** en `tests/test_api.py`, 30.72 s. Incluye los cuatro ensayos reales de Cali nuevamente.
- Las cuatro omisiones de la regresión completa corresponden a datos de ingesta/demo locales no presentes en este checkout; las pruebas reales de Cali **sí se ejecutaron**.
- Advertencia del cliente de pruebas: Starlette anuncia sustitución futura de httpx por httpx2. No se alteran resultados ni se silencia la advertencia.
- Servidor Uvicorn real enlazado a 127.0.0.1:8000: health=200, OpenAPI=200, experiments=200, benchmarks=200. Contrato publicado OpenAPI 3.1.0; cuatro experimentos históricos y benchmark identificado como sintético.

## Integridad científica

Se ejecutó Cali (76001), corte inclusivo 779 y horizonte ocho por REST, con `ultimo_valor`, `ingenua_estacional`, `sarima_sin_estacional` y `sarima_estacional`. Se contrastaron predicciones y MAE/RMSE/MASE con las evidencias IA-I1; en SARIMA también bandas y convergencia. Tolerancia relativa 1e-8, sin modificar B06 ni relajar comparaciones.

Objetivos observados comprobados: 57, 66, 57, 48, 68, 51, 50, 58. Fechas técnicas originales; no son calendario epidemiológico oficial. Se preserva la identidad SHA-256 de fuente y configuración. Ningún ensayo certifica superioridad poblacional, calibración epidemiológica o independencia de prueba.

La primera prueba detectó una diferencia SARIMA estacional con NumPy/pandas 2.3.3. Se reprodujo usando las versiones de la evidencia IA-I1, NumPy 2.5.4 y pandas 3.1.0, manteniendo statsmodels 0.15.0 y sin cambiar algoritmos. La regresión estricta pasó después.

Panel original utilizado, copiado a una ruta nueva ignorada por Git desde el respaldo local disponible, sin modificar el origen:

`data/processed/panel_casos.parquet`

SHA-256: `41e592e9fb548085377a1c6d7ed7de026496d8c530583ba5aaf6c80e2fee5989`.

Los tests comparan hashes del panel y de todas las evidencias de experimentos/benchmarks antes y después de cada pronóstico real. No se escribieron modelos, resultados REST, datasets de usuario ni archivos históricos en disco. Los motores científicos y la aplicación Streamlit permanecen sin cambios.

## Contratos y aislamiento

Probados: CSV y manual por B04, construcción B05, rechazo completo de duplicados/eventos/semanas/conteos inválidos, enteros estrictos, huecos null frente a ceros explícitos, referencias de procedencia, TTL y cuotas de sesiones, acceso ajeno=404, ausencia de token=401, eliminación, límite de cuerpo, cortes inválidos, ausencia de fuente=503, MASE no disponible y objetivos incompletos sin métricas.

Comprobados: slot real compartido entre solicitudes HTTP concurrentes (429), timeout sin curva parcial (504), no convergencia estructurada (422), fallo del worker (503), errores inesperados sin rutas internas, identificador HTTP y CORS en errores, contrato OpenAPI exportado idéntico al servido y ninguna ejecución de B06 al consultar o cargar datos.

## Pendiente I4

La API y el contrato están disponibles para conexión local. No se ha integrado una aplicación React específica ni realizado despliegue remoto: no se suministraron frontend, destino ni credenciales. La guía incluye ejemplo de consumo y límites de la ejecución local. CI quedó configurada; este documento no afirma que GitHub Actions haya ejecutado el workflow.
