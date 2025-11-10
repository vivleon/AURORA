// Simple Node smoke script to probe core endpoints
// (scripts_smoke.js [cite: vivleon/aurora/AURORA-main/aurora-win/aurora-win/scripts_smoke.js]를 .mjs로 리네임)
// Usage: node scripts/smoke.mjs http://localhost:8000

const base = process.argv[2] || process.env.BASE_URL || 'http://localhost:8000';

const fetchJson = async (url, options = {}) => {
  console.log(`[FETCH] ${options.method || 'GET'} ${url}`);
  const r = await fetch(url, options);
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`[FAIL] ${r.status} ${r.statusText} @ ${url}\n${text}`);
  }
  return r.json();
};

const main = async () => {
  console.log(`[SMOKE] Base: ${base}`);
  
  // 1. 대시보드 API 스모크
  const kpi = await fetchJson(`${base}/dash/kpi?window=1h`);
  console.log('[OK] /dash/kpi:', kpi.kpi);

  const latency = await fetchJson(`${base}/dash/latency?window=1h`);
  console.log(`[OK] /dash/latency: Found ${latency.series.length} series.`);

  // 2. 핵심 인지 API 스모크 (Plan -> Execute)
  const planReq = { input: "내일 일정 알려줘" };
  const plan = await fetchJson(`${base}/aurora/plan`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(planReq)
  });
  console.log('[OK] /aurora/plan:', plan.plan.steps[0].tool);
  
  const execReq = { plan: plan.plan, session_id: "smoke-test" };
  const exec = await fetchJson(`${base}/aurora/execute`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(execReq)
  });
  
  if (exec.requires_consent) {
    console.log('[OK] /aurora/execute: Received consent request (as expected).');
  } else {
    console.log('[OK] /aurora/execute:', exec.result[0].out);
  }

  console.log('\n[SMOKE] All endpoints smoke tested successfully.');
};

main().catch((e) => { 
  console.error('\n[SMOKE] TEST FAILED');
  console.error(e.message);
  process.exit(1); 
});