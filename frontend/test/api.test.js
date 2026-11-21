import test from 'node:test';
import assert from 'node:assert/strict';
import {apiBase, request} from '../src/api.js';
test('production API URL is HTTPS, exact and contains no secret/query', () => {
  assert.equal(apiBase('https://api.example.org/api/v1', true), 'https://api.example.org/api/v1');
  for (const value of ['', 'http://api.example.org/api/v1', 'https://secret@api.example.org/api/v1', 'https://api.example.org/api/v1?token=secret']) assert.throws(() => apiBase(value, true));
});
test('structured errors are propagated once without retry or substitute result', async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls++; return new Response(JSON.stringify({error: {code: 'METHOD_DISABLED', message: 'Disabled'}}), {status: 403}); };
  try { await assert.rejects(request('https://api.example.org/api/v1', '/forecasts/retrospective'), /METHOD_DISABLED/); assert.equal(calls, 1); }
  finally { globalThis.fetch = original; }
});
test('cold-start HTML is an explicit error, never data or a fake forecast', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response('<html>Starting</html>', {status: 503});
  try { await assert.rejects(request('https://api.example.org/api/v1', '/overview'), /aún no devolvió JSON/); }
  finally { globalThis.fetch = original; }
});
