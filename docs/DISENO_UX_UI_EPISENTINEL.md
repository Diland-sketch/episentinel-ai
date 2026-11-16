# EpiSentinel AI — fuente de verdad UX/UI, B08-I1

Identidad: **Centro Inteligente de Vigilancia Epidemiológica**. Experiencia guiada
para observaciones de dengue, sin pronósticos ni señales simuladas. Rama de trabajo:
`feat/b08-streamlit-csv`. Nueva entrada `app/analysis_app.py`; la aplicación histórica
y `app/styles.css` se conservan íntegros y se ejecutan independientemente.

## Sistema visual implementado

Petróleo #102F3A, mineral #276D70, jade #8DCABA, terracota #D59A70, ámbar #E3B45C,
marfil #F7F5EF y texto #24353D. Manrope/Inter como preferencias tipográficas, con
Segoe UI/Arial locales; no se descargan fuentes ni se necesitan recursos externos.
Hero editorial, espaciado amplio, tipografía jerarquizada, controles nativos y una
sola figura protagonista. No hay sidebar de navegación ni cuadrícula de KPIs.

Texto sobre marfil: contraste calculado 11,66:1; mineral sobre marfil 5,49:1;
texto oscuro sobre jade 6,84:1. Estados escritos, no solo colores. Foco visible,
etiquetas nativas, tabla alternativa y ausencia de animaciones obligatorias.
CSS de la entrada nueva ajusta superficies de widgets aun con tema oscuro heredado.

## Pantallas y estados

- **Inicio:** marca, navegación horizontal, propósito y «Comenzar análisis».
- **Datos:** carga real UTF-8, plantilla de encabezados sin conteos, validación B04,
  errores con registro/columna/recomendación. Archivos rechazados no avanzan.
- **Territorio:** selección explícita de código presente, evento disponible para
  ese municipio y malla del equipo. Fuente/versionado visibles; calendario y
  catálogo pendientes. No se suman 210+220 ni se construye malla desde fechas.
- **Análisis:** contexto municipal, narrativa de cobertura, curva observada con
  `connectgaps=False`; franja independiente para ausencias, nunca colocadas en cero.
  Las etiquetas son año/S, incluida S53. Calidad, datos y evidencia bajo expandibles.
  Sin observaciones: estado vacío, sin curva ni total cero.
- **Evidencia:** archivo, SHA-256, configuración, cobertura, registros y límites.
  La huella identifica bytes, no certifica procedencia de cualquier carga nueva.

La navegación principal es Inicio / Analizar datos / Evidencia. El recorrido analítico
usa Datos → Territorio → Análisis, con botones progresivos y retorno explícito.
No se habilitan modelos; se explica que elegibilidad no evaluada no es rechazo clínico.

## Integración y estado

`load_csv()` valida y aporta opciones. Confirmar el análisis llama a `run_pipeline()`
con `PipelineConfig` y modelos públicos B03. B05 vuelve a validar la entrada como
puerta autoritativa. No se duplican validadores ni se modifican B01–B07.

Bytes y diagnóstico viven en `st.session_state`, no en almacenamiento global o caché
compartida. Cada ejecución identifica huella/nombre de archivo y configuración
completa (territorio, evento, malla, procedencia, versiones). Cambiar archivo o
selección invalida resultados de inmediato. Un cambio del perfil versionado se
comprueba al renderizar y también invalida resultado/evidencia anteriores.
Los widgets pueden desmontarse al navegar; las selecciones y bytes vigentes se
conservan en estado independiente. «Retirar archivo» limpia la sesión analítica.

Errores traducidos en pantalla; diagnóstico original bajo expandible. Texto cargado
se muestra con componentes nativos o escapado, nunca como HTML de usuario.
El gráfico y la narrativa solo describen observaciones del resultado vigente.

## Perfiles y demostración real

`configs/ui_period_grids.json` contiene el perfil provisional de tres etiquetas
observadas en los originales de Cali: 2020-S52, 2020-S53 y 2021-S01. No es un calendario
oficial ni acredita continuidad fuera de esos periodos; no genera otros periodos.
La app informa que la verificación está pendiente. Sin perfiles, bloquea ejecución.

Ver [DEMO_B08.md](DEMO_B08.md) para preparar el CSV real sin publicar datos ignorados,
procedencia/licencia y pasos exactos ante el profesor. El CSV canónico del usuario
no se convierte automáticamente desde la exportación histórica de nueve columnas.

## Archivos B08

- `app/analysis_app.py`: entrada Streamlit y navegación.
- `app/analysis_components.py`: componentes visuales, resultado y evidencia.
- `app/analysis_presenter.py`: estado, identidad de ejecución, configuración,
  adaptación de datos al gráfico y narrativa; sin reglas epidemiológicas nuevas.
- `app/analysis_styles.css`: identidad, responsive y contraste nativo.
- `configs/ui_period_grids.json`: malla explícita versionada del equipo.
- `scripts/prepare_b08_demo.py`: derivación local reproducible de datos reales.
- `tests/test_analysis_presenter.py`, `tests/test_analysis_app.py`: pruebas sintéticas
  de transformación/presentación, invalidación y estados de interfaz con AppTest.
- Dos documentos: este contrato y las instrucciones de demostración.

## Verificación y límites

Las pruebas automatizadas no sustituyen inspección visual o carga en navegador.
AppTest usa estado de carga sintético para probar navegación; el recorrido real con
el archivo derivado se verifica por separado en navegador local.
Pendiente de validación manual exhaustiva: lectores de pantalla, todos los navegadores,
zoom del sistema, límites de archivos grandes y dispositivos móviles físicos.
No hay despliegue público, persistencia de sesiones, autenticación ni evaluación de
modelos en este incremento. No se escriben paneles/reportes históricos.


### Evidencia de implementación B08-I1

- Pruebas específicas de presentador, aplicación AppTest y derivación: **18 aprobadas**.
- Suite completa: **232 aprobadas**, ninguna omitida (22,99 s).
- Streamlit 1.67.0 inició realmente en `127.0.0.1:8502`; no es solo una prueba unitaria.
- Navegador real: archivo derivado cargado mediante selector de archivos; validación,
  selección 76001/220, perfil provisional, resultado 2/3 periodos y evidencia SHA-256.
- Se cambió a evento 210; la pantalla Evidencia informó que no había ejecución
  vigente hasta ejecutar de nuevo. El nuevo resultado mostró 3/3 observaciones.
- Revisión visual en viewport 1280×900 y 390×844: portada, resultado y navegación;
  en 390 px el ancho de documento observado fue 390 px, sin desbordamiento horizontal.
  Se corrigieron contrastes de controles, avisos y expandibles detectados en navegador.
- Verificado foco visible de navegación con teclado. Esto no equivale a una auditoría
  completa de teclado/lectores de pantalla ni a pruebas en teléfonos físicos.
- El viewport temporal de prueba se restauró al finalizar. La app quedó abierta
  localmente para demostración, sin despliegue público.

### Segunda iteración visual B08-I1 · 12/11/2026

La presentación evoluciona hacia una composición editorial: hero de dos bloques,
encabezado de análisis en petróleo, tarjetas ejecutivas contextuales, superficies
alternadas y formularios agrupados. Se mantiene la navegación horizontal y el
recorrido Datos → Territorio → Análisis.

- El resumen deriva observaciones, cobertura, ausencias y advertencias del resultado
  vigente. La cobertura se refiere a la malla declarada, no a completitud de notificación.
- Una sola visualización protagonista de 530 px, sin barra de herramientas visible.
  Conserva ceros, huecos y S53; los faltantes se marcan en una franja separada del eje
  de conteos. No se añaden fechas ni puntos para embellecer la curva.
- La interpretación distingue qué muestran los datos, qué puede describirse y qué
  sigue siendo incierto. No introduce señales, tendencias inferidas ni riesgo clínico.
- La evidencia presenta primero archivo, huella resumida, configuración, malla,
  validación y avisos. La huella íntegra, JSON, razones y trazabilidad extendida
  permanecen accesibles en expandibles secundarios.
- La banda de capacidades comunica validación, trazabilidad, cobertura y pruebas
  documentadas, sin inventar cifras de pruebas ni acreditaciones.
- Los controles conservan componentes nativos y sus claves; las superficies, espacios,
  contraste y columnas mejoran su integración. No cambian interfaces B03–B07.

Verificación ejecutada en esta iteración:

- Pruebas específicas (presentador, AppTest y derivación): **21 aprobadas**.
- Suite completa: **235 aprobadas**, sin omitidas (14,19 s).
- Después del ajuste final de singular y marcas enteras del eje: se repitieron las
  específicas, **21 aprobadas** (16,38 s).
- Recorrido real: nueva carga local de `b08_demo.csv`, selección 76001/220 y perfil
  documentado; resultado con 2/3 observaciones, 67 % de cobertura redondeada, una
  ausencia y siete avisos contextuales. Se verificó invalidación al cambiar evento.
- Revisión visual de resultado y evidencia en 1440 × 1000 y 390 × 844. En móvil,
  documento y viewport midieron 390 px: sin desbordamiento horizontal. Se restauró
  el viewport al terminar y se conservó la pestaña local para revisión.

Límites visuales que permanecen: selección territorial por código hasta disponer de
catálogo aprobado; controles nativos de carga y selección; curva de demostración
necesariamente breve por sus tres periodos reales. Sigue pendiente una evaluación
exhaustiva de accesibilidad con lectores de pantalla y dispositivos físicos.
