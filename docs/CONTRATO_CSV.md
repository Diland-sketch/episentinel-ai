# Contrato CSV v1 — incremento B01/B02

Alcance autorizado por Diland: lectura, normalización conservadora y auditoría.
No cambia el pipeline heredado ni ratifica decisiones epidemiológicas de B03.

## Entrada canónica

UTF-8, BOM opcional, delimitador coma, comillas dobles, LF o CRLF.
Encabezados exactos y únicos, en cualquier orden. No se permiten columnas extra,
ni archivo vacío o solo encabezado. Los errores bloquean el archivo completo.

| Campo obligatorio | Regla |
|---|---|
| cod_mun | Texto de cinco dígitos, con ceros iniciales. Solo candidato municipal. |
| ano | Cuatro dígitos; entero 1000–9999. No se limita a 2007–2022. |
| semana | Entero 1–53. Validez de la pareja año/semana pendiente de calendario. |
| cod_eve | Entero 210, 220 o 580; se conservan separados. |
| conteo | Entero no negativo. Cero explícito se conserva. |

No hay campos opcionales en esta primera versión. Nombres y etiquetas se
conservan en el adaptador histórico, no se añaden al esquema canónico.
No se aceptan espacios, signos, decimales, miles ni notación científica en
campos numéricos canónicos. No se redondea ni corrige ningún código.

Ejemplo sintético:

```csv
cod_mun,ano,semana,cod_eve,conteo
05001,2020,53,210,0
05001,2021,1,210,2
```

Clave: `(cod_mun, ano, semana, cod_eve)`. Toda repetición, idéntica o
conflictiva, produce error en cada registro involucrado. No se suma ni elimina:
los registros parseados quedan en `parsed`, fuera de las particiones utilizables.
La detección es dentro de cada archivo. No concatenar cargas sin volver a validar
la clave del conjunto resultante.

## API y reporte

- `read_canonical(path)` en `episentinel.data.csv_contract`.
- `audit_sivigila(path, expected_event)` en `episentinel.data.sivigila_adapter`.

Ambas devuelven `AuditResult`: `source`, `sha256`, `rows_read`, `candidates`,
`special`, `parsed`, `issues` y propiedad `blocked`. Una lista de candidatos
no autoriza la ejecución: el consumidor debe comprobar `blocked` primero.
Las particiones son para revisión si el archivo está bloqueado. No se publica
una carga parcial. Errores de acceso al archivo se propagan como errores de E/S.

Cada incidencia contiene `source, record, column, value, code, reason, severity`.
`record` es el ordinal lógico CSV, con encabezado = 1 y primer dato = 2;
no es número de línea física si un campo entre comillas contiene saltos.
Errores de archivo usan localización nula. `rows_read` cuenta registros completos
leídos, incluidos los de ancho incorrecto, no bytes ni líneas físicas.
`parsed` conserva registros convertibles, incluso eventos ajenos y duplicados;
los errores de conversión se conservan en incidencias con valor de origen.
`column` usa el encabezado real de la fuente: `cod_eve` en canónico y `COD_EVE`
en histórico. Un evento ajeno produce una sola incidencia `unexpected_event`;
varias causas independientes pueden generar varias incidencias en el mismo registro.
El script separa `issue_counts` (incidencias por código) y `records_with_issues`
(registros lógicos afectados). Los eventos admitidos comparten la constante `EVENTS`.
El adaptador usa helpers públicos del validador; los nombres privados anteriores
permanecen como alias de compatibilidad, sin modificar sus consumidores.

## Adaptador histórico

Acepta exactamente los nueve encabezados originales:
`COD_EVE,Nombre_evento,SEMANA,ANO,COD_DPTO_O,COD_MUN_O,Departamento_ocurrencia,Municipio_ocurrencia,conteo`.

Interpreta enteros simples o miles bien agrupados (`"2,013"`, `"68,320"`).
Si el municipio es local (<1000), construye departamento × 1000 + municipio;
si es completo, verifica coincidencia con departamento. Conserva nombres,
archivo, registro, año, semana y evento. El evento debe coincidir con el declarado
para el archivo; los ajenos quedan trazables y bloquean la carga.

| Clasificación | Regla sintáctica | Destino |
|---|---|---|
| unknown_origin | 00000 | special |
| exterior_unknown | 01000 | special |
| exterior | prefijo 01 y municipio distinto de 000 | special |
| unknown_municipality | otros códigos terminados en 000 | special |
| municipal_candidate | resto de códigos de cinco dígitos | candidates |

La clasificación no acredita existencia o vigencia DIVIPOLA. Se requiere catálogo
oficial versionado en B03. El lector canónico bloquea territorios especiales;
el adaptador los separa sin llamarlos municipios ni descartarlos. No agrega
registros desconocidos a departamentos o nación.

## Métodos analíticos: implementación y disponibilidad

Ningún método analítico está disponible aún para CSV cargados por el usuario.
Este incremento ofrece lectura y auditoría; no existe conexión desde los nuevos
lectores al dashboard ni a modelos. Streamlit consume el panel histórico en disco.
La integración de cargas pertenece a incrementos posteriores, no a esta corrección.

| Método | Implementación existente | Disponible para carga CSV | Pendiente de integración | Restricciones verificadas en código |
|---|---|---|---|---|
| Último valor | `baselines/ingenua_estacional.py:pronosticar_ultimo_valor`; usado por dashboard | No | Serie normalizada y servicio B06; flujo de carga posterior | Accede al último valor e índice: necesita serie no vacía, sin validación explícita. No valida faltantes; si el último valor es faltante, lo replica. Sin intervalo. |
| Ingenua estacional | `baselines/ingenua_estacional.py:pronosticar_ingenua_estacional`; usado por dashboard | No | B06 y flujo de carga posterior | Exige `len(train) >= m`, por defecto 52 observaciones; genera fechas cada 7 días. No verifica cobertura ni faltantes y puede replicarlos. Sin intervalo. |
| SARIMA, con/sin estacionalidad | `models/sarima.py:ajustar_sarima, pronosticar`; usado por dashboard | No | B06 y flujo de carga posterior | Usa `log1p`; estacionalidad por defecto 52, desactivable. No establece mínimo histórico ni política de faltantes en el envoltorio. Produce `yhat, lo, hi`, alpha=0,05 por defecto. Convergencia/series aptas por validar en B06. |
| Canal endémico | `baselines/canal_endemico.py`; usado en alertas históricas | No | Calendario/cobertura B03 y servicio/flujo posterior | Año/semana por posición de 52 observaciones. Referencia por defecto 5 años y máscara `min_anios=2`; no equivale a garantía de cobertura completa. No hay validación general de faltantes. |
| EARS C2 semanal | `detection/alertas.py:ears_c2`; usado en alertas históricas | No | Servicio y flujo posterior | Base=7, guard=2; ventana desplazada 3 posiciones: primer z posible en observación 10 si la ventana está completa. Faltantes dejan z indefinido y comparaciones falsas; no existe estado explícito de insuficiencia. |
| SARIMA un paso y semáforo combinado | `detection/alertas.py:alertas_sarima_un_paso, tabla_alertas, semaforo` | No | Servicio y flujo posterior | Requiere corte `train_end`; combina SARIMA, EARS y canal. No define mínimo histórico operativo. El semáforo rellena indicadores faltantes con falso; no valida brotes reales. |
| Prophet | No hay módulo de implementación en el árbol revisado; aparece como dependencia opcional | No | Implementación y eventual integración, fuera de este incremento | Sin requisitos operativos verificados; no se promete longitud mínima, manejo de faltantes ni disponibilidad. |

La existencia de funciones o de una opción histórica en Streamlit no acredita
soporte para nuevos CSV. Los límites anteriores describen código inspeccionado,
no una aprobación epidemiológica ni resultados de nuevos experimentos analíticos.

## Semántica pendiente de B03

- Calendario oficial, significado de semana (ocurrencia/notificación) y fechas.
- S53 en modelos y periodos estacionales. La entrada conserva S53.
- Cobertura: ninguna fila ausente se transforma en cero. No hay ceros explícitos
  en los tres originales auditados. Una serie temporal completa aún no se produce.
- Comparabilidad y posible solapamiento 210/220. 580 permanece separado.
- Agregados con municipio desconocido y Exterior; catálogo territorial histórico.
- Política de revisiones y duplicados futuros. No hay fecha de revisión por fila.
- Elegibilidad de series por método para B06.

## Verificación reproducible

Desde la raíz del repositorio, con Python y pytest disponibles:

```powershell
.\.venv\Scripts\python -m pytest tests/test_csv_contract.py tests/test_sivigila_adapter.py -q
.\.venv\Scripts\python scripts/audit_csv_sources.py --source-dir "C:\Users\dilan\Downloads"
```

La segunda orden lee los originales y `reports/ingest_report.json`, imprime JSON
y devuelve 0 si coinciden las huellas, controles por fuente y reporte completo.
También comprueba, por fuente, conservación de registros y suma de conteos entre
candidatos, especiales y eventos ajenos; identidad única sin solapamientos;
correspondencia de valores con registros parseados; clasificación territorial
independiente del adaptador, y cantidades/sumas esperadas por categoría.
Si hay registros no convertibles o no asignados, falla la conservación completa.
No interpreta esos registros como ceros.

Devuelve 0 solo si todos los controles pasan, 1 ante discrepancias de integridad,
huellas, categorías o reporte, y 2 ante errores de acceso/lectura de archivos o JSON
del reporte (también argumentos inválidos de CLI). `historical_discrepancies`
expone los valores calculados y guardados que difieren.
No escribe archivos ni regenera el reporte.
`blocked: true` en fuentes originales es esperado por los 22 eventos ajenos:
que la conciliación pase no habilita esos archivos para el pipeline.

`legacy_comparison_only` reproduce la aceptación histórica: incluye Exterior y
excluye municipio desconocido. Es una comparación, no una política aprobada nueva.
No se ejecutan modelos ni se recalculan sus métricas.

Cifras históricas: 1.194.662 = 1.193.088 casos 210+220 + 1.574 muertes;
1.186.504 = 1.184.953 casos con municipio específico (incluye Exterior) + 1.551
muertes. Ambas sumas mezclan indicadores. No se han corregido reportes históricos.


## Evidencia de validación — ejecuciones diferenciadas

### Ejecución inicial de Codex, 2026-11-11

- Rama de trabajo: `feat/b01-b02-csv-audit`; sin commits de este incremento.
- Python 3.13.4; pytest 9.2.0 en `.venv` local (con paquetes del sistema).
- Pruebas nuevas: 36 aprobadas.
- Suite completa: 64 aprobadas, 2 omitidas. Las omitidas son las de ingesta
  heredada, que buscan originales dentro de `data/raw`; no se copiaron allí.
- Comprobación independiente en Downloads: tres huellas coincidentes y todos
  los campos de `ingest_report.json` coincidentes. Se leyeron 223.651 registros.
- Comparación heredada: 219.083 registros aceptados, 1.184.953 casos 210+220,
  1.551 muertes y 696 registros S53. No es una selección epidemiológica nueva.
- Partición conservadora: 218.063 registros municipales candidatos, 5.566
  territoriales especiales y 22 eventos ajenos (sin pérdida de registros).
- Los 22 ajenos generan incidencias bloqueantes, no se reclasifican como dengue.
- No se escribieron originales, reportes históricos, paneles ni resultados de modelos.
- Las pruebas sintéticas crean archivos temporales; no incorporan datos reales a Git.

Para ejecutar toda la suite en el entorno preparado:

```powershell
.\.venv\Scripts\python -m pytest -q
```

Las decisiones pendientes de B03 no se consideran cerradas por pasar estas pruebas.


### Revisión independiente de OpenCode, 2026-11-11

Datos transcritos del informe de revisión aportado por Diland; no son una ejecución
realizada por Codex en esta segunda iteración:

- Proyecto original `C:\Proyecto IA\episentinel-ai`; Python 3.13.4, pytest 9.1.1.
- 36 pruebas nuevas aprobadas; suite completa 66 aprobadas, 0 omitidas.
- Originales disponibles en `data/raw`, ignorados por Git; auditoría con salida 0.
- El informe registra cuatro controles verdaderos de la primera versión del script.

La ejecución inicial anterior usó un clon sin originales en `data/raw`, pytest
9.2.0 y auditoría separada en Downloads. Eso explica sus dos omisiones; no son
resultados intercambiables. Tras trasladar el incremento al proyecto original,
Codex también ejecutó 66 pruebas sin omisiones, antes de esta segunda iteración.

### Estado de preparación

Este incremento es parcial respecto de los Issues: no cierra B01/B02 ni autoriza
la integración del CSV a métodos. B02 sigue abierto por procedencia pendiente
propia, no por depender de B03. La matriz delimita los métodos de B01; no declara
integraciones futuras como disponibles. El pipeline heredado aún tiene plegado,
fechas posicionales y relleno de ceros: las garantías conservadoras corresponden
solo a los módulos nuevos. Que sus pruebas heredadas pasen no ratifica esa política.


### Segunda iteración ejecutada por Codex, 2026-11-11

Proyecto original `C:\Proyecto IA\episentinel-ai`, rama
`feat/b01-b02-csv-audit`, Python 3.13.4, pytest 9.1.1. Originales disponibles
localmente en `data/raw`, ignorados por Git.

```powershell
.\.venv\Scripts\python -B -m pytest tests/test_csv_contract.py tests/test_sivigila_adapter.py tests/test_audit_csv_sources.py -q -p no:cacheprovider
.\.venv\Scripts\python -B -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python -B scripts/audit_csv_sources.py --source-dir data/raw
git diff --check
```

- Módulos modificados: **52 aprobadas**, 0 omitidas.
- Suite completa: **82 aprobadas**, 0 omitidas.
- Auditoría original: 25 controles verdaderos; salida 0; sin discrepancias con
  el reporte histórico. Tres huellas coincidentes.
- Conservación comprobada: 218.063 candidatos + 5.566 especiales + 22 ajenos
  = 223.651 registros, sin solapamientos. También se conserva la suma de conteos.
- Incidencias de eventos ajenos: 22, una por registro, con columna `COD_EVE`.
- Fallos sintéticos probados: intercambio municipal/Exterior, solapamiento,
  pérdida de registro, alteración de conteo, discrepancia histórica, cambio de
  huella, fila no convertible, CSV truncado, fuente ausente y JSON inválido.
- CLI: salida 0 ante coincidencia; 1 ante discrepancia; 2 ante error de entrada.
- `git diff --check`: sin errores; archivos nuevos revisados además sin espacios
  finales. No se modificaron originales, pipeline, interfaz ni reportes existentes.

Resultado: preparado técnicamente para revisión de commit/PR como avance parcial,
sin cierre automático de Issues. La procedencia institucional pendiente mantiene
B02 abierto independientemente de las pruebas y de B03.
