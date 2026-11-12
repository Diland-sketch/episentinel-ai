# B02 — procedencia y reproducción desde los originales

Actualización documental: 11/11/2026. Fuente del nuevo vínculo histórico y fecha:
Diland, responsable del proyecto. Las instrucciones siguientes documentan operaciones
futuras; no se descargaron datos ni se regeneraron salidas durante esta tarea.

## 1. Evidencias y alcance

El Issue #2 exige huella, fuente, fecha, condiciones de uso, evidencia verificable
e instrucciones de reconstrucción. El [manifiesto](../data/README.md) registra los
tres originales, su identidad, procedencia declarada y licencia actual verificada.

Los metadatos oficiales de
[4hyg-wa9d](https://www.datos.gov.co/api/views/4hyg-wa9d.json), consultados el
11/11/2026, devolvieron los siguientes campos (transcripción selectiva, sin datos
personales de propietarios ni registros del conjunto):

```json
{
  "id": "4hyg-wa9d",
  "name": "Datos de Vigilancia en Salud Pública de Colombia",
  "attribution": "Instituto Nacional de Salud - INS, Bogotá D.C.",
  "attributionLink": "https://portalsivigila.ins.gov.co/Paginas/Buscador.aspx",
  "licenseId": "CC_40_BY_SA",
  "license": {
    "name": "Creative Commons Attribution | Share Alike 4.0 International",
    "termsLink": "http://creativecommons.org/licenses/by-sa/4.0/legalcode"
  }
}
```

La descripción oficial identifica un histórico de eventos por municipio/departamento
de ocurrencia, semana epidemiológica y año desde 2007. No resuelve aquí el calendario
operativo ni otras decisiones de B03. Los metadatos actuales no prueban qué filtros
usó el usuario en septiembre ni que la versión actual sea idéntica a la descargada.

| Encabezado visible en metadatos/originales | Campo de consulta del portal | Tipo del portal |
|---|---|---|
| COD_EVE | cod_eve | number |
| Nombre_evento | nombre_evento | text |
| SEMANA | semana | number |
| ANO | ano | number |
| COD_DPTO_O | cod_dpto_o | number |
| COD_MUN_O | cod_mun_o | number |
| Departamento_ocurrencia | departamento_ocurrencia | text |
| Municipio_ocurrencia | municipio_ocurrencia | text |
| conteo | conteo | number |

## 2. Recuperar los mismos archivos históricos

1. Solicitar al custodio del proyecto las copias originales conservadas de la
   descarga del 23/09/2026. Las copias locales ya auditadas se encuentran en
   `C:\Users\dilan\Downloads` y en `data/raw` del proyecto original; ninguna
   ruta implica disponibilidad pública ni respaldo compartido garantizado.
2. Obtenerlas por copia binaria en una carpeta nueva; no abrir y guardar con Excel,
   cambiar codificación, ordenar filas, eliminar eventos ajenos o editar encabezados.
3. Comprobar nombres, bytes y SHA-256 con el manifiesto. Por ejemplo, desde la raíz:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath data/raw/Dengue_210.csv,data/raw/Dengue_220.csv,data/raw/Dengue_580.csv
.\.venv\Scripts\python -B scripts/audit_csv_sources.py --source-dir data/raw
```

La auditoría solo lee fuentes y reporte; imprime JSON. Salida 0 indica coincidencia
de los 25 controles vigentes, 1 discrepancias y 2 error de entrada. No guarda ni
normaliza los originales. `blocked: true` sigue siendo esperado por los eventos
ajenos: auditoría coincidente no habilita cargas bloqueadas.

Con las mismas huellas se identifica el mismo material histórico, aunque haya
cambiado el portal. Sin esas copias o un archivo institucional de la misma versión,
no está probado que pueda recuperarse byte a byte desde una exportación actual.

## 3. Descargar una versión actual del portal

Procedimiento propuesto de nueva extracción; no reconstrucción comprobada de los
filtros históricos. Solo se consultaron metadatos, no se ejecutaron exportaciones.

1. Abrir la [ficha oficial](https://www.datos.gov.co/Salud-y-Protecci-n-Social/Datos-de-Vigilancia-en-Salud-P-blica-de-Colombia/4hyg-wa9d/about_data)
   y acceder a su vista de datos. Comprobar título, ID, entidad y licencia visible.
2. Para obtener cada evento, usar la función de filtro del portal sobre el campo
   numérico `COD_EVE` (`cod_eve`): igualdad exacta a 210, después 220 y después 580,
   en exportaciones separadas. Esto es un filtro definido para la nueva extracción;
   no se afirma que fuera el utilizado en 2026-09-23.
3. Registrar cualquier otro filtro. Si se pretende comparar solo 2007–2022,
   registrar expresamente la restricción adicional de `ANO` entre esos años como
   decisión de la nueva extracción; el periodo observado no prueba un filtro antiguo.
   No filtrar mediante búsqueda libre del texto "210", "220" o "580".
4. Exportar la vista filtrada a CSV conservando las nueve columnas y sus encabezados,
   sin agregaciones, renombrados, limpieza ni redondeo. Registrar fecha/hora de la
   nueva descarga, filtros, formato y si se exportó la vista filtrada o el conjunto
   completo. Verificar esto antes de tratar el archivo como una fuente por evento.
5. Guardar fuera de `data/raw` del proyecto activo y fuera de Git, bajo una carpeta
   de nueva extracción con fecha. Conservar el archivo original tal como se descargó;
   cualquier nombre local alternativo se registra aparte.
6. Comparar huellas, estructura, periodo, eventos y conteos con el manifiesto.
   El adaptador histórico exige encabezados exactos: si el portal produce nombres
   técnicos en minúsculas u otro formato, no editar los archivos para forzar una
   coincidencia. Registrar la diferencia y tratar su adaptación como trabajo futuro.

No se proporciona una URL de exportación no verificada. No se han observado en esta
tarea los controles interactivos ni todas las opciones de exportación del portal.
Una descarga actual puede cambiar contenido, orden o serialización, aun sin cambios
epidemiológicos. Una huella diferente no demuestra corrupción, pero sí que no son
los mismos bytes. El filtro exacto por evento tampoco reproduciría las 22 filas
ajenas históricas; su causa original sigue sin acreditarse.

## 4. Reconstruir el histórico con el código existente, sin pisar salidas

La reconstrucción requiere los originales identificados y dependencias del proyecto.
No confundir esta ejecución heredada con la ingesta conservadora nueva: conserva el
plegado S53, fechas posicionales y relleno de ceros, pendientes de B03.

Ejemplo futuro desde la raíz del repositorio. Genera una carpeta temporal única y
trabaja allí. `git archive HEAD` incluye solo archivos confirmados; para reproducir
el incremento previo, la referencia registrada en esta tarea es `eff3dd9`.
Los cambios documentales aún no confirmados no forman parte del archivo de HEAD.

```powershell
$sourceRepo = (Get-Location).Path
$rebuildRoot = Join-Path $env:TEMP ('episentinel-b02-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $rebuildRoot | Out-Null
$archivePath = Join-Path $rebuildRoot 'source.zip'
git archive --format=zip "--output=$archivePath" HEAD
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar la copia del código' }
$rebuildRepo = Join-Path $rebuildRoot 'repo'
Expand-Archive -LiteralPath $archivePath -DestinationPath $rebuildRepo
foreach ($name in @('Dengue_210.csv','Dengue_220.csv','Dengue_580.csv')) {
    Copy-Item -LiteralPath (Join-Path $sourceRepo ('data/raw/' + $name)) -Destination (Join-Path $rebuildRepo ('data/raw/' + $name))
}
Set-Location -LiteralPath $rebuildRepo
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Falló la creación del entorno' }
.\.venv\Scripts\python -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Falló la instalación' }
.\.venv\Scripts\python -B scripts/audit_csv_sources.py --source-dir data/raw
if ($LASTEXITCODE -ne 0) { throw 'Originales o código no coinciden; detener reconstrucción' }
.\.venv\Scripts\python -B scripts/run_ingest.py
if ($LASTEXITCODE -ne 0) { throw 'Falló la ingesta' }
.\.venv\Scripts\python -B scripts/build_panel.py
if ($LASTEXITCODE -ne 0) { throw 'Falló el panel' }
.\.venv\Scripts\python -B scripts/build_lookup.py
if ($LASTEXITCODE -ne 0) { throw 'Falló el catálogo' }
Set-Location -LiteralPath $sourceRepo
```

Revisar también que la creación del entorno y la instalación terminen correctamente
antes de ejecutar scripts. Registrar Python, dependencias instaladas y commit:
`python --version`, `.\.venv\Scripts\python -m pip freeze`, `git rev-parse HEAD`
(este último en el repositorio fuente, pues el archivo no contiene `.git`). Las
dependencias tienen mínimos en `pyproject.toml`, no un bloqueo de versiones; esto
no garantiza identidad binaria de Parquet ni reproducción exacta de modelos.

| Script existente | Salidas que escribe en la copia aislada |
|---|---|
| run_ingest.py | data/interim/eventos_validos.parquet y reports/ingest_report.json |
| build_panel.py | data/processed/panel_casos.parquet, panel_muertes.parquet, configs/series_seleccionadas.csv y reports/ingest_report.json |
| build_lookup.py | data/processed/municipios.csv y reports/ingest_report.json |

`configs/split.json` se toma de la revisión del código; esos scripts no recalculan
un calendario nuevo. Los originales se leen sin modificarlos. La auditoría inicial
debe ejecutarse antes de regenerar el reporte de la copia, para compararse con el
reporte versionado de referencia. No se ejecutaron estos comandos en esta tarea.

## 5. Criterios del Issue #2 y evidencia restante

| Criterio | Evaluación documental actual |
|---|---|
| Huella, fuente, fecha y condiciones | Huellas ya verificadas; fuente oficial identificada; fecha de descarga comunicada por el responsable; licencia actual verificada. |
| Evidencia verificable | Manifiesto, metadatos selectivos y resultados previos documentados: 82 pruebas y 25 controles verdaderos. El historial personal no fue inspeccionado ni versionado. |
| Instrucciones, decisiones y límites | Auditoría y reconstrucción desde copias conservadas documentadas; nueva extracción diferenciada; filtros históricos exactos no acreditados. |

Veredicto: cumple la reproducción del procesamiento desde los originales recuperados
e identificados; no acredita recuperación histórica exacta desde el portal para un
tercero sin esas copias. B02 puede presentarse con ese alcance explícito, pero no se
afirma cumplimiento íntegro e incondicional de trazabilidad histórica.

Para cerrar sin esa reserva: acordar y registrar un resguardo histórico accesible al
equipo, referenciar evidencia no sensible de la descarga y recuperar la consulta u
opciones antiguas (o dejar aceptada expresamente la limitación de reexportación).
No atribuir estas reservas de B02 a B03. No se ha actualizado ni cerrado el Issue.
