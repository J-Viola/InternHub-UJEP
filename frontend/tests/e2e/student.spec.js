import { test, expect } from '@playwright/test';
import { clickNavLink, checkHeading, waitForAppLoad } from './helpers';

test.describe('Student role navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/nabidka');
    await waitForAppLoad(page);
  });

  test('can navigate to Moje aplikace', async ({ page }) => {
    await clickNavLink(page, null, 'Praxe');
    // Targeting specifically the h3 heading to avoid conflict with the "no applications" message
    await expect(page.locator('h3').filter({ hasText: 'Podané přihlášky' })).toBeVisible();
  });

  test('can navigate to Profil', async ({ page }) => {
    await clickNavLink(page, null, 'Profil');
    await checkHeading(page, 'Osobní údaje');
  });
});
