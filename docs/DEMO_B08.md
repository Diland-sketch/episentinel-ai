# B08-I1 — demostración real reproducible

## Procedencia y política de publicación

Fuente: originales auditados `Dengue_210.csv` y `Dengue_220.csv`, suministrados por
el responsable y vinculados al conjunto institucional `4hyg-wa9d` del Portal
Nacional de Datos Abiertos, atribuido al INS. Descarga histórica declarada:
23/09/2026. Licencia actual verificada: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Ver [manifiesto y límites de procedencia B02](../data/README.md).

La derivación mantiene atribución, referencia de licencia e identificación de cambios
en su manifiesto local. No hay datos individuales. Los conteos son registros
municipales agregados, no predicciones ni cifras inventadas.
Los archivos reales **no se añaden a Git**: se generan en `data/processed`, ya ignorado.
El script rechaza ubicaciones no ignoradas y no sobrescribe archivos diferentes.
Esto evita publicar los originales o el subconjunto durante este incremento.

## Transformación explícita

Se usa el adaptador B02, sin modificarlo, para interpretar los campos numéricos
históricos y recuperar candidatos municipales. Se exigen las huellas de referencia.
Solo se selecciona municipio `76001` (Cali), eventos 210 y 220 y periodos explícitos
2020-S52, 2020-S53, 2021-S01. Se conservan únicamente las cinco columnas canónicas.

Las incidencias conocidas de eventos ajenos no se reclasifican. Cualquier incidencia
original diferente de `unexpected_event` detiene la preparación. Esta operación es
la preparación declarada de un subconjunto, no aceptación parcial de un archivo
rechazado por la carga de producción. El derivado debe pasar `load_csv()` íntegramente.

La salida contiene **cinco observaciones reales** y sus cinco referencias a archivo
y registro original. No hay observación 220 en S01: queda ausente, sin insertar cero.
No se crean registros 580 ni ceros para ilustrar casos. Los ceros se comprueban con
fixtures sintéticos en pruebas, nunca se presentan como datos reales de la demo.
Cada periodo de la malla tiene evidencia en las filas de origen; eso no acredita
que el perfil sea un calendario oficial ni continuidad fuera de su dominio.

## Preparar y abrir

Desde PowerShell, en `C:\Proyecto IA\episentinel-ai`, usando el entorno existente:

```powershell
.\.venv\Scripts\python -B scripts/prepare_b08_demo.py --source-dir data/raw --output-dir data/processed
.\.venv\Scripts\python -B -m streamlit run app/analysis_app.py --server.address 127.0.0.1 --server.port 8502 --server.headless true --browser.gatherUsageStats false
```

Si los originales solo están en Downloads, sustituir `--source-dir data/raw` por
`--source-dir "C:\Users\dilan\Downloads"`. No modificar ni guardar de nuevo los CSV.
Entorno nuevo: instalar primero el proyecto con `pip install -e '.[dev,app]'`.
No se añadieron dependencias al proyecto para esta experiencia.

Abrir [http://127.0.0.1:8502](http://127.0.0.1:8502).
La preparación crea exclusivamente:

- `data/processed/b08_demo.csv`
- `data/processed/b08_demo_manifest.json`

La ejecución de preparación realizada produjo cinco registros y huella del derivado:
`09ef879677aa4ada53f27c2e6f305ff55fcf12068804d4d0e78497b9c14ca6f6`.
La repetición con los mismos originales/perfil es determinista: acepta salidas
idénticas y rechaza sobrescribir contenido diferente. Si hay diferencias, conservar
la copia existente y revisar la causa antes de elegir otra carpeta ignorada.

## Recorrido ante el profesor

1. Inicio: presentar propósito y «Comenzar análisis».
2. Datos: usar el control de carga para seleccionar
   `C:\Proyecto IA\episentinel-ai\data\processed\b08_demo.csv`.
   También puede descargarse la copia local desde el expandible de demostración.
3. Confirmar «Archivo aceptado» y continuar a territorio.
4. Municipio `76001`, evento **Dengue grave · 220**, perfil
   **Tres periodos documentados · 2020–2021**. Leer la procedencia y limitación.
5. Analizar: mostrar cobertura de dos de tres periodos, S53 separada y S01 ausente.
   La marca ámbar pertenece a la banda de ausencia, no al valor cero del conteo.
6. Abrir datos y evidencia para ver los registros entregados por B05 y el SHA-256.
7. Cambiar configuración a **Dengue · 210**: el resultado anterior se invalida;
   ejecutar de nuevo para ver sus tres observaciones independientes.
8. Evidencia: explicar que no hay pronóstico, señal de brote ni riesgo clínico validado.

La fuente del gráfico son los resultados reales de B05. No usa paneles históricos
precalculados ni añade valores de relleno. La aplicación histórica sigue disponible:
`streamlit run app/streamlit_app.py` en otro puerto, con sus propias limitaciones.

## Comprobaciones

```powershell
.\.venv\Scripts\python -B -m pytest tests/test_analysis_presenter.py tests/test_analysis_app.py -q -p no:cacheprovider
.\.venv\Scripts\python -B -m pytest -q -p no:cacheprovider
git check-ignore data/processed/b08_demo.csv data/processed/b08_demo_manifest.json
git diff --check
```

No ejecutar scripts históricos de reconstrucción para demostrar esta nueva experiencia.
La verificación visual y el recorrido real se registran aparte de los resultados
AppTest; sus límites no deben ocultarse.


### Resultado de la comprobación realizada

18 pruebas específicas y 232 totales aprobadas. El recorrido del CSV real se ejecutó
además en navegador local: carga aceptada, municipio 76001, evento 220, resultado
2/3 periodos, evidencia con huella coincidente y cambio de evento que invalidó
el resultado anterior. La ejecución posterior de 210 mostró 3/3 periodos.
La revisión responsive se realizó con viewports de escritorio y móvil, no con un
móvil físico. Lectores de pantalla y recorrido completo de teclado quedan pendientes.
