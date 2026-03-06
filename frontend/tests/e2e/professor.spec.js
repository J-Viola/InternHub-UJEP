import { test, expect } from '@playwright/test';
import { clickNavLink, checkHeading, waitForAppLoad } from './helpers';

test.describe('Professor role navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/nabidka');
    await waitForAppLoad(page);
  });

  test('can navigate to Sprava Stazi', async ({ page }) => {
    await clickNavLink(page, null, 'Správa stáží');
    await checkHeading(page, 'Probíhající stáže');
  });

  test('can navigate to Students', async ({ page }) => {
    await clickNavLink(page, null, 'Studentské účty');
    await checkHeading(page, 'Studenti katedry');
  });

  test('can navigate to Subjects', async ({ page }) => {
    await clickNavLink(page, null, 'Předměty');
    await expect(page.getByRole('heading', { name: 'Předměty', exact: false })).toBeVisible();
  });
});
