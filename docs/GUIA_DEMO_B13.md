# B13-I1 — Guía reproducible de sustentación

**Fecha:** jueves 19 de noviembre de 2026. **Equipo:** DKK, EpiSentinel AI.
**Referencia científica y de aplicación:** `ef6e2e770a9f075bc73fdcb28d3bd855b44ceec9`
(PR #27 integrado, después de #23–#26). Rama de preparación: `feat/b13-i1-demo`.
La referencia identifica la aplicación evaluada; esta guía, el preflight y sus
pruebas son cambios B13 locales hasta que se autorice publicarlos.

## 1. Propósito y alcance

Demostrar dos ambientes complementarios: Laboratorio científico y Observatorio
interactivo. Doce fases documentadas no equivalen a doce fases completadas.
Separar siempre **resultados históricos guardados**, **servicios implementados**
y **experimentos pendientes**. B13 no añade modelos, no corrige la evaluación
histórica y no conecta B06 al Observatorio.

## 2. Entorno preparado, sin instalaciones durante la exposición

Carpeta: `C:\Proyecto IA\episentinel-ai`. Usar su `.venv\Scripts\python.exe`.
No actualizar Python ni paquetes antes del ensayo final; no ejecutar pip durante
la exposición. La instalación de esta máquina tiene Python 3.13.4, pandas 3.1.0,
NumPy 2.5.4, statsmodels 0.15.0, scikit-learn 1.9.1, pyarrow 26.0.0, openpyxl 3.1.5,
Streamlit 1.67.0, Plotly 7.1.0 y pytest 9.1.1. Son versiones observadas, no nuevos
requisitos universales ni una garantía de portabilidad de `.venv`.

Otro equipo debe prepararse y probarse antes del 19, con `pip install -e ".[dev,app]"`
y los mismos artefactos permitidos. No copiar una `.venv` suponiendo que es portátil.
La demo principal no necesita Prophet, tokens, cuentas, Internet ni una base remota.

### Comprobación previa de solo lectura

```powershell
cd "C:\Proyecto IA\episentinel-ai"
.\.venv\Scripts\python.exe -B scripts/preflight_demo.py
```

Comprueba imports/versiones, archivos, estilos, hashes, CSV/manifiesto/perfil,
construcción B04 → B05 → B03 y disponibilidad de la comparación y del plan B10.
No descarga, instala, repara, sobrescribe ni ajusta modelos. Devuelve 1 si encuentra
errores. `APTO CON OBSERVACIONES` puede deberse al trabajo B13 pendiente de commit
o a una referencia diferente; revisar el detalle, no ignorarlo automáticamente.
No certifica por sí solo el renderizado ni valida desempeño epidemiológico.

## 3. Artefactos que deben viajar con la instalación

| Artefacto | Uso / dependencia |
|---|---|
| `app/platform_app.py` y módulos de `app/` | Entrada oficial, navegación, B08 y Laboratorio |
| `app/analysis_styles.css` | Identidad y controles; estilos y fuentes de reserva locales |
| `configs/ui_period_grids.json` | Perfil de tres periodos, procedencia y verificación pendiente |
| `configs/split.json` | Cortes históricos; no calendario oficial |
| `configs/evaluacion_b10.json` | Ejemplo de planificación posicional B10; no ejecución real |
| `data/processed/b08_demo.csv` | Cinco observaciones reales de Cali, 210/220 |
| `data/processed/b08_demo_manifest.json` | Huella, atribución, transformaciones y cinco referencias originales |
| `data/processed/panel_casos.parquet` | Panorama, EDA, pronósticos y señales históricos |
| `data/processed/municipios.csv` | Nombres territoriales; sin él, la app puede usar códigos |
| `reports/comparacion_fase2.csv` | Evaluación histórica independiente del panel |
| `reports/comparacion_fase2.json`, `reports/ingest_report.json` | Copia equivalente de evaluación y reporte de limpieza |
| `data/raw/Dengue_210.csv`, `Dengue_220.csv`, `Dengue_580.csv` | Procedencia/hash de originales; fase 2 completa para las copias conservadas |
| `data/processed/panel_muertes.parquet` | Artefacto histórico conservado; no necesario para el gráfico B08 |
| `docs/`, código `src/` y entorno instalado | Evidencia local, contratos y funcionamiento |

Los datos ignorados no están en Git. Un clon limpio no basta para repetir el
recorrido completo. No sustituir originales por una descarga nueva ni reconstruir
paneles durante la sustentación. Mantener atribución y condiciones documentadas.

### Huellas principales de esta instalación

| Archivo | SHA-256 |
|---|---|
| `b08_demo.csv` | `09ef879677aa4ada53f27c2e6f305ff55fcf12068804d4d0e78497b9c14ca6f6` |
| `panel_casos.parquet` | `41e592e9fb548085377a1c6d7ed7de026496d8c530583ba5aaf6c80e2fee5989` |
| `comparacion_fase2.csv` | `efa45e3adcc51d90c669bffcb9d5beef6e41d19e2edaaf40bb163782fcf94830` |
| `ingest_report.json` | `e380bcdefb8280a78f96196c5456dbcbfe0510529cfa0f87ca13ac49d401e4f2` |

El preflight contiene y verifica las once huellas de artefactos, incluidos los tres
originales. Son identidades de bytes de esta instalación: no probarlas implica
riesgo de mezclar versiones. Una diferencia no se arregla editando el archivo o
regenerándolo en el momento; recuperar la copia conservada y repetir el ensayo.

## 4. Arranque oficial verificado

```powershell
cd "C:\Proyecto IA\episentinel-ai"
.\.venv\Scripts\python.exe -B -m streamlit run app/platform_app.py --server.address 127.0.0.1 --server.port 8507 --server.headless true --browser.gatherUsageStats false
```

Abrir `http://127.0.0.1:8507`. Mantener esa terminal abierta. Esperado: identidad
EpiSentinel y navegación superior Observatorio / Laboratorio / Evidencia.
No usar como entrada oficial las aplicaciones independientes antiguas.

La aplicación utiliza recursos instalados y archivos locales; los enlaces a INS,
datos.gov.co o licencias son referencias, no requisitos del recorrido. No abrirlos
durante el ensayo sin Internet. Los contratos ya están en `docs/` y en la interfaz.

## 5. Guion del Laboratorio — estimación de 7–9 minutos

Los tiempos son estimaciones de exposición, no mediciones de rendimiento ni de ajuste.

| Paso | Acción reproducible | Resultado esperado / mensaje para el profesor |
|---|---|---|
| Entrada, 30 s | Laboratorio → Recorrido científico | Cuatro capítulos y doce fases; estados escritos. El histórico no corresponde al CSV de sesión. |
| Capítulo 1, 2 min | Problema y datos → fases 1, 2, 3 y 4 | Objetivo municipal/semanal; originales identificados por huellas; limpieza y ausencias explícitas. Fase 2 completa solo para originales conservados. |
| EDA, dentro del capítulo 1 | Fase 3 → Explorar vista histórica · Territorio y patrones | Mapas de calor y perfiles reales. Volver a Recorrido científico conserva la fase. También está disponible Panorama con curva y barras. |
| Capítulo 2, 2 min | Diseño experimental → fases 5, 6 y 7 | log1p/escala original; configuración 728/52/52; cuatro métodos. Explicar selección territorial retrospectiva del histórico. |
| Capítulo 3, 2 min | Entrenamiento y evaluación → fases 8, 9 y 10 | Entrenamiento implementado, hiperparámetros pendiente y evaluación guardada. Fase 10 muestra 24 registros, seis series y cuatro métodos. |
| Capítulo 4, 1 min | Generalización y despliegue → fases 11 y 12 | Origen móvil y despliegue aún sin evidencia de ejecución real completa. Código de servicio no equivale a modelo desplegado o validado. |
| Servicios, 30–60 s | Evidencia y metodología → Metodología y contratos → B06-I2 | Último valor, ingenua estacional y dos SARIMA. Estimaciones/intervalos condicionados a éxito; convergencia no acredita eficacia epidemiológica. |

No pulsar los botones de cálculo SARIMA/señales en el recorrido principal. Las
vistas Pronósticos y Señales de alerta pueden abrirse sin ajustar modelos. La
comparación guardada basta para demostrar resultados existentes. Un cálculo
opcional debe anunciarse como retrospectivo y explícito; no es una predicción
del CSV B08 ni una nueva evaluación validada.

### Resultados históricos que sí podemos citar

El evaluador ajustó con 2007–2021 y pronosticó 52 posiciones de 2022. Nacional y
cinco municipios; selección retrospectiva. MASE medio guardado: último valor
0,194168; SARIMA estacional 0,213113; SARIMA sin estacionalidad 0,214962;
ingenua estacional 0,270374. No hay superioridad general demostrada de SARIMA.

El histórico suma 210+220, pliega S53 a S52, usa fechas técnicas y completa
ausencias con cero. Panorama nacional excluye Exterior; la evaluación guardada
lo incluye. B03/B08 no adoptan implícitamente esas reglas. Las señales históricas
no son brotes confirmados ni resultados validados de B07.

### B10-I1: demostración de planificación — estimación de 1 minuto

Desde otra terminal, sin ejecutar modelos:

```powershell
.\.venv\Scripts\python.exe -B scripts/preflight_demo.py --plan-b10
```

Esperado: plan **posicional ilustrativo**, horizonte 8 y paso 4, cuatro métodos,
12 orígenes de validación y 12 de prueba; colas 775 y 827 excluidas. Cortes válidos:
727…771 y 779…823. Los límites exclusivos B10 728/780/832 corresponden al ejemplo;
no acreditan calendario epidemiológico oficial.

Abrir localmente `docs/CONTRATO_EVALUACION_B10.md` para mostrar `select_cohort()` y
`plan_rolling_origin()`. El contrato B10 todavía no figura en el menú de documentos
de la plataforma; no fingir una integración de interfaz. Universo/criterios reales
siguen en null y `real_execution_authorized=false`. El ejecutor de experimentos,
pronósticos por origen y métricas reales siguen pendientes. El motor causal nuevo
no elimina la fuga de la comparación histórica que ya fue calculada.

## 6. Guion del Observatorio — estimación de 4–5 minutos

1. Observatorio → Inicio → Comenzar análisis.
2. Cargar **el archivo existente** `data/processed/b08_demo.csv`. Esperado:
   «Archivo aceptado». No cargar directamente los originales de nueve columnas.
3. Continuar a territorio. Municipio `76001`; evento **Dengue · 210**; perfil
   **Tres periodos documentados · 2020–2021**. Calendario mostrado como pendiente.
4. Analizar observaciones. Esperado: **3/3**, conteos **142, 112, 150** para
   2020-S52, 2020-S53 y 2021-S01. Son registros, no estimaciones.
5. Revisar archivo, huella, configuración, procedencia y trazabilidad. La huella
   del CSV coincide con la tabla anterior; la cobertura solo describe esta malla.
6. Ir al Laboratorio y volver. Esperado: mismo resultado 210, sin pérdida de carga.
7. Cambiar configuración → **Dengue grave · 220**. Antes de analizar, el resultado
   anterior queda invalidado. Evidencia de sesión debe informar que no hay ejecución
   vigente, no mostrar los datos anteriores como si fueran de 220.
8. Volver al Observatorio y analizar. Esperado: **2/3**, conteos **2, 2, ausente**.
   S01 no se dibuja como cero; S53 sigue siendo un periodo independiente.
9. Mostrar Datos observados y ausencias y la evidencia vigente de 220. No hay
   pronósticos, alertas ni riesgo clínico añadidos a este CSV.

El CSV real no contiene ceros. La preservación de ceros explícitos se comprueba
con fixtures sintéticos en pruebas; no añadir un cero al archivo para ilustrarlo.
Retirar/cambiar archivo también invalida selecciones y resultados. Si se desea
ensayarlo, retirar y volver a seleccionar el mismo archivo, luego repetir 3–4.

## 7. Plan de contingencia

| Problema real | Recuperación conservadora |
|---|---|
| Puerto ocupado | Usar el mismo comando con `--server.port 8510` y abrir esa URL. No terminar procesos desconocidos. |
| Terminal cerrada / servidor detenido | Abrir PowerShell, situarse en la raíz y repetir el comando oficial. Recargar navegador; una sesión nueva requiere cargar y configurar de nuevo. |
| Import o dependencia ausente | Usar la instalación de respaldo ya preparada. No instalar ni actualizar en la exposición. Mostrar guía, contratos y resultados guardados. |
| Panel ausente o huella diferente | Recuperar la copia histórica comprobada. Mientras tanto, Evidencia → Resultados históricos funciona sin panel; no sustituir por datos ficticios. |
| CSV/manifiesto/perfil ausente | Recuperar los archivos conservados con sus hashes. No regenerar durante la exposición. La preparación B08, si hiciera falta, se ensaya antes y en una carpeta aislada. |
| CSV rechazado | Leer el diagnóstico y comprobar que se eligió el derivado canónico. No editar observaciones para superar la validación. |
| Sin Internet | Continuar con app, fuentes locales y contratos. No abrir enlaces externos. |
| Streamlit no recuperable | Usar la salida CSV del comando siguiente y abrir la guía/contratos locales; indicar que se muestran resultados guardados, no una sesión operativa. |

### Respaldo de resultados sin Streamlit ni librerías científicas

```powershell
.\.venv\Scripts\python.exe -B scripts/preflight_demo.py --saved-results
```

Este modo usa biblioteca estándar y muestra exactamente las 24 filas guardadas,
sin recalcular métricas. Puede ejecutarse con otro Python ya instalado si falla
la `.venv`. Alternativa nativa PowerShell:

```powershell
Import-Csv -Encoding UTF8 -LiteralPath .\reports\comparacion_fase2.csv | Format-Table serie,modelo,mae,rmse,mase -AutoSize
Get-Content -Encoding UTF8 -LiteralPath .\docs\GUIA_DEMO_B13.md
Get-Content -Encoding UTF8 -LiteralPath .\docs\CONTRATO_EVALUACION_B10.md
```

También se puede abrir el CSV en un visor ya instalado, sin guardarlo de nuevo.
No ejecutar `evaluate_fase2.py`, `build_panel.py` o `build_lookup.py` como recuperación:
escriben salidas históricas. Conservar una copia local de toda la instalación y
los artefactos permitidos antes del viaje; comprobar la copia antes del 19. No
publicar originales, derivados ni paneles en Git.

## 8. Validación reproducible y alcance sin Internet

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_demo_preflight.py tests/test_lab_app.py tests/test_platform_app.py tests/test_analysis_app.py tests/test_analysis_presenter.py tests/test_series_selection.py tests/test_rolling_origin.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

El ensayo `test_offline_rehearsal_real_artifacts_and_session_isolation` recorre
capítulos/fases y vistas con los artefactos locales, bloqueando conexiones TCP/DNS
Python externas y cualquier ajuste histórico al navegar. Verifica el CSV real,
selecciones, cambios de evento, invalidez y retorno entre ambientes. AppTest recibe
los bytes del archivo mediante las APIs reales; no simula el selector nativo del
navegador. Los dos tests con datos reales se omiten si faltan artefactos locales;
una omisión no sirve como evidencia de ensayo completado en el equipo de exposición.

La carga nativa y el renderizado se revisan por separado en navegador. Las fuentes
de reserva y los recursos de la interfaz son locales. El bloqueo de conexiones
en pruebas no equivale a desconectar físicamente todos los adaptadores del equipo;
permite verificar que el flujo probado no depende de llamadas externas Python.

## 9. Checklist antes de salir y antes de empezar

- [ ] Portátil, cargador, adaptador de proyección y navegador probados.
- [ ] No actualizar entorno después del ensayo aprobado.
- [ ] Commit de referencia y cambios B13 identificados; copia local de respaldo.
- [ ] Preflight sin errores; observaciones de Git explicadas.
- [ ] Originales, panel, nombres, reportes, CSV, manifiesto y perfil verificados.
- [ ] Comando de arranque y puerto alternativo preparados en una terminal.
- [ ] App con estilos; navegación y carga real ensayadas en este equipo.
- [ ] Eventos 210 y 220 reproducen 3/3 y 2/3; S01 ausente no es cero.
- [ ] Evidencia corresponde al evento vigente; cambios invalidan resultados.
- [ ] Guía, contratos y salida histórica disponibles sin abrir enlaces externos.
- [ ] Explicar fuga histórica, límites de calendario/cobertura, intervalos nominales,
      ausencia de etiquetas y diferencia entre planificación B10 y experimento ejecutado.
- [ ] Durante la exposición, no instalar paquetes, regenerar resultados ni pulsar
      ajustes costosos por accidente.

## 10. Registro del ensayo B13

Los resultados ejecutados y las observaciones de esta preparación se registran
al finalizar la verificación; no se deducen de cifras de otros incrementos.

### Resultado ejecutado — 17 de noviembre de 2026

| Comprobación | Resultado de esta preparación |
|---|---|
| Referencia | ef6e2e770a9f075bc73fdcb28d3bd855b44ceec9, rama feat/b13-i1-demo |
| Preflight final | Código 0; APTO CON OBSERVACIONES, solo por tres archivos B13 locales sin commit |
| Pruebas relevantes | 127 aprobadas en 121,56 s; ninguna omitida |
| Suite completa | 745 aprobadas en 174,60 s; ninguna omitida |
| Conservación histórica | 13 archivos idénticos antes/después por SHA-256, incluidos dos marcadores; once artefactos comprobados por preflight |
| Arranque oficial | Instancia nueva 127.0.0.1:8507; HTTP 200 / ok |
| Ensayo offline automatizado | Cuatro capítulos, doce fases y cinco vistas, con TCP/DNS externos bloqueados; ningún intento externo ni ajuste al navegar |
| Observatorio, archivo real | 210: 142/112/150, cobertura 3/3; 220: 2/2/ausente, cobertura 2/3; huella de archivo coincidente |
| Estado de sesión | Resultado 210 conservado al volver del Laboratorio; cambio a 220 invalida resultado y evidencia antes de nueva ejecución |
| B10 | 24 orígenes, dos colas excluidas, cuatro métodos; planificación sin modelos, selección real ni métricas nuevas |
| Respaldo sin Streamlit | Modo --saved-results imprimió las 24 filas preservadas sin importar librerías científicas |
| Navegador | Estilos, navegación, división temporal, evaluación guardada y métodos B06 visibles; scripts y CSS observados de origen local |

Se encontró y corrigió una incompatibilidad de salida con la consola cp1252 de
Windows: el CLI configura UTF-8. La suite final incluye su regresión. No hubo
cambios en datos, paneles, reportes, app/, src/ o configuraciones.

El ensayo real de datos usa AppTest y las APIs existentes; en B13 no se volvió a
operar el selector nativo de archivos. La carga nativa ya tiene evidencia en
DEMO_B08.md; antes de exponer se debe completar el checklist en el equipo de
proyección. Tampoco se desconectó físicamente la red: se bloqueó acceso externo
Python y se comprobaron los recursos locales del navegador.

**Veredicto: APTO CON OBSERVACIONES.** No hay bloqueantes de ejecución en esta
instalación. Conservar el paquete local, completar el ensayo de proyección y
congelar/publicar B13 solo cuando se autorice. Las limitaciones científicas
permanecen visibles; no son resultados adicionales de B13. No se hicieron
commits, push, PR ni merge de B13.
