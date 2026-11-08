import { test, expect } from '@playwright/test';
import { execSync } from 'node:child_process';

/**
 * Auto-close inzerátu (D-06): v den start_date přejde do CLOSED_FOR_APPLICATIONS.
 *
 * Data a přechody se připravují přes API (izolovaný stack), takže test
 * nezávisí na UI formuláři ani na hostitelském Pythonu.
 */
test.describe('Auto-Close Practices (E2E)', () => {
  test('auto_close_practices uzavře inzerát v den start_date', async ({ request }) => {
    const api = process.env.E2E_API_URL || 'http://localhost:8000';

    // 1) Inzerát ve stavu PENDING (scénář zakládá kompletní nabídku).
    const scenario = await request.post(`${api}/api/test/scenario/practice-editable/`);
    expect(scenario.ok()).toBeTruthy();
    const practiceId = (await scenario.json()).result.practice_id;
    expect(practiceId).toBeTruthy();

    // 2) start_date = dnes, dokud je inzerát editovatelný (PENDING).
    const today = new Date();
    const d = `${String(today.getDate()).padStart(2, '0')}.${String(today.getMonth() + 1).padStart(2, '0')}.${today.getFullYear()}`;
    const companyLogin = await request.post(`${api}/api/users/login/`, {
      data: { email: 'hr@techcorp.cz', password: 'password123' },
    });
    const companyToken = (await companyLogin.json()).access;
    expect(companyToken).toBeTruthy();
    const patch = await request.patch(`${api}/api/practices/employer/${practiceId}/`, {
      headers: { Authorization: `Bearer ${companyToken}` },
      data: { start_date: d },
    });
    expect(patch.ok()).toBeTruthy();

    // 3) Schválit obsah a otevřít inzerát (admin).
    const adminLogin = await request.post(`${api}/api/users/login/`, {
      data: { email: 'admin@admin.com', password: 'demodemo' },
    });
    const adminToken = (await adminLogin.json()).access;
    const headers = { Authorization: `Bearer ${adminToken}` };
    expect((await request.post(`${api}/api/practices/${practiceId}/transition/`, { headers, data: { target_state: 1 } })).ok()).toBeTruthy();
    expect((await request.post(`${api}/api/practices/${practiceId}/transition/`, { headers, data: { target_state: 3 } })).ok()).toBeTruthy();

    // 4) Cron příkaz v izolovaném backendu.
    execSync('docker exec internhub-e2e-backend python manage.py auto_close_practices --settings=app.e2e_settings', {
      encoding: 'utf-8',
    });

    // 5) Stav přímo z DB (employer endpoint je pro admina 404).
    const state = execSync(
      `docker exec internhub-e2e-backend python manage.py shell --settings=app.e2e_settings -c ` +
        `"from practices.models import Practice; print(Practice.objects.get(pk=${practiceId}).workflow_state.name)"`,
      { encoding: "utf-8" }
    ).trim().split("\n").pop();
    expect(state).toBe("CLOSED_FOR_APPLICATIONS");
  });
});
