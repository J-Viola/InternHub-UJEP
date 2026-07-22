import { test, expect } from '@playwright/test';
import { waitForAppLoad } from './helpers';

test.describe('Scenario A: Company Registration Flow', () => {
  test('Complete registration and profile verification', async ({ page }) => {
    const uniqueId = Date.now().toString();
    const email = `test_org_${uniqueId}@example.com`;
    const password = 'Password123!';
    const ico = '44555601'; // UJEP ICO

    await page.goto('/login');

    // Click on registration
    await page.getByRole('button', { name: 'Registrace' }).click();
    await expect(page).toHaveURL(/.*\/registrace/);

    // Fill ICO and search
    await page.getByLabel('Zadejte IČO firmy').fill(ico);
    await page.getByRole('button', { name: 'Hledat' }).click();

    // Wait for ARES results and select
    await expect(page.getByText('Výsledky vyhledávání')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Univerzita Jana Evangelisty Purkyně v Ústí nad Labem')).toBeVisible();
    await page.getByRole('button', { name: 'Vybrat' }).first().click();

    // Fill manager info
    await page.getByLabel('Jméno jednatele').fill('Jan');
    await page.getByLabel('Příjmení jednatele').fill('Dvořák');
    await page.getByLabel('E-mailová adresa jednatele').fill(email);
    await page.getByLabel('Telefonní číslo jednatele').fill('+420777123456');

    // Fill passwords
    // Note: LoginForm uses type="password" so we can use getByLabel if it has associated label
    await page.locator('input[id="executivePassword1"]').fill(password);
    await page.locator('input[id="executivePassword2"]').fill(password);

    // Submit registration
    await page.getByRole('button', { name: 'Vytvořit zaměstnavatele' }).click();

    // Should redirect to login
    await expect(page).toHaveURL(/.*\/login/, { timeout: 15000 });

    // Login with new credentials
    await page.getByRole('button', { name: 'Jsem firma' }).click();
    await page.getByLabel('E-mail').fill(email);
    await page.getByLabel('Heslo').fill(password);
    await page.getByRole('button', { name: 'Přihlaste se' }).click();

    // Verify dashboard
    await waitForAppLoad(page);
    await expect(page.getByText('Univerzita Jana Evangelisty Purkyně v Ústí nad Labem')).toBeVisible();

    // Check if we can see 'Správa organizace' menu
    await expect(page.getByRole('button', { name: 'Správa organizace' })).toBeVisible();
  });
});
