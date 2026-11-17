# B10-I1/I2 — protocolo retrospectivo y planificación causal

Refs #10. Alcance autorizado: contrato, selección y planificación puras, sin
ajuste de modelos, lectura automática de datos o publicación de resultados reales.
Base de implementación: `4347f6c7a15ef54a32e40fda0d705f660ec78ead`, con B06-I2
integrado. Este documento no declara completado B10 ni cierra el issue.

## 1. Alcance y dependencias

El objetivo futuro es evaluar pronósticos a ocho semanas con paso de cuatro.
I2 solo trabaja con posiciones: no certifica que ocho posiciones sean ocho
semanas epidemiológicas. No construye fechas ni adapta automáticamente B03 a B06.
Puede desarrollarse y probarse con series sintéticas sin decidir el calendario.

Para datos reales quedan pendientes de Diland/B03/B09: calendario y continuidad,
semana 53, eventos, agregaciones, catálogo territorial, cobertura, procedencia y
tratamiento analítico de faltantes. El panel histórico que combina 210+220,
pliega S53 y rellena ausencias con cero no permite reconstruir esos faltantes.
No se importa ese panel ni se reutilizan sus decisiones de forma implícita.

La evaluación es retrospectiva sobre una versión de datos. Sin versiones de
notificación no reproduce necesariamente la información disponible en tiempo real.
El período histórico 2022 ya fue examinado: no se describe como prueba intacta.
El paso de validación a prueba exige congelar las decisiones del experimento;
el planificador no impone por sí solo ese control de acceso.

## 2. Protocolo público

Importaciones explícitas; no se cambian exportaciones de módulos compartidos:

```python
from episentinel.evaluation.temporal_protocol import TemporalProtocol, validate_protocol
from episentinel.evaluation.series_selection import EligibilityCriteria, select_cohort
from episentinel.evaluation.rolling_origin import plan_rolling_origin, validate_origin
```

`TemporalProtocol(train_size, validation_end, total_size, ...)` es un dataclass
congelado. Los límites son enteros positivos **exclusivos** y crecientes:

- Entrenamiento inicial: `[0, train_size)`.
- Validación: `[train_size, validation_end)`.
- Prueba: `[validation_end, total_size)`.

Se exige horizonte 8, paso 4, ventana `expanding`, cohorte
`fixed_initial_training` y la tupla canónica de los cuatro métodos B06:
`ultimo_valor`, `ingenua_estacional`, `sarima_sin_estacional`, `sarima_estacional`.
Cada partición de evaluación debe admitir al menos una ventana completa de ocho
objetivos. Se rechazan booleanos, fracciones, límites invertidos y protocolos
incompatibles mediante `ValueError`; un objeto de protocolo incorrecto causa
`TypeError`. No hay coerción automática de fechas, diccionarios o nombres.

`configs/evaluacion_b10.json` es una especificación inicial, no una orden de
ejecución. Su universo y criterios están en `null` deliberadamente: deben ser
explícitos antes de seleccionar. La sección `positional_example` es ilustrativa.
El JSON representa métodos como lista; al construir el protocolo se convierte
explícitamente a tupla. Las funciones no leen ese archivo por sí mismas.

## 3. Selección causal

```python
cohort = select_cohort(
    series, candidate_codes=("05001", "76001"),
    protocol=protocol,
    criteria=EligibilityCriteria(min_observed=8, max_series=1, min_positive=None),
)
```

`series` es un mapping de código territorial a `pd.Series`. `candidate_codes`
es una tupla explícita, no vacía, sin duplicados ni códigos vacíos o con espacios
externos. El proveedor debe obtener ese universo de un catálogo aprobado o del
entrenamiento inicial, nunca de observaciones futuras. Entradas adicionales del
mapping se ignoran: un territorio que aparece después no entra en la cohorte.

El consumidor debe alinear las posiciones de todas las series a la misma malla
antes de llamar. La función no consulta etiquetas del índice ni les atribuye
significado calendario. No ordena, agrega, reindexa ni elimina observaciones.
Un prefijo sin alineación acreditada no debe usarse en una ejecución real.

Solo se lee `serie.iloc[:train_size]`. La longitud total, valores futuros,
etiquetas del índice y resultados de modelos no participan en filtros ni ranking.
La garantía se aplica al prefijo recibido: no recupera tipos o precisión perdidos
por una transformación anterior que hubiera usado el conjunto completo.

Los criterios son obligatorios y quedan guardados en el resultado:

- `min_observed`: cantidad mínima explícita de valores válidos.
- `max_series`: límite explícito de selección; no se completa con series inelegibles.
- `min_positive=None`: no filtra por cantidad de valores positivos. Si se proporciona
  un entero positivo, aplica ese umbral únicamente al prefijo inicial.

**No se adopta el criterio histórico de 52 semanas positivas.** Estos criterios
son filtros operativos del experimento; no garantizan suficiencia estadística.
I2 exige además prefijos iniciales completos y válidos. Por ello, en esta versión,
`min_observed <= train_size` no permite aceptar huecos; se conserva como criterio
explícito para auditoría. Los umbrales mayores que el prefijo se rechazan.

El score es la suma flotante mediante `math.fsum` del prefijo completo. Orden:
score descendente y código textual ascendente. Se rechazan conversiones numéricas
inexactas y sumas no representables; la suma final sigue siendo flotante y no es
una garantía de precisión aritmética ilimitada. El ranking favorece series de
mayor actividad: su población objetivo debe declararse, no generalizarse a todos
los territorios. Los niveles territoriales deben separarse antes de seleccionar;
no se mezclan municipios con agregados nacionales en un ranking implícito.

## 4. Resultado de selección y exclusiones

`FrozenCohort` contiene `train_size`, criterios congelados, universo ordenado,
`selected_codes` en orden de ranking, registros por código y regla de puntuación.
No retiene referencias a las series originales ni ofrece entrada de resultados
de pronóstico. Sus colecciones son tuplas y sus registros dataclasses congelados.
La protección cubre el uso normal, no manipulación deliberada de internos Python.

Cada `SelectionRecord` conserva score (o `None`), número de valores válidos y
positivos, `eligible`, `selected` y motivos. Un candidato elegible fuera del top
conserva `eligible=True`, `selected=False` y `outside_top_k`.

Motivos posibles:

| Motivo | Significado |
|---|---|
| `series_absent` | Candidato explícito sin serie disponible |
| `insufficient_initial_history` | Prefijo menor que `train_size` |
| `missing_initial_value` | Faltante en el prefijo; no se convierte en cero |
| `invalid_initial_value` | Valor no real, booleano, negativo, infinito o no representable |
| `inexact_initial_value` | Conversión a float pierde precisión |
| `min_observed_not_met` | No alcanza el umbral explícito de valores válidos |
| `min_positive_not_met` | No alcanza el umbral opcional de positivos |
| `nonfinite_score` | La suma no es representable |
| `outside_top_k` | Elegible pero fuera del límite solicitado |

Puede haber varios motivos por candidato. Los conteos parciales son diagnósticos,
no una imputación ni una puntuación parcial. Prefijos cortos o inválidos no reciben
score. Una cohorte vacía es un resultado explícito, no activa otra selección.

## 5. Rolling origin común

`plan_rolling_origin(protocol) -> RollingPlan` devuelve un calendario posicional
compartido por todos los métodos, independiente de series o éxitos de ajuste.
Cada `Origin` contiene partición, corte inclusivo, `train_start=0`, inicio y fin
exclusivo de objetivos y los cuatro métodos. `target_positions` contiene ocho
posiciones. La ventana de entrenamiento futura será `[0, cut + 1)`.

El primer corte de cada partición es su inicio menos uno. Se avanza de cuatro en
cuatro, reiniciando la cuadrícula al comenzar prueba. Solo se incluyen objetivos
completamente contenidos en su partición. Los candidatos finales incompletos se
guardan en `excluded` con `incomplete_partition_horizon`; nunca se acortan.

`validate_origin(protocol, partition=..., cut=...)` valida solicitudes explícitas:
rechaza cortes fuera de cuadrícula, tipos ambiguos y horizontes que crucen el
límite. La exclusión automática de colas al generar un plan se distingue así de
aceptar silenciosamente una solicitud explícita inválida.

Ejemplo de tamaños **sin atribución de fechas epidemiológicas**:

| Partición | Cortes | Objetivos permitidos | Cantidad |
|---|---|---|---:|
| Validación | 727, 731, ..., 771 | 728 a 779 | 12 |
| Prueba | 779, 783, ..., 823 | 780 a 831 | 12 |

Se registran como excluidos 775 y 827, respectivamente. Dentro de un pronóstico
de ocho pasos no se incorporan objetivos observados para actualizar el modelo.
En el siguiente origen podrán usarse observaciones ya anteriores a ese corte.
Esto deberá implementarse en I3; I2 no ajusta ni actualiza modelos.

## 6. Métricas y fallos: contrato para I3, aún no implementado

Una futura ejecución conservará una fila por serie, modelo y corte, también en
fallo, y predicciones por paso. Los mínimos B06 1/52/30/156 no se sustituyen por
el filtro de selección. Un rechazo de SARIMA por histórico insuficiente o serie
constante no cambia la cohorte ni los orígenes de los baselines.

Se prevén MAE, RMSE, MASE y cobertura/ancho de intervalos disponibles. Se comprobará
alineación exacta y ocho objetivos finitos; los objetivos faltantes implicarán
evaluación no disponible con motivo explícito, sin imputar ni truncar. El score
de selección no se recalcula usando esos objetivos.

MASE usará exclusivamente el prefijo del origen; denominador cero o histórico
insuficiente producirán métrica nula con motivo. El retardo estacional requiere
decisión temporal: no se ratifica aquí un año epidemiológico de 52 posiciones.
Se separarán rechazos de entrada, fallos de ajuste y métricas no evaluables.
No habrá sustitución de métodos ni descarte silencioso de errores inesperados.

Comparaciones: soporte común acompañado de tasas de fallo y exclusiones sobre
todos los intentos planificados; resúmenes por nivel territorial y paso. Las
ventanas solapadas y los agregados territoriales no son observaciones independientes.
Los intervalos son nominales; pasar pruebas sintéticas no valida brotes ni
calibración epidemiológica. No se modifican `forecast_metrics.py` ni B06.

## 7. Ejemplo sintético reproducible

Desde la raíz, con dependencias instaladas:

```python
import sys
sys.path.insert(0, "src")
import pandas as pd
from episentinel.evaluation.temporal_protocol import TemporalProtocol
from episentinel.evaluation.series_selection import EligibilityCriteria, select_cohort
from episentinel.evaluation.rolling_origin import plan_rolling_origin

p = TemporalProtocol(train_size=8, validation_end=20, total_size=32)
data = {"B": pd.Series([2.] * 8 + [999.] * 24),
        "A": pd.Series([2.] * 8 + [0.] * 24)}
c = select_cohort(data, candidate_codes=("B", "A"), protocol=p,
                  criteria=EligibilityCriteria(min_observed=8, max_series=1))
assert c.selected_codes == ("A",)
data["B"].iloc[8:] = -999
assert select_cohort(data, candidate_codes=("B", "A"), protocol=p,
                     criteria=c.criteria) == c
plan = plan_rolling_origin(p)
assert tuple(o.cut for o in plan.origins) == (7, 11, 19, 23)
assert all(len(o.target_positions) == 8 for o in plan.origins)
```

## 8. Verificación y siguientes incrementos

```powershell
python -B -m pytest -q -p no:cacheprovider tests/test_series_selection.py tests/test_rolling_origin.py
python -B -m pytest -q -p no:cacheprovider
```

Las pruebas utilizan datos sintéticos y verifican independencia del futuro,
desempates, filtros, inmutabilidad, límites inclusivos/exclusivos, métodos comunes
y colas incompletas. No se ejecutan experimentos epidemiológicos reales.

Ejecución local del 17 de noviembre de 2026, sobre la base indicada al inicio:

| Comprobación | Resultado |
|---|---|
| Selección y rolling origin | `74 passed in 3.56s` |
| Suite completa, incluida plataforma y Laboratorio | `735 passed in 37.06s` |
| Ejemplo sintético completo de la sección 7 | Aprobado |

Ambas ejecuciones pytest terminaron con código cero, sin fallos ni resumen de
advertencias. Entorno: Python 3.14.5, pandas 3.0.3, NumPy 2.4.6,
statsmodels 0.15.0 y pytest 8.4.2 en Windows. La suite incluye las pruebas
sintéticas SARIMA ya existentes; las funciones nuevas no ejecutan modelos.
Los dos reportes históricos conservaron sus hashes previos. Esta evidencia
verifica planificación y regresiones del checkout, no resultados de evaluación real.

I3 requerirá una nueva revisión para implementar el ejecutor B06, validación de
métricas y persistencia por ejecución. Quedan sin autorización los ajustes masivos,
la evaluación real, modificaciones compartidas, commits, push y PR. El protocolo
no fija por sí solo un universo de 65 series ni criterios epidemiológicos.
