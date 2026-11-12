# B07-I1 — servicio de señales por periodos explícitos

## Base y diagnóstico

Rama `feat/b07-signal-service`, creada desde `origin/main` actualizado en
`53716df432e87eee6cebbc5350f8f5a789f4c3f8`. B04, B03-I1 y B05-I1 están
integrados. Los Issues #3, #5, #6 y #7 siguen abiertos en la consulta inicial.
B06 aún no tiene servicio reutilizable en esta base; solo existe el SARIMA
histórico. La modificación local preexistente de `README.md` se conserva.

El servicio histórico `detection/alertas.py` combina booleanos y rellena
indicadores ausentes con falso en su semáforo. El canal deriva año/semana por
bloques de 52 posiciones. B07-I1 no usa ese semáforo ni convierte las series B03
a fechas ficticias. Ambos módulos históricos permanecen intactos.

## Contrato público

Módulo: `episentinel.services.signal_service`.

```python
evaluate_signals(
    bundle: SeriesBundle,
    *,
    ears_config: EarsC2Config | None = None,
    rules: tuple[str, ...] = ("ears_c2", "canal_endemico", "sarima_one_step"),
) -> SignalReport
```

Recibe un `SeriesBundle` estructuralmente válido construido por B03, sin rutas,
fechas, carga CSV ni dependencia de Streamlit. La selección de reglas debe ser
explícita, no vacía y sin repeticiones; se admite lista además de tupla.
Configuración o estructuras inconsistentes producen `TypeError` o `ValueError`,
no resultados negativos silenciosos. B07 comprueba los invariantes necesarios
para evaluar sin reemplazar la validación de B03/B04.

`EarsC2Config(base=7, guard=2, k=3.0, min_sd=1.0, min_casos=3)` conserva los
parámetros de la demostración. Son parámetros numéricos reproducibles, no umbrales
con eficacia epidemiológica validada. `base` debe ser entero >=2 (SD muestral),
`guard` y `min_casos` enteros >=0, `k` finito >=0 y `min_sd` finito >0.
No se aceptan booleanos como parámetros numéricos.

`SignalReport` contiene `contract_version="1"`, metadatos originales de calendario
y `results`, una tupla de evaluaciones en orden evento → periodo → regla.
`dataclasses.asdict(report)` puede serializarse con `json.dumps(..., allow_nan=False)`.
No se produce un estado agregado ni un semáforo.

Cada `SignalEvaluation` incluye:

| Campo | Significado |
|---|---|
| period, event_code, territory_code | Identidad de la evaluación, sin combinar eventos o territorios |
| rule, status | Regla y estado `signal`, `no_signal` o `not_evaluable` |
| observed_count | Conteo observado, incluido cero; `None` conserva ausencia |
| reference | Puntos B03 con periodos, conteos, estado y trazabilidad |
| reference_mean, reference_sd, effective_sd | Referencia numérica calculada y piso aplicado a la SD |
| threshold, score | Umbral de conteo y z de EARS, cuando se puede evaluar |
| reason | Explicación legible del resultado |
| not_evaluable_reason | Código del impedimento, o `None` si se evaluó |
| parameters | Parámetros usados; en integraciones pendientes solo `integration=pending` |

En `not_evaluable`, las estadísticas, umbral y score son `None`; `reference`
puede mostrar los puntos candidatos anteriores disponibles, incluso ausentes.
Esos puntos permiten diagnosticar el impedimento, no representan una referencia
numérica utilizada con éxito. Las dataclasses son congeladas; cada evaluación
recibe su propio diccionario de parámetros. No se modifica el bundle recibido.

## EARS C2 funcional y requisitos

Reutiliza directamente `detection.alertas.ears_c2` para z y decisión, sobre una
ventana local con índice numérico. No se reimplementa el detector. Las reducciones
de media y SD se repiten solo para explicar la referencia con las mismas
operaciones de pandas que el núcleo existente.

Para posición T, la referencia es `[T-guard-base, T-guard)`, excluyendo la
observación T y los `guard` periodos anteriores. Por defecto utiliza siete
observaciones y deja dos periodos de separación. La primera posición evaluable
es la décima observación de una ventana suficiente.

Condiciones de evaluabilidad de I1:

1. T tiene conteo observado.
2. Los metadatos del proveedor declaran calendario `verified` con evidencia.
3. Existen al menos `base + guard` periodos anteriores en la malla.
4. La ventana local completa, incluidos separación y T, pertenece al mismo año y
   sus semanas son consecutivas. No se comprimen saltos ni se decide si un año
   termina en 52 o 53; los cruces de año quedan pendientes.
5. Todos los puntos de la referencia tienen conteo observado y las operaciones
   numéricas son finitas y cumplen la certificación de precisión descrita abajo.

La condición `verified` es la declaración del proveedor definida por B03-I1,
no una certificación institucional realizada por B07. La comprobación local de
consecutividad es un requisito del método, no un calendario oficial nuevo.
La malla `unverified` por defecto de B03 no se habilita automáticamente.

Los faltantes en la separación no participan en la referencia y conservan sus
posiciones. Los faltantes en la referencia impiden evaluarla; nunca se imputan.

`effective_sd = max(SD_muestral, min_sd)`;
`threshold = media + k * effective_sd`;
`score = (observado - media) / effective_sd`.
La decisión del núcleo reutilizado es `score > k` y `observado >= min_casos`.
Exactamente en el umbral no hay señal; se registra `no_signal` solo después de
cumplir todos los requisitos. El piso de SD permite evaluar una serie constante,
incluidos ceros explícitos, sin divisiones por cero. Un score no finito produce
`not_evaluable`, nunca un negativo ni NaN serializable.

## H1: rechazo numérico conservador

Estrategia B: conservar el núcleo EARS existente y rechazar una evaluación cuya
precisión no se pueda certificar. B03/B04 siguen admitiendo enteros grandes; no
se modifica su dominio ni se truncan conteos. El impedimento pertenece a B07.

El defecto original convertía conteos a `float64` antes de restar la media.
`10**20` y `10**20 + 4` pueden convertirse al mismo flotante finito: `isfinite`
no detecta esa pérdida. También se alteraban igualdades de umbral cerca de
`10**16`, provocando falsos positivos además de falsos negativos.

La protección tiene dos etapas:

1. **Antes de convertir enteros:** los conteos utilizados (referencia y T) deben
   ser menores que `2**(sys.float_info.mant_dig - 1)`, es decir, `2**52` para
   binary64 de 53 bits. Desde `2**52` la separación entre flotantes alcanza una
   unidad; ya no queda resolución subunitaria para medias y umbrales fraccionarios.
   Esta frontera proviene de la representación numérica, no de un máximo
   epidemiológico arbitrario. Todos los enteros del dominio admitido se convierten
   exactamente. La región de enteros exactos hasta `2**53` por sí sola no basta
   para garantizar precisión en estadísticas derivadas.
2. **Antes de publicar el resultado:** se calculan media y varianza muestral
   exactas con enteros/Fraction: `mu = sum(x)/n` y
   `v = (n*sum(x*x) - sum(x)**2)/(n*(n-1))`. El piso de varianza es
   `max(v, min_sd**2)`. Los parámetros flotantes se interpretan como sus valores
   binarios exactos ya aceptados por `EarsC2Config`.

La certificación compara mediante fracciones y cuadrados, sin aproximar raíces:
para `Delta = observado - mu >= 0`, el signo de `score-k` coincide con el de
`Delta**2 - k**2 * varianza_efectiva`; los signos negativos se tratan por separado.
Esto comprueba exactamente la comparación estricta, incluida la igualdad y la
condición `min_casos`. La decisión sigue proviniendo del núcleo reutilizado;
la certificación solo la acepta o rechaza, nunca la reemplaza por otro detector.

También se comprueba que cada estadística publicada esté a no más de un flotante
adyacente de su valor matemático, usando `nextafter` y comparaciones exactas.
Todas deben tener `ulp < 1`. El umbral publicado frente al entero observado y el
score publicado frente a k deben conservar exactamente el signo matemático de
la comparación. Estas condiciones comprueban tanto la clasificación como la
coherencia de los números mostrados; la mera finitud no es suficiente.

Si falla cualquiera de estas comprobaciones, el resultado es `not_evaluable`,
con `not_evaluable_reason="numeric_precision_unsupported"`. Media, desviaciones,
umbral y score son `None`; conteo original, referencia y trazabilidad se conservan.
El resultado admite JSON estricto con `allow_nan=False`.

Los valores de separación no son referencia: el adaptador reserva sus posiciones
sin convertir sus conteos a flotantes. No cambia puntos B03 ni rellena ausencias.
Así, un valor enorme solo en la separación o en el futuro no invalida por sí
solo una referencia anterior segura. Los resultados no finitos de operaciones
con parámetros extremos siguen produciendo `numeric_range`.

**Limitaciones:** se pueden rechazar datos matemáticamente evaluables, incluidos
enteros grandes que individualmente sí sean representables y cálculos que excedan
la tolerancia de un flotante adyacente. Las estadísticas aceptadas siguen siendo
aproximaciones binary64 certificadas, no números reales exactos. No se ofrece
una implementación de precisión arbitraria; no se cambian firmas ni esquema.

Reproducción real antes de H1 y resultado después, mediante B04 → B05 → B03 → B07:

| Referencia constante N / observado | Antes | Después |
|---|---|---|
| `10**20` / `N+4` | `no_signal`, umbral `1e20`, score `0` (incorrecto) | `not_evaluable`, precisión no soportada |
| `10**16` / `N+3` | `signal`, score `4` (igualdad mal clasificada) | `not_evaluable`, precisión no soportada |
| `10` / `13` | `no_signal`, umbral `13`, score `3` | Se conserva |
| `10` / `14` | `signal`, umbral `13`, score `4` | Se conserva |

## Integraciones pendientes

| Regla | Estado real en I1 | Motivo |
|---|---|---|
| EARS C2 | Funcional bajo los requisitos anteriores | Usa el detector existente y conserva parámetros |
| Canal endémico | `not_evaluable` | `explicit_period_channel_pending`: el adaptador del canal histórico de 52 posiciones no es compatible con B03 |
| SARIMA un paso | `not_evaluable` | `forecast_service_pending`: no existe contrato B06 para predicciones causales por periodo |

Una observación ausente tiene prioridad y devuelve `missing_observation` en
cualquier regla. Otros motivos EARS: `calendar_unverified`,
`insufficient_reference`, `calendar_boundary_pending`, `nonconsecutive_grid`,
`missing_reference`, `numeric_range` y `numeric_precision_unsupported`.
No son booleanos ni colores.

No se ajusta SARIMA, no se inventan predicciones o fechas y no se ejecuta un canal
simulado. La adaptación futura del canal debe conservar referencias de años
anteriores y resolver S53 y cobertura. Requiere coordinación B03, no un nuevo
mapeo posicional. La regla de rojo con dos reglas continúa únicamente en la demo
histórica; una política nueva de agregación requiere decisión separada.

## Conexión con B05-I1 y B04

La API real de B05 es `run_pipeline(..., config=PipelineConfig(...))` y su salida
es `PipelineResult`. No se modifica ni se inventa otra interfaz. El consumidor
posterior debe hacer:

```python
if pipeline_result.status == "completed" and pipeline_result.series is not None:
    signals = evaluate_signals(pipeline_result.series)
```

La ejecución integrada de B05-I2 deberá acordar selección/configuración de reglas
y cómo presentar `not_evaluable`. Este incremento entrega el núcleo y prueba el
recorrido real B04 → B05-I1 → B03 → B07, pero no añade llamadas a B05.
`completed` en B05 y `eligibility=not_evaluated` en B03 no equivalen a aptitud:
B07 evalúa sus requisitos locales sin cambiar esos estados de entrada.
Las cargas bloqueadas de B04/B05 no proporcionan bundle y no se evalúan.

## Ejemplo sintético ejecutable

```python
from episentinel.data.epidemiological_series import (
    CalendarMetadata, MunicipalIdentity, PeriodGrid, build_series,
)
from episentinel.services.signal_service import evaluate_signals

# Declaración de prueba; no acredita un calendario epidemiológico oficial.
grid = PeriodGrid(
    tuple((2020, week) for week in range(1, 11)),
    CalendarMetadata("synthetic", "v1", "ejemplo sintético", "verified",
                     "declaración sintética del proveedor para probar el método"),
)
rows = [dict(cod_mun="05001", ano=2020, semana=week, cod_eve=210,
             conteo=40 if week == 10 else 10) for week in range(1, 11)]
bundle = build_series(rows, territory=MunicipalIdentity("05001"),
                      event_codes=(210,), period_grid=grid)
report = evaluate_signals(bundle)
last_ears = [r for r in report.results if r.rule == "ears_c2"][-1]
assert last_ears.status == "signal" and last_ears.threshold == 13
assert all(r.status == "not_evaluable" for r in report.results if r.rule != "ears_c2")
print(last_ears.status)
```

## Causalidad y verificación

El cálculo numérico recibe únicamente una ventana terminada en T. Nunca se ajustan
parámetros con la serie completa. La referencia excluye T y la separación. Los
tests prueban invariancia ante cambios de conteos/faltantes futuros y extensión
de la malla; también prueban que modificar T o la separación no cambia la
referencia. Los cambios futuros deben seguir siendo estructuralmente válidos
para B03: errores estructurales bloquean la llamada, no son experimentos causales.

```powershell
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -B -m pytest tests/test_signal_service.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest tests/test_alertas.py -q -p no:cacheprovider
python -B -m pytest -q -p no:cacheprovider tests/test_epidemiological_series.py tests/test_csv_loader.py tests/test_csv_contract.py tests/test_sivigila_adapter.py tests/test_audit_csv_sources.py tests/test_isolated_pipeline.py
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
git diff --check
git status --short
```

## Limitaciones epidemiológicas

Resultados sintéticos verifican software, no sensibilidad, especificidad ni
anticipación de brotes reales. No hay etiquetas de referencia para afirmar
eficacia epidemiológica. Identidad municipal sigue siendo candidata, con catálogo
pendiente. No se infiere subregistro ni completitud de notificación. S53 se
conserva sin declarar oficialmente válida su presencia en un año. Las decisiones
B03 pendientes, B06 y la adaptación del canal limitan el alcance de B07-I1.

## Evidencia inicial de I1 (antes de H1/H2)

Python 3.12.5, pytest 9.2.0, entorno `.venv` del proyecto:

- B07: **44 aprobadas**.
- Alertas históricas: **6 aprobadas**.
- Regresión B03/B04/B01-B02/B05: **184 aprobadas**.
- Suite completa: **258 aprobadas**.
- Ningún fallo, omisión ni advertencia reportada por pytest en estas ejecuciones.

Son grupos superpuestos: la suite completa incluye las pruebas específicas.
Los tests funcionales EARS se distinguen de los tests que comprueban el estado
no evaluable de SARIMA y canal. No se cuentan esas integraciones como funcionales.

El comando de regresión anterior omitía tres archivos en la documentación.
H2 corrige la lista para reproducir las 184 pruebas de los seis archivos. En la
ejecución se utiliza el intérprete explícito `.venv/Scripts/python.exe`, equivalente
a `python` después de activar ese entorno.

## Evidencia posterior a H1/H2

Mismo entorno local (Python 3.12.5, pytest 9.2.0):

- B07: **81 aprobadas**; incluye 37 casos nuevos de regresión numérica.
- Alertas históricas: **6 aprobadas**.
- Grupo completo B01/B02/B03/B04/B05, seis archivos: **184 aprobadas**.
- Suite completa: **295 aprobadas**.
- Ejecuciones finales sin fallos, omisiones ni advertencias reportadas por pytest.

La primera ejecución de las 44 pruebas antiguas tras introducir el rechazo previo
dio 43 aprobadas y un fallo: el test de `10**400` todavía esperaba `numeric_range`.
Se actualizó para exigir `numeric_precision_unsupported`, porque ahora se rechaza
antes de convertir a flotante. No se debilitó su exigencia de estado no evaluable
ni de JSON estricto. Las ejecuciones finales incluyen esa prueba corregida.

Las nuevas regresiones cubren el recorrido real CSV → B05 → B03 → B07 para
`10**20`, valores alrededor de `10**16`, vecinos de `2**53` y `10**400`; igualdad
y superación del umbral; frontera subunitaria `2**52`; negativos y picos ordinarios;
rechazo previo a pandas; independencia de valores de separación/futuros y rechazo
de salidas numéricas inconsistentes. Se mantienen las pruebas causales anteriores.

Preparado para revisión local independiente de OpenCode; sin publicación,
commit ni cierre del Issue #7. B07-I1 no cierra el alcance epidemiológico ni
las integraciones pendientes de B07.
