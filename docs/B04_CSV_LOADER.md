# B04: contrato público de carga CSV

```python
from episentinel.data.csv_loader import CsvLoadResult, load_csv

result = load_csv(source, source_name="carga.csv")
if result.blocked:
    errors = result.report["errors"]  # result.data es None
else:
    observations = result.data
    # B05 debe verificar condiciones B03 y requisitos del método por separado.
```

`source` admite ruta (`str` o `os.PathLike`), `bytes` y flujo binario con
`read()` que devuelve bytes, incluido `BytesIO`. No admite contenido CSV como
texto ni flujos de texto. Los flujos se consumen desde su posición actual hasta
EOF y quedan abiertos; para repetir una carga, el llamador debe reposicionarlos.
Los errores de E/S se propagan (por ejemplo, `FileNotFoundError` u `OSError`).
Los tipos no admitidos producen `TypeError`; `source_name` debe ser `str` o
`None` y se valida antes de leer la entrada. También se propaga `ValueError`
al leer un flujo cerrado o al utilizar rutas inválidas, por ejemplo con un
carácter NUL. Estas excepciones no se convierten en un reporte de carga.
Los errores del contenido CSV se devuelven en el resultado.

Se reutiliza el validador canónico de B01, sin detección automática del formato
histórico ni cambios en sus reglas. `read_canonical(path)` y el adaptador
SIVIGILA conservan sus interfaces por ruta. El lector compartido y
`read_canonical` aceptan además bytes y `source_name` opcional.

## Resultado

`CsvLoadResult` contiene:

- `data`: lista de observaciones normalizadas en el orden de entrada; `None`
  si cualquier error bloquea el archivo. No entrega subconjuntos utilizables
  de una carga bloqueada.
- `report`: diccionario serializable con `errors`, `warnings` y `summary`.
- `blocked`: rechazo completo por errores del contrato CSV.
- `pending_decisions`: lista informativa y no exhaustiva de objetos
  `code, reason` con pendientes B03.
- `source`: nombre explícito, nombre de archivo sin directorio o `<memory>`.
- `sha256`: huella exacta de los bytes recibidos, incluido BOM y saltos de línea;
  para flujos, corresponde a los bytes leídos desde la posición inicial de carga.
- `contract_version`: `"1"`, correspondiente a `CONTRATO_CSV.md` v1.

Cada observación conserva los cinco campos canónicos: `cod_mun` como texto de
cinco dígitos y `ano, semana, cod_eve, conteo` como enteros. Incluye también
`source`, `record` y la clasificación sintáctica `territory` de B01.
`municipal_candidate` no certifica existencia ni vigencia DIVIPOLA.

Cada incidencia conserva `source, record, column, value, code, reason, severity`.
`record` es el ordinal lógico CSV (encabezado = 1), no necesariamente la línea
física. Los errores de archivo y advertencias generales pueden tener fila o
columna nulas, conforme al diagnóstico de B01.

El resumen informa `rows_read`, `rows_parsed`, `municipal_candidates`,
`special_records`, `rows_delivered`, `records_with_errors`, `error_count` y
`warning_count`. Los candidatos son diagnósticos; solo `rows_delivered` representa
la entrega autorizada por el validador. `rows_read` cuenta registros completos
leídos, no permite inferir cuántos registros había después de un CSV truncado.
Los errores de archivo sin fila no aumentan `records_with_errors`.

## Pendientes y garantías para B05

Toda carga expresa como advertencias informativas estos pendientes B03:
`calendar`, `week_53`, `coverage`, `territory` y `event_comparability`.
Esta lista no agota las decisiones B03. También siguen pendientes la política
de revisiones y duplicados futuros y la ausencia de fecha de revisión por fila,
descritas en [Contrato CSV v1: Semántica pendiente de B03](CONTRATO_CSV.md#semántica-pendiente-de-b03).
No se implementan esas políticas en este incremento.
No cambian las reglas bloqueantes de B01: los territorios especiales siguen
bloqueando la entrada canónica y los duplicados no se suman ni eliminan.

La carga conserva S53, ceros iniciales, ceros observados y eventos separados.
No genera fechas, no crea filas para semanas ausentes y no rellena ceros.
La ausencia permanece sin observación; su significado y cobertura esperada
requieren las decisiones B03. `blocked=False` solo acredita el contrato CSV;
no acredita cobertura, calendario, elegibilidad para modelos ni brotes.

No escribe archivos ni modifica paneles, originales o reportes. B05 debe recibir
`data` únicamente tras comprobar `blocked`; B07 y Streamlit quedan fuera de
este incremento.

## Verificación

Desde la raíz, con las dependencias de desarrollo instaladas:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_csv_loader.py tests/test_csv_contract.py tests/test_sivigila_adapter.py tests/test_audit_csv_sources.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Ejecución de este incremento: Python 3.12.5 y pytest 9.2.0 en `.venv` local.
Tras los ajustes H1–H3: **48 pruebas B04 aprobadas** (incluidos cinco casos
de regresión de `source_name`) y **52 pruebas de regresión B01/B02 aprobadas**.
Suite completa: **130 aprobadas**, sin omisiones. La suite incluye una
comprobación de integridad de originales y reportes antes/después de la carga.
Estos resultados validan software y compatibilidad; no resuelven B03.
