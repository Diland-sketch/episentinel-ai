# React para EpiSentinel AI

Base funcional para Kerin: consulta catálogo y series reales, muestra 832 posiciones originales de Cali y consume pronósticos B06 únicamente al pulsar Ejecutar. No contiene fixtures, métricas inventadas ni fallback de API/método. La identidad de fuente y las limitaciones permanecen visibles.

Desarrollo local, backend público de demostración en 10000 con origen exacto local autorizado:

```powershell
Set-Location frontend
npm ci
$env:VITE_API_URL='http://127.0.0.1:10000/api/v1'
npm run dev
```

Build para Static Site: `npm ci && npm run build`, con `VITE_API_URL` HTTPS real obligatorio y Node >=20.19 (Render fijado a 22.16.0). Publicar `dist/` y reescribir rutas a `/index.html`. No hay servidor Node en producción. Una URL ausente/insegura hace fallar el build. Cambiarla exige reconstruir.

Solo `VITE_API_URL` puede exponerse. Nunca usar variables VITE para claves, signed URLs, bearer del panel o credenciales. La clave de operador se introduce manualmente por el operador en la página y permanece en memoria; no se guarda en localStorage/cookies. Los demás visitantes solo consultan. Ingesta es una capacidad P2 de backend, no una interfaz agregada a esta base.

Integración: `src/api.js` valida la URL y propaga errores estructurados. Carga inicial secuencial para respetar los dos slots HTTP del backend. Sin reintentos automáticos; el usuario puede volver a conectar ante suspensión de Render. `/capabilities` decide métodos visibles. Cambiar código/método/corte invalida resultados anteriores. El gráfico usa exclusivamente puntos recibidos; no genera fechas ni predicciones.

Contrato de producción: `/api/v1/openapi.json` del perfil Render, con `OperatorKey` y bearer de sesión cuando corresponde. Contrato local histórico: `docs/api/openapi.json`. Seguir [guía Render](../docs/RENDER_FREE.md) para configuración, despliegue manual y aceptación remota.
