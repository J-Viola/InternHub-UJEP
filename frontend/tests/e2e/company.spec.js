import { test, expect } from '@playwright/test';
import { clickNavLink, checkHeading, waitForAppLoad } from './helpers';

test.describe('Company role navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/nabidka');
    await waitForAppLoad(page);
  });

  test('can navigate to Moje stáže', async ({ page }) => {
    await clickNavLink(page, 'Správa organizace', 'Stáže');
    await checkHeading(page, 'Vytvořené stáže');
  });

  test('can navigate to Prihlasky', async ({ page }) => {
    await clickNavLink(page, 'Správa organizace', 'Přihlášky');
    await checkHeading(page, 'Nevyřízené přihlášky');
  });

  test('can navigate to Students', async ({ page }) => {
    await clickNavLink(page, null, 'Studenti');
    // Use getByRole heading to avoid strict mode violation with nav link
    await expect(page.getByRole('heading', { name: 'Studenti', exact: true })).toBeVisible();
  });

  test('can navigate to Organization Users', async ({ page }) => {
    await clickNavLink(page, 'Správa organizace', 'Uživatelské účty organizace');
    await checkHeading(page, 'Účty organizací');
  });
});
