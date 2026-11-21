export function apiBase(value, production = false) {
  if (!value) throw new Error('Falta configurar la URL pública de la API.');
  const url = new URL(value);
  if (production && url.protocol !== 'https:') throw new Error('La API pública requiere HTTPS.');
  if (url.username || url.password || url.search || url.hash || !url.pathname.endsWith('/api/v1')) throw new Error('La URL debe terminar en /api/v1, sin claves ni parámetros.');
  return url.href.replace(/\/$/, '');
}

export async function request(base, path, options = {}) {
  const response = await fetch(base + path, {...options, signal: options.signal ?? AbortSignal.timeout(90000)});
  const text = await response.text();
  let result;
  try { result = JSON.parse(text); }
  catch { throw new Error('El servicio aún no devolvió JSON. Puede estar despertando; vuelve a intentar.'); }
  if (!response.ok) throw new Error(`${result.error?.code ?? response.status}: ${result.error?.message ?? 'Solicitud rechazada'}`);
  return result;
}
