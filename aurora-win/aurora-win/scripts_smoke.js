// Simple Node smoke script to probe core endpoints
// Usage: node scripts/smoke.mjs http://localhost:8000

const base = process.argv[2] || process.env.BASE_URL || 'http://localhost:8000';
const fetchJson = async (url) => {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
};

const main = async () => {
  console.log(`[SMOKE] Base: ${base}`);
  const kpi = await fetchJson(`${base}/dash/kpi?window=1h`);
  console.log('[SMOKE] KPI:', kpi);
};

main().catch((e) => { console.error('[SMOKE] FAIL', e); process.exit(1); });
