# Render Free — preparación V2, despliegue manual

Rama `feat/v2-render-deployment`, desde `main` actualizado en `38f1aa2` (merge real del PR #35). Esta entrega prepara los servicios; **no crea recursos de Render, publica datos, registra tarjetas ni realiza despliegues externos**. Revisar este PR y autorizar su merge antes de desplegar desde main.

## Qué se puede publicar

- **P0:** consultas reales, procedencia SHA-256, contrato OpenAPI y React en `frontend/` consumiendo la API remota.
- **P1:** último valor B06, protegido por clave de operador. SARIMA no estacional se ensayó realmente en Linux con 512 MiB, pero queda **deshabilitado por defecto y no aprobado para habilitación general en Free**: dos ejecuciones convergieron y dos posteriores fueron rechazadas por falta de margen de memoria. Exige aceptación explícita del entorno numérico y comprobación remota antes de considerar su habilitación.
- **P2:** CSV/manual B04/B05, deshabilitados por defecto; activación manual y cuotas reducidas. Experimentos y benchmarks son evidencias existentes, con su contexto histórico/sintético explícito.

La URL del Static Site será la entrada pública para Kerin y el resto del equipo; el Web Service tendrá una segunda URL HTTPS que React utiliza. **Todavía no existen esas URLs en esta entrega.** No hay mocks, sustitución automática de método ni resultados fabricados.

Render documenta suspensión del Web Service Free tras 15 minutos sin tráfico, reactivación cercana a un minuto y pérdida del filesystem al reiniciar, redesplegar o suspender. Hay 750 horas gratuitas por workspace/mes y límites de transferencia/build; revisar la facturación y los límites vigentes antes de crear recursos. No usar upgrades, discos, bases de datos, workers, cron ni dominios con cargo. Ver [limitaciones oficiales Free](https://render.com/docs/free). El Static Site es gratuito y recibe su URL propia; ver [Static Sites](https://render.com/docs/static-sites).

## Mediciones reales y decisión sobre SARIMA

Evidencias nuevas, sin sobrescribir históricos: [`memory-local-01.json`](render/memory-local-01.json), [`02`](render/memory-local-02.json), [`03`](render/memory-local-03.json) y [`04`](render/memory-local-04.json). La cuarta corresponde al código final y contiene sus huellas.

**Resultado operativo final:** con las protecciones definitivas, P0 y último valor respondieron 200; el intento SARIMA respondió **503 `INSUFFICIENT_MEMORY_HEADROOM`**, sin ejecutar modelo ni devolver curva de reemplazo. En esa ejecución el pico global fue **397.172.736 B (378,77 MiB)**; en la tercera fue **413.917.184 B (394,74 MiB)**. Ambas mantuvieron `oom=0` y `oom_kill=0`. No seleccionar únicamente las ejecuciones de menor memoria para aprobar el hosting. La diferencia de consumo entre contenedores se observó, pero no se estableció su causa exacta; la contabilidad de caché/páginas compartidas puede influir. SARIMA permanece deshabilitado por defecto.

Se ejecutó la imagen Docker Linux/amd64, Python 3.13.4, con `--memory=512m --memory-swap=512m --cpus=0.5`, filesystem de imagen de solo lectura y panel montado solo en lectura. Esa cuota CPU es una condición del ensayo local, **no una garantía sobre CPU de Render**. Muestreo cada 10 ms, más `memory.peak` del cgroup. El cgroup incluye supervisor de medición, kernel y caché; RSS comparte páginas y no equivale a memoria física única. Docker local puede compartir páginas con otras imágenes/contenedores, de modo que también se publican los RSS individuales. Ninguna cifra se presenta como medición en hardware Render.

Segunda ejecución, Cali 76001, corte 779, horizonte ocho:

| Fase | HTTP / tiempo | Pico RSS servidor | Pico RSS hijo de pronóstico | Pico cgroup muestreado |
|---|---|---|---|---|
| Arranque con verificación del panel | 200 / 15,96 s | 168.570.880 B | — | 140.554.240 B |
| Overview | 200 / 0,52 s | 177.651.712 B | — | 135.245.824 B |
| Serie Cali | 200 / 0,19 s | 179.421.184 B | — | 136.585.216 B |
| Último valor | 200 / 3,39 s | 181.538.816 B | 113.004.544 B | 194.691.072 B |
| SARIMA no estacional | 200 / 16,48 s | 181.071.872 B | 202.637.312 B | 250.875.904 B |

Pico cgroup de toda la segunda ejecución: **250.875.904 B (239,25 MiB)**; `oom=0`, `oom_kill=0`, swap permitido cero. La primera dio 251.027.456 B (239,40 MiB), SARIMA 16,62 s. Los picos de RSS servidor e hijo SARIMA suman aproximadamente 366 MiB, una cota conservadora que cuenta páginas compartidas dos veces y no incluye toda la memoria del sistema. El panel comprimido pesa **1.047.381 B**; su DataFrame decodificado ocupa **7.495.956 B**, 1124 filas × 832 posiciones, columnas DatetimeIndex y valores numéricos agregados.

**Regresión científica y diferencia de plataforma:** las estimaciones/bandas REST coinciden exactamente con una ejecución directa B06 en el mismo Linux; el estado de ajuste también coincide. Último valor coincide con la evidencia histórica. SARIMA converge (11 iteraciones), pero las estimaciones/bandas Linux NO satisfacen la comparación rtol=1e-8 contra el artefacto Windows: máxima diferencia absoluta 0,00004658087300413172 entre los valores comparados. Se conserva esa discrepancia como `false` en la evidencia, sin relajar pruebas, editar históricos ni cambiar algoritmos. No atribuirla causalmente a una biblioteca concreta: se comprobó igualdad de algoritmo y entorno dentro de Linux, no la causa exacta entre plataformas.

Antes de habilitar SARIMA: el responsable científico debe aceptar/documentar esa diferencia de entorno y comprobar el mismo contenedor en Render. No afirmar reproducción bit a bit del histórico Windows. El resultado devuelto, si se habilita, es el resultado real Linux con sus versiones y limitaciones. Los ensayos solo cubren un origen municipal; otros cortes/series pueden consumir más tiempo o memoria.

## Provisión autorizada y reproducible del panel

El panel **no está en Git, el contexto de build ni las capas de la imagen**. Tampoco hay URL histórica inventada ni reconstrucción desde una exportación reciente del portal. Se requiere una copia del custodio con esta identidad, fijada en `deploy/panel-manifest.json`:

- Nombre: `panel_casos.parquet`.
- Bytes: `1047381`.
- SHA-256: `41e592e9fb548085377a1c6d7ed7de026496d8c530583ba5aaf6c80e2fee5989`.
- Procedencia/licencia: [README de datos](../data/README.md), [B02](PROCEDENCIA_B02.md), INS / conjunto 4hyg-wa9d, CC BY-SA 4.0 con atribución, licencia e identificación de cambios.

Procedimiento del custodio, **manual**:

1. Obtener la copia binaria conservada y comprobar bytes/hash con `Get-FileHash -Algorithm SHA256`. No abrir/guardar con Excel ni regenerar fechas.
2. Confirmar que autoriza servir estos conteos agregados, que no contiene datos individuales privados y que conserva los avisos/licencia. La revisión local encontró una matriz numérica con índice territorial y fechas, sin columnas individuales; la aprobación de publicación sigue siendo del custodio.
3. Disponer el archivo en un almacenamiento HTTPS **existente y autorizado**, con respuesta directa de bytes: sin página HTML, login interactivo ni redirecciones. Puede ser una URL firmada o un endpoint estable autenticado con bearer. Elegir un recurso sin costos adicionales dentro de sus cuotas; este trabajo no crea ni selecciona una cuenta de almacenamiento por el usuario.
4. Guardar únicamente en Environment del backend `EPISENTINEL_PANEL_URL`, `EPISENTINEL_PANEL_HOST` (hostname exacto, sin esquema/ruta) y, si corresponde, `EPISENTINEL_PANEL_BEARER`. Nunca en Git, Docker build args, frontend o variables `VITE_*`.
5. Establecer manualmente `EPISENTINEL_PANEL_APPROVED_SHA256` a la huella anterior; sin ese consentimiento explícito el arranque se rechaza.

`deploy.start` hidrata `/tmp/episentinel/data/processed/panel_casos.parquet` antes de aceptar tráfico. El descargador admite solo HTTPS/443 y el hostname autorizado, rechaza credenciales de URL y redirecciones, acota bytes/lecturas y verifica tamaño, hash y forma a través del cargador IA-I1. No modifica fechas/valores. Si el destino ya existe, solo lo acepta si coincide; jamás lo sobrescribe. Ante error, el servicio no arranca y muestra un código sin URL firmada, tokens o cuerpo de respuesta. No usar este mecanismo como descargador de URLs aportadas por usuarios HTTP.

En cada arranque tras suspensión/redeploy vuelve a ser necesaria la fuente. Una URL firmada vencida impide el arranque: renovarla manualmente en Environment o usar un endpoint estable con credencial revocable. No hay copia histórica alternativa automática. La descarga es runtime, no build; una imagen exportada no contiene el panel. `EPISENTINEL_PANEL_FILE` existe para ensayos locales con bind mount de solo lectura; dejarla ausente en Render cuando se usa URL.

## Variables del backend

| Variable | Configuración |
|---|---|
| `PORT` | La proporciona Render; `deploy.start` la lee, valida y usa. No fijarla a 8000. Default local 10000. |
| `EPISENTINEL_CORS_ORIGINS` | Orígenes HTTPS reales exactos del frontend, separados por coma, sin slash final, path ni wildcard. Obligatoria. |
| `EPISENTINEL_OPERATOR_KEY` | Secreto aleatorio ASCII de al menos 32 caracteres, solo backend. Obligatorio. Generarlo localmente con `secrets.token_urlsafe(32)` y pegarlo manualmente sin guardarlo en archivos del repo. |
| `EPISENTINEL_PANEL_URL` | URL HTTPS directa autorizada. Tratar como secreto si está firmada. |
| `EPISENTINEL_PANEL_HOST` | Hostname exacto de la URL anterior. |
| `EPISENTINEL_PANEL_BEARER` | Opcional; secreto del endpoint de almacenamiento. No es la clave de operador. |
| `EPISENTINEL_PANEL_APPROVED_SHA256` | Huella exacta aprobada por el custodio; obligatoria. |
| `EPISENTINEL_RUNTIME_ROOT` | `/tmp/episentinel`, almacenamiento efímero. |
| `EPISENTINEL_FORECAST_METHODS` | Default `ultimo_valor`. Vacío deshabilita todos. Tras aceptación explícita: `ultimo_valor,sarima_sin_estacional`. No admite SARIMA estacional ni ingenua estacional en este perfil. |
| `EPISENTINEL_SARIMA_ACCEPTED` | Ausente por defecto. `1` solo después de aceptación científica/recursos y prueba remota. |
| `EPISENTINEL_ENABLE_INGESTION` | Default `0`; cambiar a `1` solo si se acepta P2 efímero con sus cuotas. |
| `EPISENTINEL_ALLOW_LOOPBACK_ORIGIN` | Solo preview local: `1` permite HTTP exacto localhost/127.0.0.1. **Ausente en Render.** |

## Protección del servicio gratuito

Entrypoint público: **`api.render:application --factory`**, a través de `python -m deploy.start`. No desplegar `api.main:app`, que conserva el contrato de uso local de I1–I3.

- Todas las operaciones POST/DELETE y el acceso a datasets exigen `X-Operator-Key`. Datasets además mantienen bearer de sesión aislada. CORS no se usa como autenticación.
- La clave de operador se introduce en el formulario React solo por personas autorizadas, permanece en memoria y se descarta al recargar. Nunca se distribuye en el bundle ni `localStorage`. Es acceso compartido revocable de demostración, no autenticación nominal/RBAC.
- Cuotas globales por proceso: 120 consultas/minuto, cinco solicitudes protegidas/minuto, dos solicitudes activas como máximo, un ajuste B06 concurrente. No dependen de cabeceras de IP manipulables. Health/readiness quedan exentos del presupuesto de consultas.
- El perfil Render reduce el cuerpo a **128 KiB**, antes de parsearlo, incluso con envío fragmentado. El perfil local sigue en 1 MiB. Manual conserva máximo 1000 filas, sujeto además al tamaño.
- Sesiones públicas: máximo cuatro, TTL fijo 1800 s, un dataset por sesión. Ingesta deshabilitada por defecto. Sesiones/datasets se pierden al suspender/reiniciar y no se guardan en disco.
- Métodos no habilitados devuelven 403. No cambian a otro modelo. Slot/presupuesto ocupado=429. Timeout de ajuste=504, sin salida parcial, máximo 45 s incluyendo arranque.
- SARIMA exige además poder leer el cgroup y que el consumo actual no supere **256 MiB**, dejando margen antes del hijo. Sin medición disponible o con mayor consumo responde 503. No es un límite duro de RSS ni una garantía universal frente a OOM.
- Un worker Uvicorn y un hilo por biblioteca numérica. Usuario no root en Docker; `--no-access-log` evita registrar paths/query de usuarios en el acceso Uvicorn. El panel se aprovisiona sin imprimir credenciales.

## Crear manualmente los servicios Free

Las opciones actuales de Render se contrastaron con la [guía FastAPI](https://render.com/docs/deploy-fastapi) y la [especificación Blueprint](https://render.com/docs/blueprint-spec). `render.yaml` es una plantilla con Docker, Static Site, health check y auto-deploy desactivado. **No aplicarla automáticamente**; crearla o usar Dashboard es una acción posterior del dueño. No incluye discos, bases de datos, cron, workers ni previews con costo.

### 1. Preparar las URLs y el frontend

En Render: **New → Static Site**, conectar `Diland-sketch/episentinel-ai` y seleccionar `main` después del merge autorizado del PR de despliegue.

| Campo | Valor |
|---|---|
| Root Directory | `frontend` |
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |
| Node | `NODE_VERSION=22.16.0` |
| Auto-Deploy | Off |
| Rewrite | `/*` → `/index.html` |

Se necesita `VITE_API_URL=https://<backend-real>.onrender.com/api/v1`. No es un secreto. Si todavía no existe backend, el primer build **fallará de forma explícita** al faltar esa variable; esto permite obtener la URL asignada al Static Site sin publicar una interfaz con datos simulados o una API inventada. Copiar la URL HTTPS que Render asigne realmente. No suponer que el nombre elegido garantice un subdominio concreto.

Si ya se conocen/reservaron ambas URLs reales, configurar la variable antes del primer build y omitir esa etapa pendiente. La configuración de producción rechaza HTTP, credenciales/query en URL y otras variables `VITE_*`; el único valor de ese prefijo que puede exponerse es la URL de API.

### 2. Crear el backend

En Render: **New → Web Service**, conectar el mismo repositorio y main autorizada.

| Campo | Valor |
|---|---|
| Runtime | Docker |
| Plan | **Free**; comprobarlo antes de Create |
| Root Directory | Vacío, raíz del repositorio |
| Dockerfile Path | `./Dockerfile` |
| Docker Context | `.` |
| Build | Lo ejecuta Dockerfile con base por digest y `deploy/requirements.lock` |
| Start / Docker Command | Dejar el CMD de imagen: `python -m deploy.start` |
| Health Check | `/api/v1/ready` |
| Auto-Deploy | Off |
| Worker | Uno, fijado por el entrypoint; no crear Background Worker |

Cargar las variables de la tabla anterior. `EPISENTINEL_CORS_ORIGINS` debe ser la URL real del Static Site obtenida en el paso anterior. Iniciar con último valor y sin ingesta ni SARIMA. Confirmar el costo mostrado cero, no añadir disco/DB ni upgrades; detener el procedimiento si Render solicita una opción con cargo.

El start usa `--host 0.0.0.0 --port $PORT --workers 1`; la lectura de PORT ocurre en Python, sin interpolación de shell. `/health` informa vida/presencia; `/ready` es 200 solo con el panel aprovisionado, o 503 si falta. No arrancar sin panel para simular disponibilidad. Render espera éxito HTTP para health checks; ver [health checks oficiales](https://render.com/docs/health-checks).

### 3. Conectar React

Copiar la URL real del Web Service y fijar en el Static Site **solo** `VITE_API_URL=https://<backend-asignado>/api/v1`. Manual Deploy del Static Site para reconstruir; Vite fija esa URL durante el build. No introducir claves de operador, URL firmada del panel o bearer de almacenamiento en frontend.

Abrir la URL del Static Site. Debe mostrar conexión, catálogo real y, tras Consultar serie en Cali, 832 posiciones originales. Cambiar selección invalida la salida anterior. El formulario solo ofrece métodos anunciados por `/capabilities`. Un operador autorizado puede introducir su clave y ejecutar último valor. Consultar o configurar no entrena. Los errores se muestran y no generan curvas de reemplazo.

### 4. Verificar remotamente antes de compartir

Desde el checkout con Python:

```powershell
python scripts/verify_render.py 'https://<backend-real>/api/v1' --frontend-origin 'https://<frontend-real>'
# Solo si se quiere ejecutar un ensayo real autorizado:
$env:EPISENTINEL_OPERATOR_KEY = Read-Host 'Clave de operador' -MaskInput
python scripts/verify_render.py 'https://<backend-real>/api/v1' --frontend-origin 'https://<frontend-real>' --forecast ultimo_valor
Remove-Item Env:EPISENTINEL_OPERATOR_KEY
```

Sustituir los marcadores por URLs reales. El modo por defecto comprueba health/readiness, capacidades, SHA del panel, OpenAPI protegido, serie Cali, CORS y rechazo anónimo 401 antes de cualquier ajuste. `--forecast` ejecuta únicamente el método solicitado, sin fallback ni reintentos. Añadir `sarima_sin_estacional` solo después de su aceptación/habilitación.

En Dashboard comprobar memoria/CPU reales durante ese ensayo, ausencia de OOM/restarts, convergencia y cumplimiento de 45 s; conservar evidencia nueva. Tras una suspensión real comprobar que el panel se vuelve a hidratar y los tokens de sesión anteriores ya no sirven. Comprobar que un origen diferente no recibe CORS. No usar pings periódicos para evitar la suspensión ni agregar servicios de keep-alive.

La verificación remota está preparada, **no ejecutada**: no se creó ningún servicio externo ni una URL pública durante este trabajo. Las cifras de Docker no sustituyen este paso.

## Repetir las mediciones localmente

Docker Linux, desde la raíz del checkout, con el panel local exacto fuera de Git:

```powershell
docker build -t episentinel-render:local .
$panelPath = (Resolve-Path data/processed/panel_casos.parquet).Path
$evidencePath = (Resolve-Path docs/render).Path
docker run --rm --memory=512m --memory-swap=512m --cpus=0.5 --pids-limit=64 --read-only --tmpfs /tmp:rw,nosuid,size=64m --mount "type=bind,source=$panelPath,target=/provision/panel.parquet,readonly" --mount "type=bind,source=$evidencePath,target=/evidence" -e EPISENTINEL_PANEL_FILE=/provision/panel.parquet -e EPISENTINEL_PANEL_APPROVED_SHA256=41e592e9fb548085377a1c6d7ed7de026496d8c530583ba5aaf6c80e2fee5989 --entrypoint python episentinel-render:local scripts/profile_render.py --output /evidence/medicion-nueva.json
```

La salida debe ser un archivo nuevo: el medidor rechaza sobrescribir evidencia. Crea una clave temporal en memoria, ejecuta consultas/ajustes reales y controla REST contra B06 directo. El contenedor no descarga panel desde un destino externo durante este ensayo: utiliza el bind mount aprobado. El ensayo de provisión HTTPS y las negativas usan tests controlados; todavía falta probar la URL elegida por el custodio.

El medidor termina con código 1 cuando una operación no produce HTTP 200 y conserva la evidencia del rechazo. Las ejecuciones 03/04 tienen ese estado por el 503 de SARIMA; no se presentan como ensayos totalmente aprobados. No modificar el límite para obtener una corrida verde ni repetir hasta ocultar el rechazo.

## Contingencia si no cabe, falla o supera el tiempo

1. Mantener P0 y último valor. No convertir un fallo SARIMA en salida de baseline.
2. Quitar `sarima_sin_estacional` de `EPISENTINEL_FORECAST_METHODS`; si también falla baseline, dejar la variable vacía. React refleja las capacidades y no ofrece ese método. Ingesta continúa desactivada.
3. Conservar error/diagnóstico y evidencia nueva. Reducir concurrencia/carga o investigar el entorno sin cambiar motores, órdenes, transformaciones, datos ni métricas.
4. Ejecutar SARIMA localmente en el entorno científico acreditado y exportar evidencia nueva si el equipo lo necesita. No presentar esa evidencia como ejecución del servicio remoto.
5. Un cambio de hosting/plan o una arquitectura de trabajos externa requiere decisión y autorización separadas. No se actualiza a pago automáticamente.

## Pruebas e integridad

Pruebas de perfil público y API: `python -m pytest tests/test_render_deployment.py tests/test_api.py -q -rs -p no:cacheprovider`. Regresión completa: `python -m pytest -q -rs -p no:cacheprovider`. Frontend: `npm ci`, `npm test`, build con VITE_API_URL HTTPS. El workflow adicional de despliegue es **manual**, no crea recursos y no ejecuta una publicación.

No hay cambios en `src/episentinel/`, motores científicos, `app/` (incluido Streamlit), datos, reportes ni evidencias históricas. La única adaptación de `api/main.py` permite una raíz runtime distinta para el panel; su contrato OpenAPI local permanece idéntico. El perfil público tiene su propio contrato y exige la clave en OpenAPI. Ver `docs/render/VERIFICACION.md` para el cierre de pruebas y el alcance pendiente.
