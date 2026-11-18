# UX-Demo I1 — Registro manual y trazabilidad de particiones

Rama: `feat/ux-demo-i1`. Referencia estable: `8062d80c209cfe70fdadba0af57954c0d871da51`.
Entrada oficial y respaldo B13 conservados. No se modifican contratos ni módulos científicos.

## Arranque

Desde `C:\Proyecto IA\episentinel-ai`, con las dependencias ya instaladas:

```powershell
.\.venv\Scripts\python.exe -B -m streamlit run app/platform_app.py --browser.gatherUsageStats false
```

Se requiere el entorno existente y los artefactos locales para las vistas históricas y el pronóstico retrospectivo. El registro manual no depende de los paneles históricos.

## Qué representa una fila

El contrato CSV v1 vigente (`src/episentinel/data/csv_contract.py` y `csv_loader.py`) exige exactamente estos campos:

| Campo | Captura y validación reutilizada |
|---|---|
| `cod_mun` | Texto de cinco dígitos; reglas territoriales sintácticas B04. Conservar ceros iniciales. Catálogo oficial pendiente. |
| `ano` | Año entero de cuatro dígitos, 1000–9999. |
| `semana` | Entero 1–53; no acredita calendario epidemiológico oficial. |
| `cod_eve` | Evento 210, 220 o 580. La interfaz muestra los nombres existentes. |
| `conteo` | Entero no negativo. Cero explícito válido. Vacío, decimales, signos o separadores de miles se rechazan. |

Una fila es un conteo declarado por municipio, año, semana y evento. No es un paciente ni necesariamente una semana nueva. La clave es `(cod_mun, ano, semana, cod_eve)`. Dos eventos en el mismo periodo son registros distintos, no dos posiciones temporales de una serie.

## Ruta de validación y procedencia

`app/input_components.py` captura los cinco campos sin reinterpretarlos. `app/session_input.py` produce CSV en memoria con `csv.DictWriter` y los campos del contrato existente. El conjunto candidato completo pasa por **B04 `load_csv()`**, igual que un CSV cargado. Si se acepta, `analysis_presenter.set_source()` invalida la lectura anterior y el análisis explícito continúa por B05/B03. No hay otra lógica científica ni llamadas de entrenamiento.

Los errores rechazan el intento completo: no se reemplaza, agrega ni suma una clave duplicada o conflictiva. Los registros anteriormente aceptados permanecen intactos. Los diagnósticos conservan códigos, columnas y registros de B04.

CSV y manual son conjuntos separados por defecto. La casilla de combinación exige consentimiento explícito y vuelve a validar todas las claves CSV + manual. Un conflicto impide combinar, preservando el conjunto anterior. El archivo original no cambia. Cambiar o retirar CSV revoca la combinación anterior.

Todo permanece en la sesión de Streamlit. El límite de interfaz es 1000 registros manuales; no hay persistencia automática ni información personal. Se pueden descargar el CSV activo y su manifiesto de procedencia. El manifiesto incluye UUID de sesión, versión local, SHA-256 del conjunto, huella del CSV original cuando corresponde, registros manuales y una vista previa de procedencia limitada a 100 filas. No certifica veracidad epidemiológica ni entrenamiento. Una nueva sesión vacía ambos conjuntos y sus resultados; conviene exportar antes de reiniciarla.

## Ensayo reproducible del formulario

1. Observatorio → Comenzar análisis → Registro manual. Contadores activos en cero.
2. Agregar `76001,2020,52,210,0`: un registro manual, un válido, total uno.
3. Agregar `76001,2020,53,210,4`: dos manuales, dos válidos, total dos.
4. Intentar el mismo segundo registro con conteo `-1`: rechazo por tipo/rango canónico; total sigue dos.
5. Intentar la misma clave con conteo `9`: conflicto; total sigue dos. Intentos rechazados: dos.
6. Continuar a territorio → 76001 → Dengue 210 → Tres periodos documentados 2020–2021 → Analizar observaciones.
7. Resultado: `[0, 4, ausente]`, dos observaciones en tres posiciones, cobertura 2/3. El cero tiene punto observado; la ausencia tiene marcador ámbar y ningún conteo inventado.
8. Consultar «Conjunto activo, procedencia y relación con particiones»: identidad, versión, huella, procedencia, observaciones y motivos que impiden entrenar.
9. Cambiar a CSV: lectura previa invalidada; manuales conservados fuera del conjunto activo. Subir `data/processed/b08_demo.csv` mediante el selector de archivos.
10. CSV real: cinco registros, cinco válidos. Evento 210: `[142,112,150]`, cobertura 3/3. Evento 220: `[2,2,ausente]`, cobertura 2/3. Cambiar evento invalida la lectura previa antes de volver a analizar.
11. Visitar B10 o IA-I1 y regresar conserva la lectura de la misma configuración. «Nueva sesión del Observatorio» elimina ambas fuentes y resultados; todos los contadores quedan en cero y cambia la identidad.

Los registros manuales de los pasos 2–5 son declaraciones de prueba del formulario, no observaciones reales acreditadas ni adiciones al histórico.

### Contadores

| Momento | CSV activo | Manual activo | Válidos B04 | Rechazados / pendientes activos | Total activo | Intentos manuales rechazados |
|---|---:|---:|---:|---:|---:|---:|
| Inicio | 0 | 0 | 0 | 0 / 0 | 0 | 0 |
| Primer registro válido | 0 | 1 | 1 | 0 / 0 | 1 | 0 |
| Segundo registro válido | 0 | 2 | 2 | 0 / 0 | 2 | 0 |
| Dos intentos rechazados | 0 | 2 | 2 | 0 / 0 | 2 | 2 |
| Cambiar a CSV vacío | 0 | 0 | 0 | 0 / 0 | 0 | 2 |
| CSV real de demostración | 5 | 0 | 5 | 0 / 0 | 5 | 2 |
| Nueva sesión | 0 | 0 | 0 | 0 / 0 | 0 | 0 |

Se muestra adicionalmente cuántos registros CSV y manuales permanecen en memoria, aunque estén fuera del conjunto activo. No se suman los registros históricos heredados. En un CSV bloqueado, B04 entrega cero registros válidos; las filas con errores se distinguen de las pendientes. Ejemplo probado: tres filas, una con error → cero válidas, una rechazada y dos pendientes. Los intentos manuales rechazados no pertenecen al conjunto activo.

## Relación real con particiones B10

B03 conserva `eligibility.status = not_evaluated`, fechas sin asignar y catálogo pendiente. La malla del Observatorio sigue siendo el perfil provisional existente de tres periodos. No se convierte automáticamente una fila manual en semana fechada o en entrenamiento.

La vista contextual muestra las posiciones declaradas, observaciones y ausencias por serie. Las posiciones elegibles y las particiones se identifican como **no acreditadas**, sin cantidades inventadas de entrenamiento/validación/prueba. También informa que B10 exige ocho objetivos de validación y ocho de prueba, más entrenamiento no vacío: 17 posiciones es una condición mínima necesaria, no una aprobación científica. Tres posiciones no alcanzan.

El botón al planificador B10 abre el componente existente en el Laboratorio, claramente independiente del CSV/manual. Su ejemplo de 832 posiciones conserva cortes enteros y ventanas válidas/descartadas; no se atribuyen sus posiciones ni métricas al conjunto del Observatorio. Ningún control ejecuta SARIMA o selecciona hiperparámetros con prueba.

Para analizar otras etiquetas temporales se necesita una malla explícita compatible y su procedencia. La aceptación estructural B04 de una fila fuera del perfil no garantiza que B03 pueda analizarla. Ampliar calendario, elegibilidad y particiones del conjunto activo queda pendiente de decisiones científicas.

## UX conservada y acceso a IA

Se preservan las doce fases, cinco vistas históricas, B13, demostración aplicada y Observatorio B08. Se añaden acceso directo al pronóstico retrospectivo desde Inicio, regreso desde análisis a fuentes y evidencia avanzada de procedencia en desplegable. No se introduce un rediseño ni dependencias nuevas. IA-I1 mantiene su ejecución exclusivamente por botón y sus resultados históricos separados de la sesión del Observatorio.

## Verificación

Pruebas nuevas: `tests/test_session_input.py` y `tests/test_manual_app.py` (26 casos). Incluyen equivalencia exacta con B04, múltiples registros, entradas inválidas, duplicados y conflictos, combinación entre fuentes, contadores, cero/ausencia, invalidación, aislamiento de sesiones, navegación, ausencia de entrenamiento y escritura de archivos.

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_session_input.py tests/test_manual_app.py tests/test_analysis_app.py tests/test_platform_app.py
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Resultado del incremento: 43 pruebas focalizadas y 818 totales aprobadas. Recorrido real en navegador: ingreso manual aceptado/rechazado, dos registros, cero/ausencia, CSV por selector de archivos, eventos 210/220, invalidación, salto a B10, acceso directo a IA-I1 sin ejecución y reinicio de sesión. Las trece huellas históricas de referencia permanecen idénticas. Ningún cambio en módulos científicos, configuraciones, contratos o reportes.

Capturas locales entregadas con el incremento: `ux-demo-manual-form.jpg`, `ux-demo-counters.jpg`, `ux-demo-manual-analysis.jpg`, `ux-demo-csv-220.jpg` y `ux-demo-partitions.jpg`, en la carpeta de evidencias externa al repositorio. No se añaden capturas ni datos generados al código.

**Veredicto: APTO CON OBSERVACIONES para demostrar captura y validación reales.** La asignación del conjunto activo a entrenamiento sigue bloqueada explícitamente por sus condiciones científicas; no se presenta como funcionalidad completada.


## Cierre y refinamiento para proyección

El formulario conserva sus cinco campos y validaciones, ahora en una sola fila en escritorio. El botón de agregar usa petróleo `#102F3A` con texto blanco; los campos tienen fondo blanco, texto oscuro y etiquetas de 14 px. Se reducen instrucciones repetidas y márgenes del panel. Las notas de interfaz usan 13 px y contraste más alto.

La primera línea prioriza total activo, válidos entregados por B04 e intentos manuales rechazados. CSV/manual, rechazados/pendientes y procedencia permanecen en «Desglose CSV/manual y procedencia de la sesión». Los intentos rechazados son acumulados de la sesión y no se suman a las filas activas. Se informa expresamente que aceptar registros no los incorpora al entrenamiento histórico.

Revisión real a **1366×768 y 1920×1080**: los cinco campos caben, el botón tiene fondo RGB(16,47,58), y el rechazo por conflicto conserva dos filas aceptadas. La sesión de revisión ya tenía un intento rechazado anterior; después de probar negativo y conflicto muestra tres intentos y total dos. Estos contadores son reales, no cifras de ejemplo fijadas en pantalla.

Se repitieron carga de `b08_demo.csv` por selector, análisis del evento 220 (2/3), cambio de fuente e invalidación, B10 independiente (19 ventanas de validación, 20 de prueba y tres descartadas en su ejemplo predeterminado), acceso al pronóstico en un clic desde Inicio y conservación de la lectura al regresar. IA-I1 sigue sin ensayo ejecutado por navegar. El análisis manual mantiene `[0,4,ausente]`.

Capturas finales externas al repositorio: `ux-demo-refined-1366-full.png`, `ux-demo-refined-1920x1080.png`, `ux-demo-refined-counters-1366.png` y `ux-demo-refined-observatory-1366.png`. Las capturas se obtuvieron con el tamaño de navegador indicado; no son diseños simulados. El avance previo al refinamiento se conserva en un ZIP externo y el respaldo Git B13 sigue disponible.

Verificación de cierre: **43 pruebas focalizadas y 818 totales aprobadas**, sin nuevas dependencias ni modificaciones científicas; trece huellas históricas idénticas. La prueba de interfaz comprueba además el orden prioritario de métricas y su desglose secundario. Se conserva el veredicto APTO CON OBSERVACIONES: calendario, elegibilidad y entrenamiento del conjunto activo siguen pendientes y visibles.
