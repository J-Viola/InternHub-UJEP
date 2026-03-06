import { test, expect } from '@playwright/test';
import { clickNavLink, checkHeading, waitForAppLoad } from './helpers';

test.describe('Admin role navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/nabidka');
    await waitForAppLoad(page);
  });

  test('can navigate to Departments', async ({ page }) => {
    await clickNavLink(page, 'Správa systému', 'Katedry');
    await checkHeading(page, 'Správa kateder');
  });

  test('can navigate to Companies', async ({ page }) => {
    await clickNavLink(page, 'Správa systému', 'Společnosti');
    await checkHeading(page, 'Správa společností');
  });

  test('can navigate to Prihlasky', async ({ page }) => {
    await clickNavLink(page, 'Správa stáží', 'Přihlášky');
    await checkHeading(page, 'Nevyřízené přihlášky');
  });

  test('can navigate to School Users', async ({ page }) => {
    await clickNavLink(page, 'Uživatelé', 'Školní uživatelé');
    await checkHeading(page, 'Školní uživatelé');
  });
});
