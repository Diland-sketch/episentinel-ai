# B03-I1 — contrato de series por periodos explícitos

Decisiones A–E aprobadas por Diland para este incremento: malla explícita con
procedencia, candidatos municipales, eventos separados, errores bloqueantes y
faltantes explícitos, elegibilidad no evaluada. Son reglas del módulo nuevo;
no cambian ni ratifican el comportamiento del pipeline histórico.

## Interfaz pública

Módulo: `episentinel.data.epidemiological_series`.

```python
build_series(
    observations: Iterable[Mapping[str, object]],
    *,
    territory: MunicipalIdentity,
    event_codes: Iterable[int],
    period_grid: PeriodGrid,
) -> SeriesBundle
```

Es una función pura: sin lectura/escritura de archivos, fechas, agregados,
imputaciones, modelos ni modificaciones de registros de entrada. Las salidas son
dataclasses congeladas con colecciones inmutables. No usa APIs privadas del lector.

- `MunicipalIdentity(code)`: texto de cinco dígitos; rechaza `00000`, prefijo `01`
  y códigos terminados en `000` como identidades municipales. La clasificación
  sintáctica reutiliza `classify_territory`; `catalog_validation` siempre es `pending`
  en I1. Un código candidato desconocido no se rechaza por ausencia de DIVIPOLA.
- `CalendarMetadata(calendar_id, version, source, verification="unverified", evidence=None)`:
  identificador, versión y procedencia no vacíos. Acepta estados `unverified` o
  `verified`; el segundo exige referencia de evidencia. Esta es una declaración
  del proveedor de la malla, no una verificación institucional realizada por B03.
- `PeriodGrid(periods, metadata)`: tupla o lista explícita, no vacía, de pares
  `(ano, semana)`, únicos y estrictamente ordenados. Año entero 1000–9999 y semana
  entera 1–53, sin booleanos ni conversiones desde texto o fracciones. Se copia
  a tuplas, sin modificar ni retener las listas mutables suministradas.

No se valida oficialmente la existencia de una S53 por año. No se infieren semanas
intermedias, años completos ni fechas con ISO, 52 posiciones u otra heurística.
B05 podrá suministrar la malla y sus metadatos desde **configuración versionada**;
no se exige que el usuario final construya la malla manualmente. I1 no implementa
lectura de configuración ni descarga/calendario oficial.

## Observaciones, selección e integridad

Cada observación debe contener los campos normalizados `cod_mun, ano, semana,
cod_eve, conteo`. Los enteros no negativos se aceptan sin redondear, también tipos
compatibles con `numbers.Integral`; booleanos, fracciones y texto se rechazan.
`source` y `record` son opcionales: si existen, fuente no vacía y registro entero
positivo. En todo caso se conserva una posición de entrada de base 1.

El consumidor debe haber comprobado previamente el resultado de B04; esta API no
puede comprobar por sí sola el estado de una fachada que aún no está integrada.
Revalida los invariantes de toda la colección recibida, no repara sus errores.

Clave única: `(cod_mun, cod_eve, (ano, semana))`, independientemente de archivo o
número de registro. Una duplicación idéntica o conflictiva bloquea toda la operación,
incluso en observaciones fuera de la selección. No se escoge versión ni se suman.

Solo se seleccionan la identidad territorial y los eventos solicitados. Las demás
observaciones permanecen intactas y se contabilizan como no seleccionadas. Un
registro territorial especial fuera de la selección no se convierte en municipio.
Las observaciones seleccionadas fuera de la malla bloquean; no se recortan.

Los eventos permitidos reutilizan `EVENTS` del contrato canónico: 210, 220 y 580.
La selección debe ser explícita, no vacía y sin repeticiones. Se conserva su orden.
Seleccionar varios devuelve series independientes; no prueba ausencia de solapamiento
ni calcula 210+220. No hay agregados departamentales o nacionales.

`SeriesValidationError(ValueError)` incluye `code` e `input_position` cuando el
error afecta una observación. Un error de configuración puede carecer de posición.
No se devuelve un resultado parcial con integridad fallida.

## Resultado

`SeriesBundle` contiene:

| Campo | Significado |
|---|---|
| structural_integrity | `valid` solo al terminar todas las validaciones; no es validez epidemiológica |
| territory | Identidad candidata con catálogo pendiente |
| grid | Periodos y metadatos declarados, sin fechas |
| event_codes | Selección explícita |
| series | Una `EventSeries` por evento, en el orden seleccionado |
| selection | Registros de entrada, seleccionados y no seleccionados; su conservación es comprobable |

Cada `EventSeries` contiene `event_code`, `points`, `coverage`, `eligibility`:

- Un `SeriesPoint` por periodo declarado: `period`, `observed_count`,
  `observation_status` y `source_refs`.
- Observado: conteo entero, incluso cero, estado `observed`, referencia con
  `input_position`, `source` y `record`. No se modifica el número de registro de origen.
- Ausente: `observed_count=None`, estado `missing`, referencias vacías. No se agrega
  una observación fuente ni se convierte ausencia en cero.
- `observed_total` es una suma **diagnóstica de observaciones de un solo evento**,
  no un total epidemiológico completo. Devuelve `None` si no hay observaciones;
  devuelve cero si existen observaciones explícitas cuyo conteo es cero.
- Cobertura: número de periodos esperados/observados, tupla de periodos ausentes y
  verificación declarada del calendario. Estados `complete_in_declared_grid` o
  `incomplete_in_declared_grid`. No acredita continuidad fuera de esa malla,
  notificación completa, ausencia de subregistro ni año epidemiológico válido.
- Elegibilidad: siempre `not_evaluated`. Razones: `method_not_evaluated`,
  `dates_unassigned`, `territorial_catalog_pending`; se agregan `calendar_unverified`
  y `missing_observations` cuando corresponda. No son umbrales de rechazo de modelos.

Una colección sin observaciones produce series completamente ausentes, integridad
estructural válida y elegibilidad no evaluada. Nunca se convierte en una serie cero.

## Ejemplo mínimo ejecutable

Desde un entorno con el paquete instalado (`pip install -e .`), ejecutar este código:

```python
from episentinel.data.epidemiological_series import (
    CalendarMetadata, MunicipalIdentity, PeriodGrid, build_series,
)

grid = PeriodGrid(
    ((2020, 52), (2020, 53), (2021, 1)),
    CalendarMetadata("example-grid", "v1", "ejemplo sintético"),
)
result = build_series(
    [dict(cod_mun="05001", ano=2020, semana=52, cod_eve=210,
          conteo=0, source="example.csv", record=2)],
    territory=MunicipalIdentity("05001"),
    event_codes=(210, 220),
    period_grid=grid,
)
assert [p.observed_count for p in result.series[0].points] == [0, None, None]
assert [p.observed_count for p in result.series[1].points] == [None, None, None]
assert result.series[0].eligibility.status == "not_evaluated"
assert result.selection.selected_records == 1
print(result.series[0].coverage.status)
# incomplete_in_declared_grid
```

Este ejemplo no respalda la validez oficial de su calendario sintético.

## Coordinación B04 → B05 → B06/B07

1. B04 mantiene lectura/normalización y errores. B05 debe comprobar que su resultado
   permite continuar antes de entregar observaciones a esta API. No se presupone
   el nombre de la función ni del resultado final de `csv_loader.py`.
2. B05 selecciona territorio/eventos y suministra la malla versionada, con metadatos;
   conserva la salida por evento y los motivos de cobertura/elegibilidad.
3. Antes de B06/B07 se debe verificar su interfaz real y acordar qué formatos de
   periodos y faltantes admiten. I1 no convierte la salida a `pd.Series` fechada,
   no elimina faltantes y no conecta directamente los servicios.
4. Si un método exige calendario, frecuencia o longitud mínima, el servicio o un
   adaptador posterior debe comprobarlo. B03-I1 no declara aptitud por defecto.

## Pendientes B03-I2

- Fuente/versionado de calendario epidemiológico, significado de semana y validación
  año/S53; asignación separada a fechas reales, cuando esté respaldada.
- Catálogo territorial oficial e histórico; tratamiento de especiales en agregados.
- Política de cobertura/faltantes para cada método, sin imputación implícita.
- Semántica de combinaciones de eventos y requisitos reales de B06/B07.
- Ejemplos/cortes históricos recalculados bajo reglas aprobadas. I1 no escribe
  paneles ni reportes ni cierra el criterio completo del Issue #3.

## Verificación

```powershell
.\.venv\Scripts\python -B -m pytest tests/test_epidemiological_series.py -q -p no:cacheprovider
.\.venv\Scripts\python -B -m pytest -q -p no:cacheprovider
git diff --check
```

Las pruebas son sintéticas: límites de año, ausencia de generación de S53,
ceros/faltantes, eventos separados, duplicados multifuente, especiales y candidatos
sin catálogo, errores de malla/datos, conservación de conteos, trazabilidad,
no mutación y estados de cobertura/elegibilidad.


### Evidencia ejecutada — B03-I1, 2026-11-11

- Rama `feat/b03-epidemiological-rules`, proyecto original `C:\Proyecto IA\episentinel-ai`.
- Pruebas específicas: **52 aprobadas**, ninguna omitida (0,20 s).
- Suite completa: **134 aprobadas**, ninguna omitida (18,40 s).
- Ejemplo Python de este documento ejecutado con sus aserciones: correcto;
  imprime `incomplete_in_declared_grid`.
- `git diff --check`: sin errores. Archivos nuevos revisados además mediante
  compilación Python y comprobación de espacios finales.
- Solo los tres archivos autorizados son nuevos; ningún archivo existente cambió.
- No se ejecutó una auditoría general adicional ni se regeneraron paneles/reportes.
- Preparado para revisión de commit/PR del incremento I1; sin commit, push, PR ni
  cierre del Issue. B03 completo sigue pendiente de I2 y sus evidencias.
