import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {apiBase, request} from './api.js';
import './style.css';

function Chart({points}) {
  const max = Math.max(1, ...points.map(p => p.observed));
  const coords = points.map((p, i) => `${40 + i * 900 / Math.max(1, points.length - 1)},${230 - p.observed * 190 / max}`).join(' ');
  return <svg viewBox="0 0 980 270" role="img" aria-label="Conteos históricos observados por fecha técnica">
    <line x1="40" y1="230" x2="940" y2="230" stroke="#a9b9bb"/><text x="8" y="45">{max}</text><text x="20" y="235">0</text>
    <polyline points={coords} fill="none" stroke="#087f82" strokeWidth="2"/>
    <text x="40" y="260">{points[0]?.technical_date.slice(0, 10)}</text><text x="820" y="260">{points.at(-1)?.technical_date.slice(0, 10)}</text>
  </svg>;
}

function App() {
  const [base, setBase] = useState(null), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const [catalogue, setCatalogue] = useState(null), [capabilities, setCapabilities] = useState(null), [methodology, setMethodology] = useState(null);
  const [code, setCode] = useState('76001'), [series, setSeries] = useState(null), [result, setResult] = useState(null);
  const [method, setMethod] = useState('ultimo_valor'), [cut, setCut] = useState(779), [key, setKey] = useState('');

  async function connect() {
    setBusy(true); setError(''); setCatalogue(null); setSeries(null); setResult(null); setCapabilities(null);
    try {
      const url = apiBase(import.meta.env.VITE_API_URL, import.meta.env.PROD);
      setBase(url);
      // Keep startup within the small public service's concurrent request budget.
      const caps = await request(url, '/capabilities');
      const territories = await request(url, '/territories?limit=2000');
      const methods = await request(url, '/methodology');
      setCatalogue(territories); setCapabilities(caps); setMethodology(methods);
      if (!territories.codes.includes(code)) setCode(territories.codes[0] ?? '');
      if (!caps.forecast_methods.includes(method)) setMethod(caps.forecast_methods[0] ?? '');
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  useEffect(() => { connect(); }, []);
  async function loadSeries(event) {
    event.preventDefault(); setBusy(true); setError(''); setSeries(null); setResult(null);
    try { setSeries(await request(base, `/series?series=${encodeURIComponent(code)}`)); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function forecast(event) {
    event.preventDefault(); setBusy(true); setError(''); setResult(null);
    try {
      setResult(await request(base, '/forecasts/retrospective', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Operator-Key': key},
        body: JSON.stringify({series: code, cut: Number(cut), method, horizon: 8})}));
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  return <><header><span className="brand">EpiSentinel AI <small>2.0</small></span><span>Observatorio histórico</span></header>
    <main><section className="intro"><p className="eyebrow">DATOS CON PROCEDENCIA</p><h1>Explora las observaciones.<br/>Conserva su contexto.</h1>
      <p>Consulta el panel histórico municipal y ejecuta ensayos retrospectivos con los métodos habilitados por el servicio.</p>
      <button className="secondary" onClick={connect} disabled={busy}>Volver a conectar</button>
      <span className="connection" role="status">{busy ? 'Consultando el servicio…' : catalogue ? 'API conectada · datos reales' : 'Esperando conexión'}</span>
    </section>
    {error && <div className="error" role="alert">{error}</div>}
    <aside>Las fechas son técnicas, no semanas epidemiológicas oficiales. El panel heredado combina eventos 210+220, suma S53 a S52 y completa ausencias con cero. Esta vista no confirma brotes ni clasifica riesgo.</aside>
    <section className="panel"><div className="section-title"><div><p className="eyebrow">CONSULTA</p><h2>Serie histórica municipal</h2></div>{catalogue && <span>{catalogue.total} códigos candidatos · catálogo pendiente de validación</span>}</div>
      <form onSubmit={loadSeries}><label>Municipio · código<select value={code} onChange={e => {setCode(e.target.value); setSeries(null); setResult(null);}} disabled={!catalogue || busy}>
        {(catalogue?.codes ?? []).map(c => <option key={c} value={c}>{c === '76001' ? '76001 · Cali' : c}</option>)}</select></label>
        <button disabled={!catalogue || !code || busy}>Consultar serie</button></form>
      {series && <><Chart points={series.points}/><p>{series.points.length} posiciones originales · municipio {series.series}</p><details><summary>Fuente y limitaciones</summary><p className="hash">SHA-256: {series.source.sha256}</p>{series.limitations.map(x => <p key={x}>{x}</p>)}</details></>}
    </section>
    <section className="panel"><p className="eyebrow">ENSAYO EXPLÍCITO</p><h2>Pronóstico retrospectivo</h2><p>El ajuste usa solo el prefijo hasta el corte. Los ocho observados siguientes se utilizan después para evaluar. Configurar esta sección no entrena.</p>
      {capabilities && !capabilities.forecast_methods.length && <p>Pronósticos deshabilitados por el servicio. Las consultas permanecen disponibles.</p>}
      <form onSubmit={forecast}><label>Método<select value={method} onChange={e => {setMethod(e.target.value); setResult(null);}} disabled={busy || !capabilities}>
        {(capabilities?.forecast_methods ?? []).map(m => <option key={m} value={m}>{m === 'ultimo_valor' ? 'Último valor · B06' : 'SARIMA no estacional · B06'}</option>)}</select></label>
        <label>Corte inclusivo<select value={cut} onChange={e => {setCut(e.target.value); setResult(null);}} disabled={busy || !methodology}>{methodology?.allowed_cuts.map(c => <option key={c}>{c}</option>)}</select></label>
        <label>Clave de operador<input type="password" autoComplete="off" value={key} onChange={e => setKey(e.target.value)} placeholder="Acceso autorizado"/></label>
        <button disabled={busy || !series || !key || !method}>Ejecutar ensayo</button></form>
      <p className="muted">La clave permanece en memoria de esta página. No se incluye en la aplicación publicada. El servicio puede suspenderse por inactividad; las solicitudes no se reintentan automáticamente.</p>
      {result && <div className="result"><h3>Resultado · {result.forecast.fit_status}</h3><p className="hash">Experimento: {result.request.request_id}</p>
        <dl>{result.indicators.map(i => <div key={i.name}><dt>{i.name}</dt><dd>{i.value === null ? 'No disponible' : i.value.toFixed(6)}</dd></div>)}</dl>
        <div className="table-wrap"><table><caption>Ocho objetivos posteriores al corte · fechas técnicas</caption><thead><tr><th>Fecha</th><th>Observado</th><th>Estimación</th><th>Inferior</th><th>Superior</th></tr></thead><tbody>{result.evaluation.rows.map(r => <tr key={r.position}><td>{r.technical_date.slice(0,10)}</td><td>{r.observed ?? 'Ausente'}</td><td>{r.yhat.toFixed(4)}</td><td>{r.lo?.toFixed(4) ?? 'No existe'}</td><td>{r.hi?.toFixed(4) ?? 'No existe'}</td></tr>)}</tbody></table></div>
        <details><summary>Advertencias, procedencia y respuesta completa</summary><pre>{JSON.stringify(result, null, 2)}</pre></details></div>}
    </section><footer>Fuente: Instituto Nacional de Salud · <a href="https://www.datos.gov.co/d/4hyg-wa9d">datos.gov.co/4hyg-wa9d</a> · <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>.<br/>Panel adaptado históricamente. Evaluación retrospectiva sobre datos ya examinados; sin prueba independiente.</footer>
    </main></>;
}
createRoot(document.getElementById('root')).render(<App/>);
