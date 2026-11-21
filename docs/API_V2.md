# EpiSentinel AI 2.0 — REST local

Rama `feat/v2-api`, creada desde `origin/main` actualizado en `b0ded49` el 21 de noviembre de 2026. La API se ejecuta desde el checkout, conserva Streamlit y no modifica los motores B03/B04/B05/B06/B07/B10 ni escribe datos o resultados científicos en disco.

## Ejecución

Python >=3.10. Desde la raíz del checkout:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c requirements-api-repro.txt -e '.[api,dev,app]'
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Swagger: `http://127.0.0.1:8000/api/v1/docs`. ReDoc: `/api/v1/redoc`. OpenAPI 3.1: `/api/v1/openapi.json`. Contrato exportado: `docs/api/openapi.json`. Para exportar una versión nueva, usar una ruta nueva:

```powershell
.\.venv\Scripts\python.exe -m api.export_openapi docs/api/openapi-revision.json
```

El archivo de restricciones fija el entorno de reproducción en Python 3.13; las dependencias generales del proyecto conservan su compatibilidad declarada. Otras versiones de bibliotecas pueden alterar ligeramente un ajuste SARIMA y requieren repetir la regresión estricta.

El panel original `data/processed/panel_casos.parquet` se suministra localmente según la procedencia/licencia de `data/README.md`; no está versionado. Sin él, health informa ausencia y las consultas que lo requieren responden 503. Nunca se genera un panel sustituto. No se reetiquetan fechas ni se imputan datos.

CORS permite localhost/127.0.0.1 en puertos 5173 y 3000. Puede configurarse con `EPISENTINEL_CORS_ORIGINS` (orígenes completos separados por comas). No utiliza cookies. Respuestas con `Cache-Control: no-store` y `X-Request-ID`.

Respaldo funcional:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/platform_app.py --server.address 127.0.0.1
```

## Contrato

Todas las rutas tienen prefijo `/api/v1`. Consultar OpenAPI para tipos, campos obligatorios y respuestas. Ninguna consulta inicia ajustes.

| Método/ruta | Capacidad real |
|---|---|
| GET `/health` | Salud del proceso y presencia del panel; no certifica validez científica |
| GET `/overview` | Conteos estructurales verificables, fuente SHA-256, periodo, universo y regla; sin categorías de riesgo |
| GET `/territories?offset=0&limit=100` | Catálogo municipal candidato IA-I1, códigos ordenados, validación territorial pendiente |
| GET `/series?series=76001&start=0&limit=832` | Valores originales y fechas técnicas, sin transformación |
| GET `/experiments` | Evidencias IA-I1 históricas con ruta y SHA-256; no historial de otras sesiones |
| POST `/forecasts/retrospective` | Ejecución explícita y real de IA-I1/B06; evaluación posterior B10 |
| POST `/sessions` | Token aleatorio de acceso a un espacio temporal aislado |
| DELETE `/sessions/current` | Eliminar sesión y sus conjuntos |
| POST `/datasets/upload` | Cuerpo CSV canónico UTF-8, `Content-Type: text/csv`; `X-Filename` opcional |
| POST `/datasets/manual` | JSON con `rows`, entre 1 y 1000 registros; cod_mun texto, otros campos enteros estrictos |
| GET/DELETE `/datasets/{dataset_id}` | Consultar/eliminar solo un conjunto de la sesión autorizada |
| POST `/datasets/{dataset_id}/series` | Configuración explícita y ejecución B05; no pronóstico |
| GET `/benchmarks` | Evidencia histórica de rendimiento sintético, identificada como tal |
| GET `/methodology` | Métodos, cortes permitidos, recursos, campos y referencias a contratos existentes |

### Pronóstico

```json
{"series":"76001","cut":779,"method":"sarima_sin_estacional","horizon":8}
```

Métodos: `ultimo_valor`, `ingenua_estacional`, `sarima_sin_estacional`, `sarima_estacional`. Corte posicional inclusivo; solo los 24 orígenes completos del protocolo B10 728/780/832, consultables en methodology. Horizonte fijo ocho; alpha 0.05, según IA-I1. No se aceptan datasets de sesión como fuente de pronóstico.

La respuesta conserva la evidencia IA-I1: identidad determinista `request.request_id`, SHA-256 de la fuente, código, método, corte, horizonte, prefijo usado, parámetros, predicciones, bandas cuando existen, convergencia, advertencias, observados y evaluación. El identificador HTTP identifica la petición; el del experimento identifica la configuración científica. `indicators` agrega fuente, periodo, universo, fórmula y estado a cada métrica B10. MASE inválido es null con motivo. No se evalúan horizontes incompletos.

Se reutilizan `prepare`, `execute_bounded` y `evidence` de `app/retrospective.py`; el ajuste recibe únicamente el prefijo hasta el corte. Un proceso hijo, máximo 45 segundos incluyendo arranque, un slot compartido con IA-I1 por proceso servidor, un hilo numérico y máximo 832 posiciones. No hay cola, reintentos, sustitución de método ni resultados parciales. BUSY=429, TIMEOUT=504, fallo de proceso=503, rechazo científico/no convergencia=422. El proceso hijo se termina ante timeout mediante el controlador existente. No se guardan modelos ni resultados REST en disco.

El panel heredado combina 210+220, suma S53 a S52 y completa ausencias con cero. Sus fechas no son calendario epidemiológico oficial. La selección y evaluación son retrospectivas sobre datos ya examinados, sin validación poblacional ni prueba independiente. Ver `docs/IA_I1.md`.

### CSV/manual y construcción B05

Crear sesión y enviar `Authorization: Bearer <token>` en las operaciones datasets y borrado de sesión. Guardar el token solo en memoria del frontend y descartarlo al cerrar la sesión. No transmitirlo en URLs ni logs. TTL fijo de una hora; no se renueva con las consultas. Reiniciar el servidor elimina todas las sesiones. Máximo 32 sesiones, cuatro conjuntos por sesión y cuerpo máximo 1 MiB, también en transferencia por fragmentos. No se escriben archivos temporales ni se usan nombres suministrados como rutas. Crear otro conjunto nunca agrega ni reemplaza automáticamente el anterior.

```csv
cod_mun,ano,semana,cod_eve,conteo
76001,2024,1,210,5
76001,2024,3,210,0
```

```json
{"rows":[{"cod_mun":"76001","ano":2024,"semana":1,"cod_eve":210,"conteo":5}]}
```

Ambas entradas se validan por `load_csv` B04; manual se serializa al mismo contrato sin convertir booleanos o números decimales. Se devuelve reporte original, conteos de filas leídas/entregadas/rechazadas, SHA-256 y registros con referencias de procedencia. Error B04 bloquea la carga completa sin entrega parcial. No se suman duplicados. Eventos permitidos 210/220/580; S53 se conserva según contrato, sin inferir fechas. Los campos `trained=false` y `forecast_eligibility=not_evaluated` no cambian por cargar o construir una serie.

Para B05, POST a `/datasets/{dataset_id}/series`:

```json
{
  "version":"frontend-v1",
  "territory":"76001",
  "event_codes":[210],
  "periods":[[2024,1],[2024,2],[2024,3]],
  "calendar":{"calendar_id":"malla-declarada","version":"1","source":"usuario","verification":"unverified"}
}
```

Se exige malla ordenada explícita; B03/B05 validan pertenencia y eventos. Los huecos permanecen null y los ceros observados siguen siendo cero. Un cliente no puede acreditar calendario enviando `verified`. No se ejecutan B06/B07, no hay asignación a particiones ni marca de entrenamiento. B05 vuelve a validar el payload original y entrega el diagnóstico completo, referencias y elegibilidad pendiente.

### Errores

```json
{"error":{"code":"CSV_REJECTED","message":"B04 rechazó el conjunto completo; no se almacenaron filas","details":{}},"request_id":"identificador-http"}
```

422: esquema inválido o rechazo científico; 401: sesión ausente/expirada; 404: conjunto ajeno o inexistente sin revelar propiedad; 413: tamaño; 415: formato; 429: capacidad/concurrencia; 503: fuente/proceso no disponible; 504: timeout. Errores inesperados devuelven 500 sin revelar trazas o rutas internas. Los errores de validación HTTP omiten valores de entrada; los reportes científicos B04 conservan sus diagnósticos originales para el usuario autorizado.

## Conexión React

Generar tipos desde el contrato exportado con la herramienta OpenAPI del frontend. Ejemplo de consumo sin dependencias adicionales:

```typescript
const base = "http://127.0.0.1:8000/api/v1";
const session = await fetch(`${base}/sessions`, { method: "POST" }).then(r => r.json());
const uploaded = await fetch(`${base}/datasets/upload`, {
  method: "POST",
  headers: { Authorization: `Bearer ${session.token}`, "Content-Type": "text/csv", "X-Filename": file.name },
  body: file,
});
const result = await uploaded.json();
if (!uploaded.ok) throw new Error(`${result.error.code}: ${result.error.message}`);
// El frontend muestra result.report.summary y result.pending_decisions.
// Una carga no habilita el botón de pronóstico histórico para este dataset.
```

## Verificación y alcance de entrega

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

La prueba real Cali se omite explícitamente si no está el panel local. Con panel, ejecuta los cuatro métodos por HTTP en procesos reales y compara estimaciones, bandas y MAE/RMSE/MASE con las evidencias históricas usando tolerancia relativa 1e-8. Comprueba SHA-256 de panel, experimentos y benchmarks antes/después. Otras pruebas cubren errores, límites, aislamiento, expiración, entradas inválidas, procedencia, huecos y concurrencia.

I1–I3 implementados para uso local: estructura, consultas, contrato OpenAPI, IA-I1 real e ingesta B04/B05. I4 ofrece contrato, ejemplo de conexión React y pruebas de backend. La integración visual del frontend y un despliegue remoto requieren su código/destino y credenciales; no se presentan como completados.

Ejecutar solo con un worker y enlazado a loopback. Este almacenamiento en memoria no es autenticación de identidades ni persistencia distribuida. Antes de despliegue público hacen falta autenticación real, autorización, cuotas globales y coordinación/persistencia de sesiones y ejecuciones. No existe límite duro de RSS; el cuerpo y la capacidad se acotan. No levantar varios workers para eludir los límites por proceso.

Referencias de implementación de transporte: [CORS de FastAPI](https://fastapi.tiangolo.com/tutorial/cors/) y [errores de FastAPI](https://fastapi.tiangolo.com/tutorial/handling-errors/). Las decisiones científicas proceden de los contratos del repositorio, no de documentación del framework.
