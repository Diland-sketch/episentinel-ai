# Demostración científica aplicada — I1

Rama: `feat/science-demo-i1`. Base: `18fd3fd36f417d31fef988d8e26a4c3060a376e1` (UX-I1, PR #29 publicado pero no integrado al comenzar). No se realizó merge de #29. El trabajo nuevo está aislado de esa rama y conserva B13. Publicación individual autorizada como dependencia de IA-I1. Este incremento se revisa por separado; no se realiza merge ni cierre de Issues.

## Disponibilidad comprobada antes de implementar

Inventario focalizado de reports, data/processed, experiments/runs y notebooks: no se encontraron predicciones por periodo ni modelos ajustados persistidos para esta evaluación. `scripts/evaluate_fase2.py` calcula yhat/lo/hi en memoria y solo escribe `reports/comparacion_fase2.csv` y `.json`. No se ejecutó ese script. Los directorios notebooks y experiments/runs no aportan una ejecución predictiva persistida.

El CSV contiene 24 filas, seis series (nacional, Cali, Medellín, Cúcuta, Bucaramanga e Ibagué) y cuatro métodos: último valor, ingenua estacional, SARIMA estacional y no estacional. Conserva MAE, RMSE, MASE, cobertura nominal cuando existe y tiempo de ajuste SARIMA. El JSON no agrega predicciones por periodo. `tiempo_s=0` en los baselines es el valor predeterminado del script, no un cronometraje de cero segundos.

La prueba histórica usa 52 posiciones de 2022 y entrenamiento 2007–2021. El panel combina 210+220, rellena ausencias con cero y pliega S53; el agregado evaluado incluye Exterior. La selección de territorios utilizó toda la ventana histórica. No se declara libre de fuga, 2022 intacto, SARIMA superior en general ni validación epidemiológica.

## Componentes y estado

| Componente | Estado entregado | Alcance |
|---|---|---|
| Resultados por serie | Visualización funcional de resultados históricos | Selección de serie y MAE/RMSE/MASE; gráfico y tabla de valores guardados, procedencia y límites |
| Curvas predicción/observado por periodo | Pendiente de evidencia | No existen artefactos verificables revisados; no se reconstruyen curvas a partir de errores agregados |
| Particiones y rolling origin | Configurador funcional sin ejecución | API real B10, límites exclusivos, ventanas admitidas/descartadas, rechazo explícito y descarga del plan |
| Benchmark B04/B05/B03 | Script funcional y visualización de ejecución registrada | Tres tamaños sintéticos, mediciones instrumentadas y procesos acotados; no es evaluación de modelos |

## Acceso y guion reproducible

```powershell
Set-Location 'C:\Proyecto IA\episentinel-ai'
.\.venv\Scripts\python.exe -B -m streamlit run app/platform_app.py --server.address 127.0.0.1 --server.port 8512 --server.headless true --browser.gatherUsageStats false
```

1. Laboratorio → Demostración aplicada → Resultados guardados. Elegir Cali · 76001 y MASE. Comparar cuatro barras y sus métricas: una comparación retrospectiva, sin pronósticos futuros. Leer el aviso de predicciones por periodo ausentes.
2. Diseño temporal → Porcentajes. Declarar 832 posiciones, 80 % entrenamiento y 10 % validación. Se obtienen 665, 83 y 84 posiciones: floor de los dos primeros tamaños, resto exacto a prueba. La tabla muestra porcentajes efectivos.
3. Cambiar entrenamiento a 98 % manteniendo validación en 10 %: configuración rechazada, sin plan ni métricas de sustitución.
4. Elegir Límites enteros: 728/780/832. Ver entrenamiento [0,728), validación [728,780), prueba [780,832). B10 devuelve 12 ventanas de validación y 12 de prueba; cortes 775 y 827 descartados por horizonte incompleto.
5. Cambiar Ventanas a inspeccionar a Prueba. Los segmentos muestran ocho posiciones objetivo por origen, no predicciones. Revisar tabla completa y motivos de exclusión. Descargar plan si hace falta; no se escribe configs/split.json ni evaluacion_b10.json.
6. Escalabilidad: leer las tres filas y gráfico del benchmark. Comparar el mayor tamaño de 50.000 filas artificiales con las 223.651 filas crudas del reporte histórico; no atribuir tiempos sintéticos a originales.
7. Observatorio: cargar b08_demo.csv normalmente con Upload. El resultado de B08 no se convierte en evaluación histórica ni en entrada B06. Al volver del Laboratorio se conserva archivo/huella/resultado. Las preferencias del configurador también se conservan.

## Compatibilidad experimental con B10

Se importan explícitamente `TemporalProtocol` y `plan_rolling_origin`; no se alteran sus módulos ni exportaciones. Se mantienen horizonte 8, paso 4, entrenamiento expansivo, cohorte inicial fija y tupla canónica de métodos. B10 rechaza límites no crecientes y particiones de evaluación menores que ocho posiciones. El planificador no certifica calendario ni elegibilidad de SARIMA.

832 es un ejemplo posicional, independiente de la serie elegida para consultar resultados históricos y del CSV de sesión. Cambiar controles no cambia métricas, no entrena y no selecciona hiperparámetros. La prueba nunca se usa para selección: antes de ejecutar se requieren decisiones congeladas después de validación, universo y criterios causales explícitos, calendario, continuidad, cobertura y elegibilidad. El plan por sí solo no impone control de acceso al conjunto de prueba.

## Benchmark ejecutado

Todos los registros son artificiales y deterministas (conteo=i%29, con ceros; evento 210; códigos sintéticos; 832 posiciones técnicas por candidato). B03 valida toda la entrada y construye solo la serie explícita 50001/210. No es la construcción de todas las series del universo. Los bytes se generan en memoria; no se mide lectura de disco ni se guarda el dataset.

Cada tamaño se ejecuta en proceso independiente con límite de 30 s y presupuesto total de 120 s. CLI permite como máximo cuatro tamaños, tres repeticiones, 100.000 filas y 8 MiB de CSV; tiempo por proceso entre 1 y 45 s. El máximo de filas limita la carga, pero no es un límite duro de RSS. Los fallos, timeouts y casos omitidos por presupuesto se registran sin métricas fabricadas. Solo se escribe un resumen JSON nuevo; se rechaza sobrescribir y dentro del repositorio las salidas se limitan a docs/benchmarks.

Instrumentación: wrappers temporales dentro del proceso aislado devuelven los argumentos/resultados originales y se restauran al salir. Ingesta/sintaxis mide read_csv_records dentro de B04. Validación es tiempo total B04 menos esa ingesta (incluye normalización, duplicados, diagnósticos y copias). Construcción mide build_series. B05 incluye además orquestación/deepcopy; no deben sumarse las tres etapas como si agotaran todo el total.

Pico de memoria: tracemalloc mide asignaciones Python e incluye generación y ejecución, con su sobrecoste de instrumentación. No mide RSS ni todas las asignaciones nativas. Una repetición por tamaño; no son estadísticas de latencia, pruebas de carga concurrente ni garantía de escalabilidad asintótica.

| Filas sintéticas | Ingesta (s) | Validación/resto B04 (s) | Construcción (s) | B05 total (s) | Pico Python (MiB) | Estado |
|---:|---:|---:|---:|---:|---:|---|
| 1000 | 0.0135 | 0.0268 | 0.0199 | 0.0763 | 1.347 | completed |
| 10000 | 0.1459 | 0.2443 | 0.1359 | 0.6617 | 9.798 | completed |
| 50000 | 0.7511 | 1.4345 | 0.7002 | 3.5489 | 49.825 | completed |

Registro: `docs/benchmarks/science_demo_i1.json`, fecha UTC `2026-11-17T23:25:07.525520+00:00`. Entorno Python 3.13.4; Windows-11-10.0.26300-SP0. Cero fallos, seis advertencias de condiciones provisionales por caso. El registro incluye huellas de código y CSV, límites y metodología.

Para reproducir en un resumen distinto (no sobrescribir la evidencia existente):

```powershell
.\.venv\Scripts\python.exe -B scripts/benchmark_demo.py --sizes 1000 10000 50000 --repetitions 1 --timeout 30 --output docs/benchmarks/science_demo_repeticion.json
```

La navegación solo lee el registro; no lanza subprocess ni entrenamiento. Ninguna pantalla conecta B03 con B06.

## Verificación y preservación

Pruebas específicas del incremento, B10 y regresión del Laboratorio: 83 aprobadas. Se añadió comprobación de preferencias y aislamiento de la sesión. Suite completa de la versión final: 775 aprobadas en 109,50 s. La ejecución previa a ese último test adicional tuvo 774 aprobadas.

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_applied_demo.py tests/test_benchmark_demo.py tests/test_lab_app.py tests/test_platform_app.py tests/test_rolling_origin.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Revisión real: selección de Cali/MASE, porcentajes incompatibles, cortes enteros 728/780/832, ventanas de prueba y benchmark. Carga nativa del CSV B13 y resultado 220 de cobertura 2/3 conservado al navegar. Preferencias de un plan 70/10 restauradas después de ir al Observatorio y volver. Las pruebas automatizadas verifican también que navegar no ajusta modelos, ausencia de artefactos y fallos del benchmark.

Capturas locales: science-historical-cali.jpg, science-invalid-plan.jpg, science-integer-partitions.jpg, science-rolling-origin.jpg, science-benchmark.jpg y science-observatory-preserved.jpg en la carpeta de evidencias de esta sesión.

No se modificaron B03/B04/B05/B06/B07/B10, contratos, configuraciones, datos ni reportes históricos. El respaldo B13 `backup/b13-before-ux-i1` y la copia independiente `ux-i1-baseline` siguen disponibles; no se requieren reset/stash para arrancarlos. Los 13 archivos históricos se contrastan con las huellas de UX-I1.

## Pendientes científicos concretos

- Persistir predicciones/observados por periodo con corte, identificador de ejecución, método, configuración, datos y versión; conservar intervalos cuando existan y motivos de fallo. No se generaron aquí.
- Acreditar calendario, continuidad, cobertura y política de faltantes, universo territorial y criterios de cohorte antes del ejecutor B10. No reutilizar implícitamente el ranking global heredado.
- Autorizar y registrar una evaluación temporal real para asignar métricas a un plan nuevo, congelando decisiones antes de prueba. B10-I1/I2 sigue siendo planificación.
- Si se necesita capacidad sobre todo el volumen original, diseñar una medición separada con un contrato compatible; este benchmark no hace esa afirmación.
