# B06-I2 — contrato del servicio de pronóstico

Refs #6. Documento del incremento acumulado I2-A (resultado protegido), I2-B
(adaptador SARIMA) e I2-C (revisión y documentación). Su publicación requiere
revisión de Diland; este documento no cierra el issue.

Base inspeccionada: `8fe8e93181386e1f77fd30a542a774f6f83d3cde` (merge de B06-I1).
El servicio estima valores futuros; no confirma brotes ni acredita detección
temprana. No implementa la evaluación B10.

## 1. API pública y métodos

```python
from episentinel.services import (
    Advertencia, ErrorPronostico, ForecastResult, generar_pronostico,
)

# Firma; los ejemplos ejecutables están en la sección 9.
# generar_pronostico(serie, corte, horizonte, metodo, *, alpha=0.05) -> ForecastResult
```

Las importaciones anteriores desde `episentinel.services.forecast_service`
también se conservan. `sarima_adapter.ejecutar_sarima` es un adaptador interno:
requiere un prefijo y un contexto ya validados; no sustituye la API pública.

| Método | Implementación reutilizada | Configuración | Histórico mínimo al corte |
|---|---|---|---:|
| `ultimo_valor` | `pronosticar_ultimo_valor` | Repetir último valor | 1 |
| `ingenua_estacional` | `pronosticar_ingenua_estacional` | Bloque cíclico de 52 observaciones | 52 |
| `sarima_sin_estacional` | `ajustar_sarima` y `pronosticar` | `(1,1,1)`, estacional `(0,0,0,0)` | 30 |
| `sarima_estacional` | Las mismas funciones SARIMA | `(1,1,1)`, estacional `(1,0,1,52)` | 156 |

Los baselines y `models/sarima.py` no se reemplazan ni modifican. No hay búsqueda
de órdenes, reintentos, selección automática ni sustitución por otro método.
El horizonte no se reduce a la cantidad de observaciones futuras disponibles.

## 2. Entrada, corte y no anticipación

- `serie`: una `pd.Series` de una unidad de análisis, ya preparada por el consumidor.
- `corte`: entero Python/NumPy, base cero e **inclusivo**, entre cero y `len(serie)-1`.
- `horizonte`: entero Python/NumPy estrictamente positivo. Booleanos no admitidos.
- `metodo`: uno de los cuatro identificadores exactos de la tabla.
- `alpha`: solo se aplica y valida para SARIMA. Real no booleano, convertible a
  float finito, con `0 < alpha < 1` y `0 < 1-alpha < 1` en la representación usada.
  Por defecto, `alpha=0.05` corresponde a nivel nominal 0.95. Los baselines lo
  ignoran, incluso si se suministra explícitamente; no adquieren intervalos.

El servicio usa únicamente `serie.iloc[:corte + 1]`. En ese prefijo exige:

1. `DatetimeIndex` sin zona horaria, sin `NaT`, único y creciente.
2. Separación exacta de siete días entre observaciones. Con un solo dato, la
   condición de separación no tiene pares que comprobar.
3. Valores reales compatibles con `numbers.Real`, finitos y no negativos;
   rechaza booleanos, complejos, texto y faltantes. `Decimal` no pertenece a ese
   conjunto de tipos soportados. No se convierten cadenas numéricas.

No se ordena, agrega, imputa ni elimina observaciones silenciosamente. El futuro
no aporta valores para validar mínimos, ajustar parámetros o actualizar estados.
Sus observaciones tampoco determinan las fechas de salida: se generan desde la
fecha del corte con pasos de siete días.

**Metadatos causales:** después de validar el prefijo SARIMA, se fija su atributo
de frecuencia a `7D` conservando exactamente las fechas. Así, que una fecha futura
invalide el atributo global `index.freq` no añade advertencias de inferencia al
resultado. Esto no asigna fechas a períodos B03 ni decide un calendario oficial.

La garantía se aplica al prefijo efectivamente recibido. El servicio no recupera
precisión ni tipos perdidos durante transformaciones anteriores del consumidor.

### Prioridad de validación

Se devuelve el primer error: tipo de serie, horizonte, método, serie vacía, corte,
índice, frecuencia, `alpha` (solo SARIMA), valores/conversión, longitud mínima,
constancia (solo SARIMA) y representabilidad de fechas futuras.

`SERIE_VACIA` tiene prioridad sobre el corte, después de horizonte y método. La
longitud mínima tiene prioridad sobre constancia si ambas condiciones fallan.

## 3. Política histórica y numérica de SARIMA

La política `sarima_min_history_v1` fija **30** observaciones sin estacionalidad
y **156** con estacionalidad. Son mínimos **operativos provisionales**:

- Treinta evita ajustar ARIMA(1,1,1) con historiales manifiestamente cortos. No es
  un mínimo matemático universal ni un requisito impuesto por statsmodels.
- Ciento cincuenta y seis proporciona tres bloques del retardo 52. Ofrece más
  repeticiones para estimar dependencias estacionales que uno o dos bloques;
  no equivale necesariamente a tres años epidemiológicos oficiales.
- La suficiencia estadística depende además de variabilidad, estructura y cambios
  de régimen. La convergencia se verifica **después** del ajuste. Ningún mínimo
  garantiza convergencia, identificabilidad o buen desempeño predictivo.

Se rechazan historiales exactamente constantes, incluidos todos ceros, para
SARIMA. Las series casi constantes pueden llegar al ajuste y siguen sujetas a sus
comprobaciones. Los baselines conservan el comportamiento de I1 sobre constantes.

Antes del ajuste SARIMA se rechaza una conversión numérica inexacta a float, por
ejemplo el entero `9007199254740993` o `Fraction(1, 3)`. Esta verificación no garantiza
que `log1p` preserve diferencias pequeñas entre conteos grandes. Los baselines
conservan la limitación conocida de conversión flotante de I1.

## 4. Resultado público e invariantes

| Atributo | Contenido |
|---|---|
| `estado_ejecucion` | `ok`, `rechazado`, `error` |
| `estado_ajuste` | Estado descrito en la tabla siguiente |
| `metodo`, `corte`, `fecha_corte`, `horizonte` | Solicitud validada hasta el punto alcanzado; pueden ser `None` en un rechazo temprano |
| `n_observaciones` | Tamaño del prefijo seleccionado; cero antes de seleccionar uno |
| `predicciones` | Copia `DataFrame`, índice temporal `fecha`, columna float `yhat` |
| `intervalos` | Copia `DataFrame` con `lo`, `hi`, o `None` |
| `nivel_intervalo` | Nivel nominal `1-alpha` en éxito SARIMA; `None` para baselines o fallos |
| `parametros` | Mapping protegido; período 52 para ingenua estacional; órdenes, alpha, transformación y política histórica para SARIMA |
| `diagnostico_ajuste` | Mapping protegido o `None`; resumen, no el objeto de statsmodels |
| `advertencias` | Tupla de `Advertencia(codigo, mensaje, fase)` |
| `error` | `ErrorPronostico(codigo, campo, mensaje, detalles)` o `None` |

El diagnóstico SARIMA contiene `converged` (bool o `None`), `llf` (float finito o
`None`), `parametros_finitos` (bool o `None`), y las claves enteras `iterations`,
`warnflag`, `fcalls` cuando están disponibles. No se fabrican diagnósticos ausentes.
Los errores del adaptador SARIMA incluyen la fase y, para excepciones capturadas,
tipo y motivo. Los rechazos de entrada incluyen detalles según la validación;
los fallos de baseline incluyen tipo y motivo de excepción, sin clave de fase.

| Situación | Ejecución | Ajuste |
|---|---|---|
| Rechazo previo | `rechazado` | `no_ejecutado` |
| Baseline correcto | `ok` | `no_requiere_ajuste` |
| Fallo operativo o salida inválida de baseline | `error` | `no_requiere_ajuste` |
| SARIMA correcto | `ok` | `convergente` |
| Optimización no convergente | `error` | `no_convergente` |
| Convergencia ausente/no interpretable/contradictoria | `error` | `no_verificado` |
| Excepción o resultado numérico inutilizable en ajuste | `error` | `fallido` |
| Ajuste convergente, pero advertencia bloqueante o fallo posterior | `error` | `convergente` |

`convergente` describe el diagnóstico de optimización; no equivale por sí solo a
éxito de ejecución. `fallido` puede conservar un indicador bruto positivo cuando
el resultado numérico sea inutilizable.

En éxito se exige horizonte exacto, fechas desde corte + siete días, valores finitos
y no negativos, y ausencia de error. SARIMA exige además diagnóstico numérico
válido, convergencia positiva, intervalos completos y nivel nominal válido.

**Cualquier resultado no exitoso tiene predicciones vacías, intervalos `None` y
nivel `None`. No hay éxito parcial con bandas inválidas.**

## 5. Códigos de error

### Rechazos de entrada (ajuste `no_ejecutado`)

| Código | Causa |
|---|---|
| `SERIE_INVALIDA` | Entrada distinta de `pd.Series` |
| `HORIZONTE_INVALIDO` | Horizonte no entero positivo o booleano |
| `METODO_INVALIDO` | Método no admitido |
| `SERIE_VACIA` | Sin observaciones |
| `CORTE_INVALIDO` | Corte no entero válido, negativo o fuera de rango |
| `INDICE_INVALIDO` | Índice no temporal, zona horaria, NaT, duplicados o desorden en el prefijo |
| `FRECUENCIA_INVALIDA` | Separación distinta de siete días |
| `VALORES_INVALIDOS` | Tipo numérico, signo, finitud o representación no admitidos |
| `ALPHA_INVALIDO` | Alpha SARIMA o su nivel resultante no válidos |
| `PRECISION_NUMERICA_NO_ADMITIDA` | Conversión inexacta previa a SARIMA |
| `HISTORICO_INSUFICIENTE` | Menos observaciones al corte que el mínimo del método |
| `SERIE_CONSTANTE_NO_ADMITIDA` | Prefijo SARIMA exactamente constante |
| `FECHAS_FUTURAS_INVALIDAS` | Fechas de salida no representables |

### Errores de ejecución

| Código | Causa / estado de ajuste SARIMA |
|---|---|
| `FALLO_AJUSTE` | Excepción operativa prevista durante ajuste / `fallido` |
| `ERROR_NUMERICO_AJUSTE` | Excepción o advertencia numérica / `fallido` |
| `AJUSTE_NUMERICO_INVALIDO` | Parámetros o log-verosimilitud inválidos / `fallido` |
| `NO_CONVERGENCIA` | Indicador negativo o aviso no contradictorio de no convergencia / `no_convergente` |
| `CONVERGENCIA_NO_VERIFICABLE` | Indicador ausente, inválido o contradictorio / `no_verificado` |
| `ADVERTENCIA_AJUSTE_BLOQUEANTE` | Aviso no permitido con indicador positivo / `convergente` |
| `FALLO_PRONOSTICO` | Excepción operativa prevista al pronosticar / `convergente` |
| `ERROR_NUMERICO_PRONOSTICO` | Excepción o advertencia numérica / `convergente` |
| `ADVERTENCIA_PRONOSTICO_BLOQUEANTE` | Otro aviso no permitido al pronosticar / `convergente` |
| `SALIDA_INVALIDA` | Estructura, columnas, longitud o fechas incompatibles / `convergente` |
| `RESULTADO_NUMERICO_INVALIDO` | Predicción puntual no real, no finita o negativa / `convergente` |
| `INTERVALO_INVALIDO` | Bandas ausentes, inválidas o sin `lo <= yhat <= hi` / `convergente` |

Los baselines conservan `FALLO_PRONOSTICO` y `SALIDA_INVALIDA` con estado de ajuste
`no_requiere_ajuste`. Si concurren varias incidencias SARIMA, rige el orden de
comprobación de la sección 6; los avisos capturados siguen disponibles.

## 6. Convergencia, advertencias y excepciones

Por fase se capturan advertencias con categoría y mensaje, sin descartarlas del
resultado. No se cambia el optimizador, sus órdenes ni los algoritmos existentes.

Después del ajuste se revisa, en este orden:

1. Excepción operativa capturada, si existe.
2. Parámetros reales finitos y log-verosimilitud finita.
3. Contradicción: `converged=True` con `ConvergenceWarning` o `warnflag` entero no cero.
4. `converged=False` o aviso de no convergencia sin indicador positivo contradictorio.
5. Ausencia de un indicador booleano positivo verificable.
6. Advertencias numéricas y demás advertencias bloqueantes.

Solo después se solicita el pronóstico. Allí se comprueban excepciones, advertencias,
estructura y valores puntuales, bandas y columnas inesperadas. Un `llf` finito por
sí solo no acredita convergencia.

| Advertencia | Tratamiento |
|---|---|
| Calendario provisional / período 52 / mínimo operativo | Informativa, fase `validacion` |
| `ValueWarning` conocido de frecuencia inferida `7D` o `W-<día>` | Permitido y registrado |
| `UserWarning` conocido de inicialización AR/MA con ceros | Permitido solo durante ajuste, sujeto al resultado final |
| `ConvergenceWarning` | Impide éxito; contradicción con indicador positivo da `no_verificado` |
| `RuntimeWarning` | Bloqueante numérico |
| Hessiano/covarianza, insuficiencia de inicialización u otro aviso no reconocido | Bloqueante |

Los códigos de avisos del adaptador son `FRECUENCIA_INFERIDA`,
`INICIALIZACION_SARIMA`, `NO_CONVERGENCIA`, `ADVERTENCIA_NUMERICA` y
`ADVERTENCIA_BLOQUEANTE`. La lista permitida usa categorías y mensajes conocidos;
cambios de versión pueden exigir revisar esa lista, sin permitir avisos desconocidos
automáticamente. Un aviso de inicialización durante pronóstico también bloquea.

Se capturan `ValueError`, `RuntimeError`, `numpy.linalg.LinAlgError`,
`FloatingPointError` y `OverflowError` alrededor de las funciones del modelo. Las
tres últimas se clasifican como numéricas. No se captura indiscriminadamente
`Exception`; `TypeError`, `AttributeError` y `AssertionError` de programación se
propagan en esas llamadas. Clasificar por tipo no permite distinguir todas las
causas posibles de un `ValueError`/`RuntimeError`.

El contexto local NumPy eleva desbordamientos, operaciones inválidas y divisiones
por cero; ignora subdesbordamientos. Filtros de avisos y configuración NumPy se
restauran al salir. No se ha certificado ejecución concurrente multihilo.

## 7. Interpretación de los intervalos

Se reutiliza el modelo histórico: ajuste sobre `log1p(casos)`, predicción y bandas
en esa escala, transformación `expm1` y truncado inferior a cero.

- `yhat` es la retransformación del punto en escala logarítmica, sin corrección
  de sesgo; no es generalmente la media predictiva de conteos.
- `nivel_intervalo=1-alpha` es **nominal**, no cobertura empírica garantizada.
- Las bandas no incorporan automáticamente toda la incertidumbre de estimación
  de parámetros o selección del modelo.
- No se redondean estimaciones a conteos enteros.
- Se exige índice común, longitud exacta y `0 <= lo <= yhat <= hi`, todo finito.
- Una banda ancha no es por sí sola un error numérico ni una señal de brote.
- No hay bandas inventadas para baselines ni conexión automática con B07.

## 8. Inmutabilidad y compatibilidad de ForecastResult

Los nombres públicos de I1 y sus rutas de importación se conservan. El constructor
ahora es keyword-only y requiere `estado_ejecucion` y `estado_ajuste`; los demás
atributos se validan según el estado. No es válido construir `ForecastResult()`
vacío y asignar campos posteriormente. La construcción directa incoherente lanza
`TypeError`/`ValueError`; las entradas inválidas al servicio generan resultados
estructurados.

Internamente hay un único eje de fechas y tuplas de valores/bandas. Cada acceso
a `predicciones` o `intervalos` materializa un DataFrame independiente. Mutar una
tabla recibida por el constructor o devuelta por una propiedad no cambia el resultado.

Parámetros, diagnósticos y detalles de errores se copian a mappings protegidos;
listas/tuplas se congelan recursivamente. Se admiten escalares simples y sus
equivalentes NumPy normalizados; claves de mapping deben ser texto. Arrays,
DataFrames, objetos arbitrarios y colecciones cíclicas en metadatos se rechazan.
El adaptador extrae un resumen de diagnósticos, no almacena el objeto ajustado.

Incompatibilidades: reasignación de campos; mutación de mappings; construcción
posicional/vacía; depender de identidad de DataFrames o de campos internos de
dataclasses. No se garantiza `asdict`, pickle ni JSON directo. `dict(mapping)`
produce una copia superficial: los mappings anidados necesitan conversión
recursiva si un consumidor requiere serialización. No hay serializador público.

El constructor admite bandas suministradas directamente para baselines como
contenedor validado, pero el servicio nunca las estima y mantiene su nivel en
`None`. La protección es para uso normal de la API, no frente a manipulación
deliberada de internals de Python.

## 9. Ejemplos reproducibles

Ejecutar cada bloque completo desde la raíz del repositorio con las dependencias
de `pyproject.toml` instaladas. Se usa `src` explícitamente para no requerir una
instalación editable. Todos los datos son sintéticos; no se escriben reportes.

### 9.1 Baselines, corte inclusivo y vistas independientes

```python
import sys
sys.path.insert(0, "src")
import numpy as np
import pandas as pd
from episentinel.services import generar_pronostico

s = pd.Series(np.arange(120, dtype=float),
              index=pd.date_range("2020-01-01", periods=120, freq="7D"))
for metodo in ("ultimo_valor", "ingenua_estacional"):
    r = generar_pronostico(s, corte=79, horizonte=60, metodo=metodo)
    assert r.estado_ejecucion == "ok" and len(r.predicciones) == 60
    assert r.intervalos is None and r.diagnostico_ajuste is None
    esperado = np.full(60, 79.) if metodo == "ultimo_valor" else np.resize(np.arange(28., 80.), 60)
    np.testing.assert_array_equal(r.predicciones.yhat, esperado)
    vista = r.predicciones
    vista.iloc[0, 0] = -999
    np.testing.assert_array_equal(r.predicciones.yhat, esperado)
    print(metodo, r.estado_ejecucion, len(r.predicciones))
```

### 9.2 SARIMA real y comparación causal del resultado completo

```python
import sys
sys.path.insert(0, "src")
import numpy as np
import pandas as pd
from episentinel.services import generar_pronostico

n = 312
rng = np.random.default_rng(42)
s = pd.Series(rng.poisson(40 + 10 * np.sin(2 * np.pi * np.arange(n) / 52)).astype(float),
              index=pd.date_range("2010-01-01", periods=n, freq="7D"))
cola = pd.Series(np.full(12, 1e12),
                 index=pd.date_range(s.index[-1] + pd.Timedelta(days=7), periods=12, freq="7D"))
completa = pd.concat([s, cola])
alterada = completa.copy()
fechas = list(alterada.index)
fechas[-1] = pd.NaT  # exclusivamente posterior al corte
alterada.index = pd.DatetimeIndex(fechas)
for metodo in ("sarima_sin_estacional", "sarima_estacional"):
    r = generar_pronostico(completa, n - 1, 8, metodo, alpha=0.05)
    if r.estado_ejecucion != "ok":
        raise RuntimeError((r.error, r.advertencias, r.diagnostico_ajuste))
    assert r.estado_ajuste == "convergente" and r.nivel_intervalo == 0.95
    assert r.diagnostico_ajuste["converged"] is True
    pd.testing.assert_index_equal(r.predicciones.index, r.intervalos.index)
    assert (r.intervalos.lo <= r.predicciones.yhat).all()
    assert (r.predicciones.yhat <= r.intervalos.hi).all()
    assert generar_pronostico(alterada, n - 1, 8, metodo) == r
    print(metodo, r.estado_ajuste, dict(r.diagnostico_ajuste))
```

La semilla fija facilita reproducir el caso; no garantiza el mismo resultado en
todas las versiones de dependencias. El ejemplo no acepta un fallo como éxito.

### 9.3 Rechazos estructurados y prioridad de serie vacía

```python
import sys
sys.path.insert(0, "src")
import pandas as pd
from episentinel.services import generar_pronostico

vacia = pd.Series(dtype=float)
r = generar_pronostico(vacia, corte=-1, horizonte=8, metodo="ultimo_valor")
assert r.error.codigo == "SERIE_VACIA" and r.estado_ajuste == "no_ejecutado"
s = pd.Series([7.] * 156, index=pd.date_range("2020-01-01", periods=156, freq="7D"))
r = generar_pronostico(s, 155, 8, "sarima_estacional")
assert r.error.codigo == "SERIE_CONSTANTE_NO_ADMITIDA"
assert r.predicciones.empty and r.intervalos is None
assert generar_pronostico(s, 155, 8, "ultimo_valor").estado_ejecucion == "ok"
print("Rechazos y prioridad verificados")
```

## 10. Integración pendiente con B03/B05 y compatibilidad

B03 devuelve `SeriesBundle` con períodos explícitos `(año, semana)`, eventos
separados y faltantes `None`. La cobertura completa de una malla declarada no
garantiza continuidad semanal, y `verification="verified"` no asigna fechas.
B05 entrega ese bundle después de completar su pipeline; no construye la
`pd.Series` fechada requerida por B06.

El adaptador de calendario queda pendiente: correspondencia versionada y con
procedencia entre períodos y fechas, continuidad del prefijo, preservación de
faltantes y selección explícita de evento/territorio. No se deben generar fechas
por posición ni convertir con ISO sin decisión aprobada. No se suman eventos,
imputan faltantes o pliega S53 en B06.

B07 conserva `forecast_service_pending` para su regla SARIMA: este incremento no
conecta la detección. Un pronóstico desde un corte fijo tampoco es equivalente a
evaluar múltiples orígenes actualizando el estado con observaciones posteriores.

Dependencias locales: `forecast_service -> forecast_result / baselines`, y solo
al solicitar SARIMA, `forecast_service -> sarima_adapter -> models.sarima`.
El adaptador importa el resultado, no el servicio. No hay dependencia circular
en ese recorrido ni importación de Streamlit. B03/B04/B05/B07 no se modifican.

### Plataforma I1 inspeccionada sin integración

El commit remoto `67984a39a22672732a22ef18c6aa05f3f84363ea` se revisó respecto de
la base local, sin merge ni rebase. Su código de aplicación no importa
`ForecastResult` ni llama a `generar_pronostico`: el Observatorio usa B05 y el
laboratorio histórico llama directamente a los baselines y a `models.sarima`.
Por ello no se identificó una adaptación funcional de B06 exigida por ese commit.
Esto es una revisión estática, no una prueba de ejecución de las ramas combinadas.

El texto de `app/platform_app.py` todavía describe B06-I1 con dos baselines y su
lista de documentos no incluye este contrato. Actualizar esa presentación tras
publicar I2 corresponde al responsable de plataforma; no se modificó aquí.

## 11. Verificación y límites de la evidencia

```powershell
python -B -m pytest -q -p no:cacheprovider tests/test_forecast_result.py tests/test_forecast_service.py tests/test_sarima_service.py
python -B -m pytest -q -s -p no:cacheprovider tests/test_sarima_service.py -k sarima_real
python -B -m pytest -q -p no:cacheprovider
git diff --check
```

Las pruebas combinan dobles deterministas para fallos con ajustes reales de ambas
variantes. Se conserva la representación de los 114 casos originales de I1. Las
pruebas reales comparan la salida con `pronosticar()` sobre el mismo ajuste y
verifican que cambiar una fecha exclusivamente futura no altere predicciones,
bandas, estados, advertencias ni diagnósticos.

La normalización del `index.freq` del prefijo descrita en la sección 2 ya estaba
presente al iniciar la revisión de Codex del 16 de noviembre de 2026. Esta revisión
verificó el comportamiento mediante las pruebas existentes; no cambió algoritmos,
código del servicio ni pruebas. Los cambios realizados fueron documentales.
No se ha evaluado desempeño sobre datos epidemiológicos reales, calibración de
intervalos, múltiples versiones de statsmodels ni ejecución concurrente. Los
horizontes no tienen límite arbitrario de 52, pero están sujetos a fechas
representables y recursos disponibles; no se captura `MemoryError`.

### Evidencia local del 16 de noviembre de 2026

Entorno Windows: Python 3.14.5 (64 bits), pandas 3.0.3, NumPy 2.4.6,
statsmodels 0.15.0 y pytest 8.4.2.

| Ejecución | Resultado exacto |
|---|---|
| Tres archivos de pruebas B06 | `323 passed in 13.03s` |
| Selección `sarima_real` | `2 passed, 101 deselected in 6.40s` |
| Suite completa del checkout local | `618 passed in 15.95s` |

Las tres ejecuciones finalizaron con código cero, sin fallos ni resumen de
advertencias de pytest. Esto no significa ausencia de advertencias estructuradas:
el servicio conserva sus avisos de calendario, período y mínimo operativo.
Los conteos coinciden con lo reportado por OpenCode; los tiempos reportados
anteriormente eran 8.14 s para B06 y 14.40 s para la suite completa. No se dispone
aquí de sus versiones para atribuir diferencias de tiempo al entorno.

Ambas variantes reales usaron 312 observaciones sintéticas al corte y horizonte 8,
con nivel nominal 0.95. Sin estacionalidad: `converged=True`, 9 iteraciones y
`llf=71.7868934524314`. Estacional: `converged=True`, 23 iteraciones y
`llf=54.58391927380473`. Se comprobó la igualdad con el algoritmo existente y
la invariancia del resultado completo ante una fecha inválida posterior al corte.

También se ejecutaron satisfactoriamente los cuatro bloques Python de este
documento (importación de la API y los tres ejemplos de la sección 9).
La suite local no incluye los nuevos tests de plataforma del commit remoto:
ese commit se inspeccionó sin integrarlo. Estos resultados no acreditan todavía
el comportamiento de un checkout combinado ni desempeño epidemiológico real.

### Verificación integrada previa a publicación — 17 de noviembre de 2026

Con autorización de publicación, la rama `feat/b06-i2a-forecast-result` se
actualizó mediante fast-forward a `67984a39a22672732a22ef18c6aa05f3f84363ea`.
Esta es la base integrada de la ejecución siguiente; la evidencia del día 16
se conserva arriba como registro anterior a la actualización.

Antes de actualizar se respaldaron fuera del repositorio los ocho archivos B06
y los dos reportes locales. Tras el fast-forward, los diez archivos conservaron
exactamente sus hashes SHA-256 y el índice permaneció vacío. No hubo conflictos.
Solo se amplió este documento después de ejecutar las pruebas; no se modificaron
el código B06, sus pruebas ni los módulos de otros integrantes.

Entorno: Python 3.14.5 (Windows, 64 bits), pandas 3.0.3, NumPy 2.4.6,
statsmodels 0.15.0 y pytest 8.4.2.

| Ejecución sobre la base integrada | Resultado exacto |
|---|---|
| Tres archivos de pruebas B06 | `323 passed in 16.50s` |
| Selección `sarima_real` | `2 passed, 101 deselected in 8.42s` |
| Suite completa, incluida plataforma | `650 passed in 28.06s` |

Las tres ejecuciones terminaron con código cero, sin fallos ni resumen de
advertencias de pytest. Las 32 pruebas adicionales respecto de la suite local
anterior corresponden al incremento de plataforma incorporado. Los avisos
estructurados del servicio siguen formando parte de su contrato.

Las pruebas reales volvieron a confirmar convergencia de ambas variantes,
8 pasos y nivel nominal 0.95: sin estacionalidad, 9 iteraciones y
`llf=71.7868934524314`; estacional, 23 iteraciones y `llf=54.58391927380473`.
La ejecución integrada no implica que la plataforma use B06: el Observatorio
sigue usando B05 y el laboratorio histórico llama al algoritmo original.
Permanecen pendientes el contrato temporal B03/B05, la integración B07 y la
evaluación de desempeño y calibración sobre datos epidemiológicos reales.
