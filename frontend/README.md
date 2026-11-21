# EpiSentinel AI 2.0 — Frontend conectado

Espacio React de inteligencia epidemiológica: dashboard ejecutivo, catálogo real,
histórico y predicción retrospectiva explícita. Conserva navegación y arquitectura.
No modifica backend, modelos, Streamlit ni reportes científicos.

## Ejecución

Iniciar FastAPI desde la raíz siguiendo [API_V2.md](../docs/API_V2.md).
Requiere el panel original local; si falta, la interfaz lo informa sin sustituirlo.
En otra consola:

```powershell
cd frontend
npm ci
npm run dev
```

Abrir http://127.0.0.1:5173. Vite usa puerto estricto y reenvía /api a
http://127.0.0.1:8000. Sin API, la aplicación sigue navegable y muestra el estado
real. VITE_API_BASE_URL permite otra base completa, por ejemplo
http://127.0.0.1:8000/api/v1; requiere CORS autorizado en el servidor.

La comprobación local utilizó dependencias de transporte aisladas en
.api-runtime/ (ignorado), sin cambiar las bibliotecas científicas. La instalación
reproducible del backend es la documentada en API_V2.

```powershell
npm run build       # TypeScript estricto y producción en dist/
npm run lint        # Cero advertencias permitidas
npm test            # Vitest, ejecución única
npm run preview     # Después del build; no incluye proxy de desarrollo
```

En producción, servir index.html para las rutas de aplicación y reenviar /api/v1
a FastAPI, o configurar la base externa al compilar. No se configuró hosting.

## Arquitectura y contratos

Referencia: [OpenAPI aprobado](../docs/api/openapi.json).

- lib/api-types.ts describe los campos consumidos; lib/api.ts valida respuestas,
  conserva errores estructurados, limita esperas y no reintenta pronósticos.
- app/application-state.tsx consulta salud, resumen y catálogo paginado, comprueba
  identidad de fuente y comparte la selección territorial.
- lib/use-historical-series.ts cancela consultas y evita publicar respuestas
  tardías de otro territorio o fuente.
- features/dashboard/ contiene indicadores con procedencia, histórico y gráficos
  Recharts cargados bajo demanda, con tabla de valores originales accesible.
- pages/exploration-page.tsx permite buscar códigos reales, sin inventar nombres.
- pages/predictions-page.tsx consulta métodos y cortes del servidor. El POST solo
  ocurre al pulsar Ejecutar predicción. Cambiar configuración oculta el resultado
  anterior; los fallos no sustituyen el método ni publican curvas parciales.
- components/ contiene disponibilidad, conexión, procedencia, shell y UI local
  siguiendo patrones shadcn/Radix. styles/global.css concentra tokens y responsive.

GET consumidos: health, overview, territories, series, methodology. POST:
forecasts/retrospective. No se leen automáticamente reportes históricos.

| Ruta | Función |
|---|---|
| / | Indicadores estructurales, histórico y acceso al pronóstico |
| /exploracion | Catálogo, búsqueda y serie seleccionada |
| /predicciones | Ejecución retrospectiva, métricas, bandas disponibles y advertencias |
| /datos | Capacidad pendiente, sin cargas |
| /laboratorio | Capacidad pendiente, sin experimentos |
| /sistema | Salud, procedencia y limitaciones |
| Otras | 404 y retorno |

## Alcance de los datos

Los indicadores son filas del panel, candidatos municipales y posiciones
históricas; no son casos totales, riesgo ni territorios acreditados. El catálogo
está pendiente de validación territorial. Se muestran las limitaciones del
servidor: el panel heredado combina 210+220, pliega S53 y contiene ceros completados
previamente. React no realiza esas transformaciones. Las fechas de siete días son
técnicas, no calendario epidemiológico oficial. Las métricas retrospectivas no
confirman brotes ni garantizan desempeño futuro.

## Diseño y accesibilidad

Navy #102B38, teal #087F8C, turquesa #12B8AE, fondo #F4F7FA; ámbar para advertencias.
Hero compacto, indicadores en franja y gráfico principal en lugar de decoración.
Tipografía del sistema sin peticiones externas. Sidebar colapsable y cajón móvil
Radix, Escape y retorno de foco, enlace para saltar al contenido, navegación
etiquetada, foco visible y tablas accesibles. Los gráficos no animan ni conectan
faltantes. La lista lateral usa el orden del catálogo, sin sugerir ranking de riesgo.

React/DOM 19.3.1, Router 8.5.2, TypeScript 6.0.3, Vite 8.3.8, Tailwind 4.3.5,
Recharts 3.11.0, Vitest 5.1.1 y axe 4.14.1. Versiones exactas en package-lock.json.
Entorno comprobado: Node 24.15.0, npm 11.12.1. Reproducir con npm ci.

## Verificación

21 de noviembre de 2026: build y lint aprobados; 41 pruebas en tres archivos
aprobadas. Cubren navegación, foco, disponibilidad, contrato HTTP, paginación,
fuentes incompatibles, respuestas tardías, valores originales, ejecución explícita,
fallos sin sustitución y axe sobre rutas y diálogo móvil.

Los datos sintéticos existen exclusivamente en pruebas. jsdom no calcula layout:
se omite solo contraste en axe y se sustituyen gráficas en las pruebas de página.
Se revisó navegador real con API local, escritorio y móvil de 390 px. Esto no
equivale a certificación WCAG ni a validación científica. La prueba manual ejecutó
solo Último valor, código 76001, corte 779, ocho objetivos; no ajustes masivos SARIMA.

El bundle inicial pesa aproximadamente 120 kB gzip; la visualización compartida,
116 kB gzip adicionales bajo demanda. Capturas antes/después conservadas fuera del
repositorio. No se crearon commits, PR ni merge de frontend.
