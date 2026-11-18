# UX-I1 — Composición y verificación visual

Fecha de revisión: 17 de noviembre de 2026. Rama: `feat/ux-i1`.
Base limpia: `1d3bd2e7416442b79128cecb76f13569aa59ebfe`, PR #28 integrado.
Publicación de UX-I1 autorizada después de verificar el selector real de archivos. El merge requiere autorización independiente.

## Alcance

- Navegación principal sobre petróleo, navegación secundaria mediante subrayado y fases del Laboratorio con controles nativos. Mismas claves, opciones y callbacks.
- Resultado municipal compuesto en dos columnas, que se apilan en móvil: gráfica e interpretación junto a cobertura y límites. Gráfica de tres periodos: 310 px, antes 530 px. Sin pronósticos añadidos. Información de archivo, configuración, advertencias y diagnóstico técnico conservada.
- Cero observado y ausencia siguen siendo distintos. `connectgaps=False`; marcadores de ausencia en eje independiente. Eje temporal separado de la banda de ausencias para evitar superposición en móvil.
- Recorrido de doce fases: cuatro capítulos interactivos, sin las cuatro tarjetas estáticas duplicadas. Se conservan todas las evidencias, estados y límites.
- Cinco vistas históricas con el mismo tema de figuras. Filtros territoriales en columnas; contexto temporal accesible mediante un desplegable.
- Mapas municipales y departamentales: nombres completos envueltos, margen izquierdo explícito, altura por filas, todos los territorios etiquetados y barra logarítmica horizontal. No se modifican conteos, log1p, rankings, escalas de color ni valores del hover.
- Estados hover/focus y transiciones de 160 ms. `prefers-reduced-motion: reduce` desactiva transiciones, animaciones y desplazamiento animado. Los controles siguen siendo nativos y operables por teclado.

## Arranque oficial

Desde PowerShell, con las dependencias ya instaladas:

```powershell
Set-Location 'C:\Proyecto IA\episentinel-ai'
.\.venv\Scripts\python.exe -B -m streamlit run app/platform_app.py --server.address 127.0.0.1 --server.port 8510 --server.headless true --browser.gatherUsageStats false
```

La instancia oficial fue comprobada en `http://127.0.0.1:8510/`. Si sigue abierta, acceder a esa URL en lugar de iniciar otra instancia en el mismo puerto.

## Verificación

- 58 pruebas específicas aprobadas: `test_visual_theme`, `test_analysis_presenter`, `test_analysis_app`, `test_platform_app`, `test_lab_app`, `test_demo_preflight`.
- 750 pruebas totales aprobadas; repetición previa a publicación: 43,88 s.
- El ensayo offline `test_offline_rehearsal_real_artifacts_and_session_isolation` usa artefactos reales, impide conexiones externas y falla si navegar invoca ajustes históricos.
- Entrada oficial iniciada realmente. Teclado: flecha derecha sobre navegación principal abre Laboratorio. Acceso a metodología B06-I2 con sus cuatro métodos conservado.
- Recorrido real en navegador por las doce fases y cuatro capítulos, cinco vistas históricas y regreso a Observatorio. Pronósticos y señales muestran botones explícitos y cero gráficas calculadas al entrar.
- CSV real `b08_demo.csv`: municipio 76001, perfil documentado de tres periodos. Evento 210: [142, 112, 150], 3/3. Evento 220: [2, 2, ausente], 2/3. Cambio de evento: cero gráficas antes de una nueva ejecución. Regreso del Laboratorio: mismo archivo, huella y resultado.
- Capturas de revisión de resultados precargadas con los bytes reales del CSV mediante las funciones existentes B04 → B05 → B03, en una instancia de revisión externa al producto. No se agregó un atajo de carga al Observatorio. Posteriormente se completó también la carga mediante el selector real de archivos: sesión nueva de la entrada oficial, botón Upload, selección local de b08_demo.csv (139 bytes), aceptación B04 y análisis con controles reales. Se verificaron 210 (3/3), 220 (2/3), invalidación visible en Evidencia al cambiar evento y conservación del archivo, huella y resultado al volver de las cinco vistas históricas. Capturas adicionales: ux-native-upload-accepted.jpg, ux-native-event210.jpg, ux-native-event220.jpg, ux-native-history-heatmap.jpg y ux-native-session-preserved.jpg.
- Escritorio y móvil de 390 px: sin desbordamiento horizontal de portada y análisis municipal. Mapas: 20 etiquetas municipales y 33 departamentales; sus límites izquierdos permanecen dentro de la figura, también en móvil.
- 13 archivos históricos con SHA-256 idénticos antes/después, incluidos originales, paneles, demostración y reportes. Sin diferencias en `src`, `services`, `configs`, `data`, `reports` ni contratos científicos.
- `git diff --check` y `git diff --cached --check` aprobados. Publicación limitada a once archivos de interfaz, pruebas y esta guía.

Comandos de pruebas:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_visual_theme.py tests/test_analysis_presenter.py tests/test_analysis_app.py tests/test_platform_app.py tests/test_lab_app.py tests/test_demo_preflight.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B scripts/preflight_demo.py
```

El preflight B13 conserva su referencia original `ef6e2e7`: avisa del HEAD posterior y del trabajo UX sin registrar. Sus comprobaciones de dependencias, artefactos, demostración y planificación B10 pasan. No se cambia el verificador para ocultar esos avisos.

## Capturas reales

Galería local y huellas antes/después en:

`C:\Users\dilan\.codex\visualizations\2026\11\16\01a1e565-851c-7072-a434-1949fa3cce44`

Abrir `ux-comparacion.html`. Pares `ux-before-*` / `ux-after-*`: home, observatorio, lab, heatmap en escritorio y móvil; departamentos en escritorio. Capturas adicionales de departamentos, evento 210 y comparación histórica en móvil. El contexto de la captura indica su ambiente y procedencia; no se sustituyeron datos.

## Punto de retorno B13

Se conserva la rama `backup/b13-before-ux-i1` en el commit base y una copia independiente ejecutable en:

`C:\Users\dilan\Documents\ChatGPT\Universidad _ EpiSentinel AI\ux-i1-baseline`

Para ejecutar B13 sin descartar los cambios UX:

```powershell
Set-Location 'C:\Users\dilan\Documents\ChatGPT\Universidad _ EpiSentinel AI\ux-i1-baseline'
& 'C:\Proyecto IA\episentinel-ai\.venv\Scripts\python.exe' -B -m streamlit run app/platform_app.py --server.address 127.0.0.1 --server.port 8511 --server.headless true --browser.gatherUsageStats false
```

Los archivos locales necesarios están presentes en la copia B13. No se necesita reset, stash ni sobrescribir la rama UX.

## Límites y evolución posterior

Sin bloqueantes encontrados para UX-I1 tras completar el ensayo con selector real. Publicación autorizada; no realizar merge ni cerrar Issues automáticamente. Mantener B13 como respaldo.

- Validado en el entorno instalado: Streamlit 1.67.0 y Plotly 7.1.0. No actualizar dependencias durante la sustentación; la presentación depende de los selectores de los componentes nativos.
- Las vistas con 33 territorios conservan desplazamiento vertical para mostrar todos los nombres. No se fuerza su reducción hasta volverlos ilegibles.
- Pronósticos y señales históricos fueron revisados sin pulsar sus cálculos costosos. No se hace un nuevo experimento SARIMA por un cambio de UX.
- Las limitaciones científicas heredadas, calendario pendiente y separación entre servicios y evaluación histórica continúan vigentes.
- Se posponen navegación fija personalizada, componentes JavaScript y transiciones de página con cambios de estado: no son necesarios para la demostración y añadirían riesgo. No se afirma una auditoría completa WCAG ni validación en todos los navegadores.
