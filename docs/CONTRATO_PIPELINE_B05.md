# B05-I1 — pipeline aislado de carga y construcción de series

Base inspeccionada: `eacbdc6c7e494887486f7411f159579b6b779f75` (B04 y B03-I1
integrados). `main`, `origin/main` y la rama de trabajo coincidían en esa revisión;
no fue necesaria una actualización fast-forward. Rama: `feat/b05-isolated-pipeline`.

## Fachada pública

Módulo `episentinel.services.isolated_pipeline`:

```python
run_pipeline(
    source: str | PathLike | bytes | BinaryIO,
    *,
    config: PipelineConfig,
    source_name: str | None = None,
) -> PipelineResult
```

`PipelineConfig(version, territory, event_codes, period_grid)` recibe identidad
`MunicipalIdentity` y malla `PeriodGrid` de B03; la malla contiene `CalendarMetadata`
con identificador, versión, procedencia y verificación. `version` identifica la
configuración completa de esta ejecución y debe ser texto no vacío.

La selección de eventos es una tupla explícita (se admite lista y se copia a tupla).
Las reglas de identidad, periodos, eventos y cobertura se delegan a B03. No existe
un lector de configuración JSON/YAML en I1. B05-I2 podrá suministrar estos objetos
desde una configuración versionada sin pedir al usuario final construir la malla.

## Secuencia y garantías

1. Comprueba el tipo de configuración, su versión y el contenedor de selección.
   Una configuración inválida en este límite se bloquea sin consumir la fuente.
2. Invoca una vez la API real de B04:
   `load_csv(source, source_name=source_name)`. No repite su validador.
3. Si B04 bloquea o informa errores, termina sin invocar B03. El diagnóstico puede
   contener los valores de error de B04, pero no se exponen observaciones crudas.
4. Con carga aceptada, invoca una vez la API real de B03:
   `build_series(data, territory=..., event_codes=..., period_grid=...)`.
   Entrega una copia de los datos cargados para evitar mutación compartida.
5. Solo devuelve `SeriesBundle` después de finalizar correctamente esa construcción.
   Un error de configuración detectado por B03 también impide devolver series.

No hay rutas fijas, almacenamiento, descarga, creación de temporales, paneles,
reportes, Streamlit, modelos ni señales. No se modificaron las APIs B01/B02/B03/B04.
No hay nuevas dependencias. Los archivos de entrada se leen; no se normalizan en disco.

Un flujo binario conserva exactamente el comportamiento de B04: se lee desde su
posición actual hasta EOF, sin cerrarlo ni restaurar el cursor. Esto es consumo de
entrada, no una mutación de su contenido. Los bytes son inmutables; los registros,
reportes y configuración devueltos por los módulos se copian para evitar alias con
el resultado. Las dataclasses son congeladas; el diagnóstico contiene diccionarios
copiados que un consumidor puede editar sin afectar a B04.

## Resultado y estados

| Campo de PipelineResult | Contenido |
|---|---|
| status | `completed`, `blocked` o `failed` |
| config | Instantánea de la configuración recibida cuando es representable; `None` ante tipo/contenedor inválido. Solo se aplica a series si termina `completed` |
| load_diagnostic | Fuente, SHA-256, versión del contrato, bloqueo, reporte y decisiones pendientes de B04; sin atributo `data`. Puede ser `None` si no se llegó a cargar |
| series | `SeriesBundle` completo o `None`; contiene identidad, selección, cobertura, trazabilidad y metadatos de malla |
| warnings | Tupla de PipelineIssue: advertencias de B04 y avisos por evento sobre cobertura, ausencia total y elegibilidad no evaluada |
| errors | Tupla de PipelineIssue con etapa, código, motivo y localización disponible |

- `completed`: carga y construcción estructural terminadas. Puede haber faltantes
  o eventos sin observaciones; esto produce advertencias, no una afirmación de
  elegibilidad. Se mantienen todos sus puntos ausentes y su total observado `None`.
- `blocked`: rechazo de CSV o reglas/configuración B03. Nunca contiene series
  parciales, aunque el diagnóstico indique registros parseados durante la carga.
- `failed`: error de acceso/tipo de fuente conocido por B04 o una carga aceptada
  sin datos (invariante defensiva). No contiene series.

`PipelineIssue` incluye `stage`, `code`, `reason` y, según la causa, `source`,
`record`, `column`, `input_position`, `event_code`. Se conservan los códigos de B04
y B03; las etapas de B05 son `configuration`, `load` y `series`.
Errores inesperados de programación se propagan: no se disfrazan como CSV inválido.

Los avisos de B04 se conservan aunque mencionen decisiones B03 pendientes; B03-I1
no ha resuelto calendario oficial, política analítica S53 ni cobertura epidemiológica.
Una carga coincidente o una malla completa no acredita notificación completa.

## Ejemplo mínimo ejecutable

Con el paquete instalado en el entorno (`pip install -e .`):

```python
from episentinel.data.epidemiological_series import (
    CalendarMetadata, MunicipalIdentity, PeriodGrid,
)
from episentinel.services.isolated_pipeline import PipelineConfig, run_pipeline

config = PipelineConfig(
    version="demo-v1",
    territory=MunicipalIdentity("05001"),
    event_codes=(210, 220, 580),
    period_grid=PeriodGrid(
        ((2020, 52), (2020, 53), (2021, 1)),
        CalendarMetadata("demo-grid", "v1", "ejemplo sintético"),
    ),
)
csv_bytes = (
    "cod_mun,ano,semana,cod_eve,conteo\n"
    "05001,2020,52,210,0\n"
    "05001,2020,53,210,5\n"
).encode("utf-8")
result = run_pipeline(csv_bytes, config=config, source_name="demo.csv")
assert result.status == "completed"
assert not result.errors
assert [p.observed_count for p in result.series.series[0].points] == [0, 5, None]
assert [p.observed_count for p in result.series.series[1].points] == [None, None, None]
assert result.series.series[0].eligibility.status == "not_evaluated"
print(result.status)
```

La misma API acepta una ruta o un flujo binario. No llama modelos, no suma eventos,
no imputa, no fecha periodos, no declara oficialmente válida una S53 y no valida
DIVIPOLA por su cuenta. S53 permanece independiente si la malla la declara; un
registro seleccionado fuera de la malla bloquea sin recorte silencioso.

## Pruebas y alcance del incremento

```powershell
.\.venv\Scripts\python -B -m pytest tests/test_isolated_pipeline.py -q -p no:cacheprovider
.\.venv\Scripts\python -B -m pytest -q -p no:cacheprovider
git diff --check
```

Las pruebas sintéticas incluyen fuentes por ruta/bytes/flujo, identidad y eventos
explícitos, errores bloqueantes y duplicados, ceros/ausencias, S53/cambio de año,
configuración inválida, ausencia total, trazabilidad y llamadas únicas a B04/B03.
También comprueban no mutación y apertura solo de lectura sobre archivos sintéticos
con sentinelas de panel/reporte. No se ejecuta una auditoría general de originales.

B05-I1 satisface el recorrido carga → series; no cierra todo el Issue #5, cuyo
pipeline integrado con resultados posteriores corresponde a incrementos siguientes.

## Dependencias siguientes

- **B05-I2:** acordar entradas/salidas concretas de B06/B07 y la configuración
  versionada de ejecución; decidir cualquier persistencia aislada antes de añadirla.
- **B06/B07:** verificar sus APIs reales, métodos y requisitos de frecuencia,
  fechas, cobertura e históricos mínimos. Reciben una serie por evento; no se
  eliminan faltantes ni se declara elegibilidad desde esta fachada.
- **B03-I2:** aportar evidencia de calendario/catálogos o políticas analíticas
  requeridas por esos métodos. No sustituirla con ISO ni malla posicional.
- **B08:** consumir estados, diagnóstico y advertencias sin lógica epidemiológica
  propia. En `blocked`/`failed` no hay series para mostrar como resultados.


## Evidencia ejecutada de B05-I1

- Pruebas específicas: **32 aprobadas**, ninguna omitida (0,29 s).
- Suite completa: **214 aprobadas**, ninguna omitida (14,77 s).
- Ejemplo de este documento ejecutado con sus aserciones: imprime `completed`.
- `git diff --check`: sin errores. Archivos nuevos comprobados además mediante
  compilación Python y revisión de espacios finales.
- Cuatro archivos nuevos: servicio, inicializador de paquete, pruebas y este contrato.
  Ningún archivo existente fue modificado; sin dependencias nuevas.
- No se recalcularon reportes ni paneles, no se ejecutaron modelos y no se realizó
  una auditoría general de originales. Las pruebas de no escritura usan sentinelas
  sintéticos; no se añaden originales al repositorio.
- Preparado para revisión de commit/PR de I1. No se realizaron commits, push, PR ni
  cierres de Issues; las conexiones analíticas posteriores siguen pendientes.
