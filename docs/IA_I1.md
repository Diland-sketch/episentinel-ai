# IA-I1 — Pronóstico retrospectivo experimental B06

Rama `feat/ia-i1`, base de commit `18fd3fd` (UX-I1). Contiene Science Demo I1 sin registrar, preservado antes de trabajar en un ZIP y parche externos. Publicación autorizada en un PR individual, dependiente de Science Demo I1. No se realiza merge ni cierre de Issues. Main remoto seguía en `1d3bd2e` al iniciar; es ancestro de la base UX. No se alteraron ni integraron ramas remotas.

## Qué es ejecutable

Laboratorio → Demostración aplicada → Pronóstico retrospectivo. Seleccionar municipio del panel, uno de los cuatro métodos B06 y un corte permitido; pulsar Ejecutar. Configurar y navegar no entrenan. Se conservan los otros tres componentes de Science Demo, las doce fases, cinco vistas históricas y Observatorio B08.

El único servicio de modelos usado por el módulo es `generar_pronostico()` de B06-I2. No se modificó. El proceso de ajuste recibe únicamente el prefijo hasta el corte inclusivo: ni valores ni fechas objetivo posteriores. El consumidor usa después esos objetivos para evaluación. Las métricas antiguas agregadas no intervienen.

## Fuente y compatibilidad temporal comprobadas

Panel original `data/processed/panel_casos.parquet`: 1124 filas y 832 columnas, DatetimeIndex técnico sin zona horaria, 831 diferencias exactamente de siete días. Se conserva ese índice, sin reindexar, interpolar, redondear o inventar fechas. B06 es estructuralmente compatible con el prefijo de esta malla. La carga rechaza otro tipo de índice; un prefijo con fechas incompatibles bloquea la ejecución sin repararlo.

Estas fechas NO son el calendario epidemiológico oficial. El panel heredado combina eventos 210+220, suma S53 a S52 y completa ausencias con cero. No se puede recuperar de él la distinción original cero/ausencia. Esto se declara visiblemente y no se traslada a B03/B05. No hay conexión del Observatorio con B06.

El catálogo municipal se ordena por código, nunca por conteos del futuro. Es una elección manual retrospectiva sobre el universo ex post del panel, no una cohorte causal certificada ni selección territorial aprobada. El histórico, incluidos los bloques llamados prueba, ya fue examinado. No se afirma prueba independiente ni evaluación epidemiológica validada.

## Cortes y evaluación

Se usa B10 con límites exclusivos 728/780/832, horizonte 8, paso 4 y cohorte inicial fija. Se ofrecen sus 24 orígenes completos; 775 y 827 no se ofrecen porque B10 los descarta. La configuración libre de Science Demo no modifica estos cortes ni hereda sus resultados. IA-I1 solo ejecuta un origen a la vez.

En cada origen el modelo recibe [0,corte+1). Los ocho objetivos posteriores solo se evalúan cuando sus posiciones, fechas técnicas y valores están alineados y son válidos. Sin horizonte completo no hay métricas parciales ni imputación. MAE y RMSE reutilizan forecast_metrics.py. MASE usa exclusivamente ese prefijo y retardo técnico heredado 52; insuficiencia o escala cero produce null con motivo. La cobertura de intervalos es nominal y retrospectiva, no calibración poblacional. No se eligen hiperparámetros.

## Ensayo real ejecutado

Cali · 76001, corte inclusivo 779, 780 observaciones de entrenamiento, horizonte ocho. Fecha técnica del corte: 2021-12-06. Objetivos 780–787: fechas técnicas 2021-12-13 a 2022-01-31; no deben relabelarse como semanas epidemiológicas oficiales ni confundirse con el rótulo histórico 2022 por bloques de 52.

Observados del panel: **57, 66, 57, 48, 68, 51, 50, 58**.

| Método | MAE | RMSE | MASE | Ajuste |
|---|---:|---:|---:|---|
| ultimo_valor | 23.125000 | 24.101349 | 0.155400 | no_requiere_ajuste |
| ingenua_estacional | 112.500000 | 115.090182 | 0.756002 | no_requiere_ajuste |
| sarima_sin_estacional | 28.695662 | 29.489060 | 0.192835 | convergente |
| sarima_estacional | 28.213683 | 29.082198 | 0.189597 | convergente |

SARIMA no estacional: converged=True, 11 iteraciones, warnflag=0. SARIMA estacional: converged=True, 23 iteraciones, warnflag=0. Ambas variantes ofrecen intervalo nominal 95 % y cobertura retrospectiva 8/8 en este tramo; eso no valida su calibración. El último valor obtiene menor error en este ensayo: no se afirma superioridad general de ningún método.

Predicciones SARIMA no estacional:

| Posición | Observado | Predicción | Inferior nominal 95 % | Superior nominal 95 % |
|---:|---:|---:|---:|---:|
| 780 | 57 | 85.887740 | 51.366514 | 143.166162 |
| 781 | 66 | 85.505883 | 46.329020 | 157.111616 |
| 782 | 57 | 85.529803 | 42.325346 | 171.818168 |
| 783 | 48 | 85.528302 | 39.065132 | 185.874388 |
| 784 | 68 | 85.528396 | 36.319615 | 199.622736 |
| 785 | 51 | 85.528390 | 33.955450 | 213.191557 |
| 786 | 50 | 85.528390 | 31.885994 | 226.670244 |
| 787 | 58 | 85.528390 | 30.051498 | 240.120811 |

## Identidad, fallos y recursos

Cada solicitud enlaza SHA-256 del panel, código, método, corte, horizonte, alpha, protocolo y valores/fechas del prefijo mediante request_id. El resultado debe devolver ese identificador. Cambiar serie, método, corte o identidad de fuente invalida la salida de sesión. La evaluación rechaza una respuesta de otra configuración. No hay reintentos ni sustitución automática de método.

Un proceso aislado por ejecución, un slot activo por proceso servidor, entrenamiento máximo 832 posiciones, horizonte fijo ocho, 45 s de límite externo (incluido arranque), bibliotecas numéricas limitadas a un hilo. Timeout termina el hijo y publica un error sin curva parcial. Se usa el control de convergencia estricto existente de B06: rechazos, no convergencia y fallos no entregan predicciones parciales. No se promete un límite duro de RSS ni soporte multiusuario distribuido; se acota la demostración local.

Los errores y advertencias B06, diagnóstico de convergencia y parámetros se conservan en la vista técnica y exportación. La gráfica solo muestra 52 posiciones de contexto pero el servicio recibe el prefijo completo; no se confunden ambos tamaños. Bandas nominales sin marcadores de alerta.

## Evidencia y reproducción

La interfaz permite exportar un JSON nuevo del ensayo completo, con prefijo, configuración, fuente SHA-256, predicciones por periodo, observados posteriores, métricas, parámetros, diagnósticos, advertencias, versiones y limitaciones. Cuatro ejecuciones explícitas quedaron en `docs/experiments/ia_i1_cali_779_*.json`. No son reportes históricos sustituidos ni modelos persistidos para inferencia futura. El panel derivado procede de los originales SIVIGILA del proyecto; preservar atribución y licencia documentadas en data/README.md y B13.

```powershell
Set-Location 'C:\Proyecto IA\episentinel-ai'
.\.venv\Scripts\python.exe -B -m streamlit run app/platform_app.py --server.address 127.0.0.1 --server.port 8513 --server.headless true --browser.gatherUsageStats false
# Guardar otra ejecución en una ruta NUEVA; no sobrescribir evidencia:
.\.venv\Scripts\python.exe -B scripts/run_retrospective.py --series 76001 --cut 779 --method sarima_sin_estacional --output docs/experiments/ia_i1_cali_repeticion.json
```

El script rechaza salidas existentes o fuera de docs/experiments. Cada corrida vuelve a usar B06 explícitamente. No se garantiza igualdad bit a bit entre otras versiones de dependencias; las pruebas contrastan predicciones con tolerancia numérica estricta en el entorno registrado.

## Protección de trabajo y pruebas

Science Demo I1 quedó preservado en `science-demo-i1-protected-before-ia.zip` (ocho archivos) y `science-demo-i1-before-ia.patch` en la carpeta externa de evidencia de la sesión. La rama Science Demo conserva su referencia. UX-I1 está publicado en su rama y B13 conserva backup/b13-before-ux-i1 y ux-i1-baseline. Ningún respaldo requiere reset hard, clean, stash ni commits no autorizados.

Pruebas: prefijo sin futuro, métricas con futuro inválido, cambios de identidad, fechas incompatibles sin conversión, MASE no evaluable, historial insuficiente, series constantes, timeout, slot ocupado, no entrenamiento al configurar, invalidación y no convergencia sin curva. Cuatro métodos ejecutados realmente con el panel local y contrastados contra evidencias guardadas. Nuevas comprobaciones de bandas exactas y rechazo de resultado ajeno.

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_retrospective.py tests/test_applied_demo.py tests/test_forecast_service.py tests/test_sarima_service.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Primera ejecución específica: 250 aprobadas; primera regresión: 790 aprobadas. Repetición final: 792 pruebas completas aprobadas en 74,14 s y 17 pruebas propias IA-I1 aprobadas. Revisión real en navegador: cero gráficas antes del botón, SARIMA convergente con banda 95 %, cambio de método invalida, baseline solo tras botón y sin intervalos. Captura ia-i1-sarima-browser.jpg en la carpeta de evidencia externa.

## IA-I2 — pendientes concretos

- Calendario epidemiológico acreditado, continuidad, faltantes, eventos y población de estudio antes de usar nuevas cargas B03/B05. No recuperar falsamente esos datos desde el panel con ceros heredados.
- Universo y selección causal de cohorte ratificados, decisiones congeladas tras validación y evaluación rolling origin completa; un ensayo manual no sustituye esa evaluación.
- Ensayos predeclarados con tasas de fallo, soporte común, calibración y múltiples series; no seleccionar ganador ni hiperparámetros usando prueba ya observada.
- Persistencia versionada y gestión de ejecuciones concurrentes si se necesita producción; el ajuste no se almacena como modelo desplegado.

No se modifican servicios B03–B10, contratos, configuraciones epidemiológicas, datos ni reportes históricos. Publicación autorizada en commit y PR propios, sin merge ni cierre automático de Issues.


## Orden de integración

Al preparar la publicación, origin/main seguía en 1d3bd2e. UX-I1 (18fd3fd) tiene PR #29 abierto. Science Demo I1 se publica contra feat/ux-i1; IA-I1 contra feat/science-demo-i1. Cada PR muestra solo su incremento. Revisar e integrar en ese orden, sin fusionar automáticamente. Después de cada integración, comprobar el diff y cambiar la base del siguiente PR a main cuando corresponda. Si se integra mediante squash/rebase, reconciliar únicamente el commit propio pendiente; no mezclar otra vez los commits de dependencias ni asumir que un cambio de base es suficiente.
