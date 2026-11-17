# Plataforma I2 — Laboratorio de las doce fases

## Base y arranque

PR #23 confirmado integrado en main, commit `67984a39a22672732a22ef18c6aa05f3f84363ea`.
El árbol local estaba limpio. Rama nueva: `feat/platform-i2`, desde esa referencia
actualizada, sin modificar main ni descartar trabajo. No se crean commits ni se
publica I2 sin autorización.

```powershell
cd "C:\Proyecto IA\episentinel-ai"
.\.venv\Scripts\python.exe -B -m streamlit run app/platform_app.py --server.address 127.0.0.1 --server.port 8504 --server.headless true --browser.gatherUsageStats false
```

Se conserva la entrada principal. El puerto 8504 permite revisar I2 sin interrumpir
instancias previas. No se requiere una dependencia nueva.

## Experiencia científica

El Laboratorio abre en **Recorrido científico**, con cuatro capítulos y doce fases:

1. Problema y datos: problema, recolección, EDA, limpieza/preparación.
2. Diseño experimental: características, partición temporal, algoritmo.
3. Entrenamiento y evaluación: entrenamiento, hiperparámetros, evaluación.
4. Generalización y despliegue: generalización, despliegue.

Capítulo y fase pueden seleccionarse directamente o con Anterior/Siguiente.
La selección se conserva al cambiar de capítulo, de modo o de ambiente.
Cada fase muestra objetivo, método, resultado y alcance, estado, limitaciones,
pendientes y fuentes reproducibles. Un mapa de evidencia reúne las doce fases.
Los documentos y resultados se descargan desde el detalle; no se expone JSON
crudo como contenido principal ni se ejecutan las instrucciones de reproducción.

Los accesos contextuales abren las figuras originales en **Vistas históricas**.
Las cinco vistas permanecen disponibles. La fase 10 reutiliza las barras y tablas
de evaluación existentes; la fase 6 representa los cortes del split como una
línea temporal técnica, sin inferir fechas. La fase 4 lee el embudo guardado;
la fase 2 verifica fuentes por SHA-256. El esquema de fase 5 ilustra el código,
no simula una ejecución. La fase 11 muestra parámetros rolling origin como
configuración pendiente, no como resultados.

## Estado científico, distinto de cobertura de interfaz

Las doce fases están documentadas; eso no significa doce fases completadas.
Solo recolección puede aparecer **Completo con evidencia**, y únicamente para
los originales conservados cuando coinciden las tres huellas B02 y existen sus
documentos/auditoría. No equivale a aceptar los originales como nuevas cargas
ni a acreditar cobertura epidemiológica. Si faltan fuentes o cambian huellas,
se muestra Parcial. Hiperparámetros permanece Pendiente; las otras diez son
Parcial. Ninguna gráfica o documento por sí solo cambia ese criterio.

Se identifican las reglas heredadas: 210+220, S53 sumada a S52, malla técnica de
52 posiciones y ausencias completadas con cero. B03/B08 conservan eventos
independientes y faltantes; ambos universos no se intercambian.

La selección municipal utiliza información del periodo completo. La evaluación
no se declara libre de fuga, SARIMA no recibe superioridad general y la prueba
2022 no demuestra generalización amplia. No se inventa ajuste de hiperparámetros,
rolling origin ejecutado, variables externas, modelo serializado ni despliegue
público. Los promedios mostrados se derivan del CSV guardado, sin recomputar MAE,
RMSE o MASE ni ajustar modelos.

El recorrido describe los experimentos del proyecto y no los resultados de la
carga vigente del Observatorio. B08, sus estados y su invalidación se conservan.
B03/B04/B05/B06/B07 y los módulos científicos no se modifican. No se conecta
B06 a B03 ni se llama B07 desde el Observatorio. Pronósticos/señales históricos
mantienen sus botones explícitos.

## Disponibilidad y reproducción

`lab_evidence.py` contiene el catálogo y lectura de archivos nombrados;
`lab_app.py` compone la navegación y presenta evidencia. El contexto se almacena
en caché por raíz, disponibilidad, tamaño y fecha de modificación de las fuentes.
La comprobación de huellas ocurre sobre los archivos locales; no descarga datos.
La caché supone que una sustitución externa cambia tamaño o fecha de modificación.

El panel local sigue siendo necesario para sus visualizaciones. La comparación
guardada funciona sin panel. Si faltan o son inválidos los reportes o el split,
se informa sin fabricar métricas o cortes. No se reconstruyen salidas.

Las instrucciones de cada fase distinguen lectura, pruebas sintéticas, ajuste
explícito y tareas todavía sin implementación. No ejecutar scripts históricos
de reconstrucción sobre archivos existentes para demostrar I2.

## Verificación

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_lab_app.py tests/test_platform_app.py tests/test_analysis_app.py tests/test_analysis_presenter.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
git diff --check
```

Las pruebas nuevas usan evidencia temporal sintética: recorrido de doce fases,
cuatro capítulos, estados científicos conservadores, hashes alterados, ausencia
y corrupción de reportes, cortes configurados, actualización de evidencia,
retorno desde figuras y conservación de sesión B08. Se prohíben ajustes de
modelos durante las pruebas de navegación. Las pruebas I1 conservan su alcance,
adaptando únicamente el acceso a Vistas históricas y el selector de modelo.

Pendientes científicos: calendario/catálogos, cobertura, selección libre de fuga,
experimentos versionados, ajuste por validación temporal, origen móvil y despliegue.
La interfaz I2 los hace verificables; no los resuelve por presentarlos.

## Evidencia ejecutada — 16 de noviembre de 2026

- Versión final: 43 pruebas específicas aprobadas (30,23 s) y 452 totales (34,01 s), sin omisiones.
- Recorrido real en navegador por los cuatro capítulos y las doce fases; cortes configurados 728/52/52 y comparación histórica de 24 resultados, seis series y cuatro métodos.
- Confirmadas la fase de hiperparámetros pendiente y las limitaciones de generalización/despliegue.
- Acceso contextual EDA → Territorio y patrones → retorno al recorrido científico.
- CSV real b08_demo.csv aceptado por B08; Cali 76001, evento 220, perfil de tres periodos; resultado 2/3 observado, una ausencia sin convertir a cero.
- Cambios Observatorio → Laboratorio → Observatorio conservaron el resultado real; el capítulo 3/fase 9 se restauró al volver al Laboratorio.
- Revisión visual del recorrido y figuras en el navegador disponible, a 1280 × 720. No constituye auditoría exhaustiva de accesibilidad ni de dispositivos móviles físicos.
- Huellas SHA-256 idénticas antes/después en 13 archivos de data/raw, data/processed y reports, incluidos marcadores.
- git diff --check sin errores. Sin cambios en src/episentinel, configuraciones, scripts, reportes, B08 o el renderizador histórico.
- Ocho archivos nuevos/modificados de I2, sin staging, commit, push, PR ni merge.

## Preparación de publicación — 17 de noviembre de 2026

Tras git fetch origin, main permanece en 67984a3. La rama feat/platform-i2 conserva ocho archivos de interfaz, evidencia, documentación y pruebas. Se prepara su publicación con Refs #8 para los criterios académicos de la Fase 3; no se realiza merge ni cierre automático del Issue. La ausencia de commits/publicación en la sección del 16 de noviembre describe el estado de aquella verificación.
