# Cierre de preparación Render — 21 de noviembre de 2026

Base verificada y sincronizada: `38f1aa23bc7bc900c11ea3c6b5f0a232efdaa806`, merge real del PR #35. Rama creada desde esa referencia: `feat/v2-render-deployment`. No se ha hecho merge de esta rama ni se han creado servicios de hosting, URLs públicas o recursos de almacenamiento.

## Veredicto de alcance

**P0 y último valor están preparados para despliegue manual de demostración. SARIMA no está aprobado para habilitación general en Render Free.** La provisión del panel requiere custodia/URL autorizadas y la aceptación remota está pendiente. No se afirma que Docker local reproduzca el hardware de Render.

El perfil público conserva consultas reales, OpenAPI, clave de operador para operaciones costosas y sesiones, límites de frecuencia y memoria, ingesta opcional apagada y un solo worker. React funciona con respuestas reales y no contiene mocks ni claves embebidas. La guía paso a paso está en [RENDER_FREE.md](../RENDER_FREE.md).

## Pruebas

- Regresión completa final: **860 aprobadas, cuatro omitidas**, sin fallos (113,10 s).
- Perfil Render y API: **46 casos aprobados dentro de la regresión final**, sin omisiones de ese grupo. La ejecución específica previa aprobó 44; las dos pruebas posteriores de almacenamiento HTTPS quedaron incluidas en la suite completa.
- Frontend: **tres pruebas aprobadas**, instalación limpia `npm ci` y build de producción HTTPS. Comprobación de build en Windows/Node 20.20.2 y Linux/Node 22.16.0.
- Negativas de build: falta de `VITE_API_URL` e intento de exponer `VITE_OPERATOR_KEY` rechazados explícitamente; build válido posterior completado.
- Blueprint: validado localmente contra `https://render.com/schema/render.yaml.json` sin aplicar el YAML. Dos servicios, API `plan: free`, Static Site, ambos con auto-deploy apagado; sin DB, disco, cron ni worker adicional.
- Browser local: API conectada, catálogo real de 1071 candidatos y 832 posiciones históricas de Cali visibles tras Consultar serie. Se corrigió la carga inicial para respetar los dos slots públicos, solicitando capacidades/catálogo/metodología de forma secuencial. Se cerraron los servidores de preview propios al terminar.
- Advertencia no silenciada: Starlette anuncia deprecación del cliente de pruebas httpx. No hubo modificación del motor ni relajación de tolerancias.

Las cuatro omisiones del conjunto completo, verificadas individualmente:

| Prueba | Causa local exacta |
|---|---|
| `tests/test_ingest.py::test_pipeline_real_end_to_end` | Ausentes `data/raw/Dengue_210.csv`, `Dengue_220.csv` y `Dengue_580.csv`; marcador de módulo «CSV reales no presentes en data/raw/ (no se versionan en Git)». |
| `tests/test_ingest.py::test_reporte_es_serializable_a_json` | Mismo marcador y mismos tres originales ausentes. |
| `tests/test_demo_preflight.py::test_real_demo_counts_and_manifest_are_consistent` | Ausente `data/processed/b08_demo.csv`; «Real demo CSV is local and not versioned». |
| `tests/test_demo_preflight.py::test_offline_rehearsal_real_artifacts_and_session_isolation` | Requiere demo CSV y panel; el panel está presente, pero el demo CSV falta; «Real demonstration artifacts are local». |

Los cuatro métodos reales de Cali en la regresión Windows y el aprovisionamiento exacto del panel sí se ejecutaron. No se generaron sustitutos para eliminar omisiones.

## Ensayos con límite físico local

Imagen Python 3.13.4 slim-bookworm por digest, Linux/amd64, dependencias directas y transitivas fijadas en `deploy/requirements.lock`. Un worker y bibliotecas numéricas a un hilo. Cgroup de **536.870.912 B**, swap máximo cero, CPU `.5`, filesystem de imagen solo lectura, panel montado solo lectura y `/tmp` efímero. Todas las evidencias nuevas permanecen separadas de los resultados históricos.

| Evidencia | Pico global de cgroup | Último valor | SARIMA no estacional |
|---|---|---|---|
| `memory-local-01.json` | 251.027.456 B / 239,40 MiB | 200 / 4,77 s | 200 / 16,62 s / convergente |
| `memory-local-02.json` | 250.875.904 B / 239,25 MiB | 200 / 3,39 s | 200 / 16,48 s / convergente |
| `memory-local-03.json` | 413.917.184 B / 394,74 MiB | 200 / 5,07 s | 503 / margen de memoria insuficiente |
| `memory-local-04.json` — código final | 397.172.736 B / 378,77 MiB | 200 / 3,97 s | 503 / margen de memoria insuficiente |

`oom=0` y `oom_kill=0` en las cuatro. Las ejecuciones 03/04 salen con código 1 por el rechazo de SARIMA y se conservan como tales; no son ensayos íntegramente aprobados. No se da por probado que los 239 MiB de las primeras sean un consumo universal. El guard impide el ajuste cuando el cgroup supera 256 MiB antes de lanzar el hijo. No existe límite duro RSS por petición.

En la segunda ejecución, RSS máximo del servidor durante SARIMA 181.071.872 B; hijo 202.637.312 B. El medidor también publica RSS del servidor por fase y uso del cgroup; esas medidas no se suman como memoria física única. Los controles B06 directos se ejecutaron en el mismo Linux y sus puntos/bandas coinciden exactamente con REST. Ambos SARIMA positivos presentan 11 iteraciones y convergencia.

Frente al artefacto Windows, SARIMA Linux no pasa rtol=1e-8 para estimaciones/bandas: máximo delta absoluto `4.658087300413172e-05`. No se oculta, relaja ni se reescribe la evidencia histórica. La causa exacta de la variación entre plataformas no quedó establecida. Habilitar SARIMA exige aceptación científica y nueva prueba real en el hosting.

Identificador de imagen local inspeccionada: `sha256:36668fe2f944729d21fa71fd7ff1c9627505e8a7295d5a496c29d0a9ff66f039`. La evidencia 04 registra las huellas de los archivos de código/lock utilizados; comprobadas contra el checkout antes de publicar el PR.

## Datos, imagen y credenciales

Panel: **1.047.381 bytes**, DataFrame decodificado **7.495.956 bytes**, 1124 × 832; columnas DatetimeIndex, índice territorial y valores numéricos agregados. SHA-256 `41e592e9fb548085377a1c6d7ed7de026496d8c530583ba5aaf6c80e2fee5989`.

La imagen se inspeccionó en un contenedor nuevo, antes de provisión: no contiene `/app/data`, archivos parquet, `.git`, `.venv`, frontend, variables runtime EPISENTINEL ni secretos de almacenamiento. Usuario UID 10001. Streamlit/Plotly/sklearn no están instalados en la imagen de API; permanecen intactos en el repositorio para el respaldo local. El Dockerfile usa COPY de código y evidencias documentales permitidas, sin copia de datasets ni secretos. `.dockerignore` opera con lista de permitidos y excluye también claves, PEM y archivos de credenciales.

La revisión del diff no detectó credenciales reales ni rutas personales incorporadas. Las cadenas que simulan claves/URLs en tests están identificadas como fixtures de prueba. El panel local, node_modules, dist y archivos .env no se incluyen en Git. URLs firmadas y bearer del almacenamiento solo se configuran manualmente en Environment del backend; se eliminan del entorno del proceso antes de iniciar la API y sus hijos.

Se comprobó diff vacío contra main en `src/`, `app/`, `data/`, `reports/`, `configs/`, `docs/experiments/` y `docs/benchmarks/`. Ningún motor B03/B04/B05/B06/B07/B10, aplicación Streamlit ni archivo histórico fue modificado. La regresión verifica además hashes antes/después de cada ejecución real de Cali. `docs/api/openapi.json` local permanece idéntico al esquema servido por `api.main`; el perfil público añade el requisito OperatorKey en su OpenAPI en vivo.

## Pendiente fuera de esta entrega

- El custodio debe autorizar la publicación del panel y proporcionar una URL HTTPS directa existente, con disponibilidad tras cada suspensión y sin redirecciones.
- Crear manualmente los servicios Free, cargar secretos solo en backend, configurar URLs reales y orígenes exactos, y verificar desde el frontend público.
- Ejecutar `scripts/verify_render.py`, comprobar memoria/CPU en Dashboard durante un ensayo autorizado, rehidratación tras suspensión y revocación de sesiones efímeras.
- SARIMA continúa deshabilitado; no elevar planes ni crear servicios externos para resolverlo sin una decisión separada.

El workflow adicional es manual y contiene únicamente checks/build; no ejecuta un deploy. No se afirma CI remota verde ni una URL pública ya operativa.
