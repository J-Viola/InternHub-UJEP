import { test, expect } from '@playwright/test';
import { waitForAppLoad } from './helpers';

/**
 * Scenario D: plná kapacita.
 *
 * Data připraví testovací scénář `capacity-full`: inzerát s 1 místem a jednou
 * zasmluvněnou přihláškou. Přihlášený student se pokusí přihlásit a musí
 * dostat chybu o plné kapacitě (UAT TC-07-02).
 */
test.describe('Scenario D: Edge Cases - Full Capacity', () => {
  test('Cannot apply to a practice with full capacity', async ({ browser, request }) => {
    const api = process.env.E2E_API_URL || 'http://localhost:8000';
    const resp = await request.post(`${api}/api/test/scenario/capacity-full/`);
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    const practiceId = data.result.practice_id;
    expect(practiceId).toBeTruthy();

    const studentContext = await browser.newContext({
      storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/student.json`,
    });
    const page = await studentContext.newPage();

    await page.goto(`/nabidka/${practiceId}`);
    await waitForAppLoad(page);

    const applyBtn = page.getByRole('button', { name: 'Podat přihlášku' });
    await applyBtn.click();
    await page.getByRole('button', { name: 'Ano', exact: true }).click();

    // Backend vrátí CAPACITY_FULL a FE zobrazí hlášku.
    await expect(page.getByText(/Kapacita partnera je plně obsazena/i).first()).toBeVisible({ timeout: 15000 });

    await studentContext.close();
  });
});
