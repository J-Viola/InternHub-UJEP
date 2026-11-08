import { test, expect, request } from '@playwright/test';
import { waitForAppLoad, clickNavLink, checkHeading } from '../helpers';

test.describe('Manage practices overview', () => {
  test.use({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/professor.json` });

  test.beforeAll(async () => {
    const ctx = await request.newContext();
    const resp = await ctx.post(`${process.env.E2E_API_URL || 'http://localhost:8000'}/api/test/scenario/practice-pending-approval/`);
    if (!resp.ok()) console.log('Warning: could not prepare scenario');
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForAppLoad(page);
  });

  test('PMP01 - shows practice management overview', async ({ page }) => {
    console.log('Navigating to Správa stáží...');
    await clickNavLink(page, null, 'Správa stáží');
    await waitForAppLoad(page);

    console.log('Verifying heading "Probíhající stáže" is visible...');
    await checkHeading(page, 'Probíhající stáže');
  });

  test('PMP02 - shows approval queue section', async ({ page }) => {
    console.log('Navigating to Správa stáží...');
    await clickNavLink(page, null, 'Správa stáží');
    await waitForAppLoad(page);

    console.log('Waiting for "Načítání stáží..." to disappear...');
    await expect(page.getByText('Načítání stáží...')).not.toBeVisible({ timeout: 15000 });

    console.log('Verifying heading "Schvalovací kolečko" is visible...');
    await checkHeading(page, 'Schvalovací kolečko');
  });
});
