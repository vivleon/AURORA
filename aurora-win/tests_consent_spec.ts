import { test, expect, request as pwRequest } from '@playwright/test';

// E2E API tests for /consent and /dash endpoints
// Assumes backend FastAPI is running at BASE_URL (see playwright.config.ts)

const sessionId = `sess-${Date.now()}`;

test.describe('Consent API', () => {
  test('should issue consent and approve', async ({ request, baseURL }) => {
    const reqBody = {
      session_id: sessionId,
      action: 'mail.send',
      purpose: '테스트 메일 발송',
      scope: 'mail',
      risk: 'high',
      ttl_hours: 1,
    };

    const issue = await request.post('/consent/request', { data: reqBody });
    expect(issue.ok()).toBeTruthy();
    const { consent_id } = await issue.json();
    expect(consent_id).toBeTruthy();

    const decision = await request.post('/consent/decision', {
      data: { consent_id, decision: 'approved' },
    });
    expect(decision.ok()).toBeTruthy();
    const j = await decision.json();
    expect(j.status).toBe('approved');
  });
});

 test.describe('Dashboard smoke', () => {
  test('kpi endpoint returns shape', async ({ request }) => {
    const r = await request.get('/dash/kpi?window=1h');
    expect(r.ok()).toBeTruthy();
    const j = await r.json();
    expect(j.kpi).toBeDefined();
    expect(j.kpi).toHaveProperty('success');
  });

  test('latency endpoint returns series', async ({ request }) => {
    const r = await request.get('/dash/latency?p=95&window=1h');
    expect(r.ok()).toBeTruthy();
    const j = await r.json();
    expect(j.series).toBeDefined();
  });
});
