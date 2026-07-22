import { test, expect } from '@playwright/test';
import { waitForAppLoad } from '../helpers';

test.describe('Login scenarios', () => {

  test('L01 (P0) - successful student login', async ({ page }) => {
    test.setTimeout(60000);

    console.log('Navigating to /');
    await page.goto('/');

    // Switch to org/email login mode
    await page.locator('#Department').click();

    // Fill credentials
    await page.locator('input[id="email"]').fill('tsedlacek@example.org');
    await page.locator('input[id="password"]').fill('password123');

    // Click login
    await page.locator('button', { hasText: 'Přihlaste se' }).click();

    // Verify redirect to /nabidka
    await page.waitForURL('**/nabidka', { timeout: 20000 });
    console.log('Redirected to /nabidka');

    // Verify localStorage has user (refreshToken is in httpOnly cookie, not localStorage)
    const user = await page.evaluate(() => localStorage.getItem('user'));

    expect(user).not.toBeNull();
    console.log('localStorage verified: user present');
  });

  test('L05 (P1) - invalid email shows error', async ({ page }) => {
    test.setTimeout(60000);

    console.log('Navigating to /');
    await page.goto('/');

    // Switch to org/email login mode
    await page.locator('#Department').click();

    // Fill nonexistent email
    await page.locator('input[id="email"]').fill('nonexistent-user@example.com');
    await page.locator('input[id="password"]').fill('password123');

    // Click login
    await page.locator('button', { hasText: 'Přihlaste se' }).click();

    // Verify error message is visible
    await expect(
      page.getByText(/Chyba při přihlášení|Neplatné přihlašovací údaje|Autentizace selhala/i)
    ).toBeVisible({ timeout: 15000 });

    console.log('Error message displayed for invalid email');
  });

  test('L06 (P1) - wrong password shows error', async ({ page }) => {
    test.setTimeout(60000);

    console.log('Navigating to /');
    await page.goto('/');

    // Switch to org/email login mode
    await page.locator('#Department').click();

    // Fill correct email + wrong password
    await page.locator('input[id="email"]').fill('tsedlacek@example.org');
    await page.locator('input[id="password"]').fill('wrongpassword123!');

    // Click login
    await page.locator('button', { hasText: 'Přihlaste se' }).click();

    // Verify error message is visible
    await expect(
      page.getByText(/Chyba při přihlášení|Neplatné přihlašovací údaje|Autentizace selhala/i)
    ).toBeVisible({ timeout: 15000 });

    console.log('Error message displayed for wrong password');
  });

  test('L07 (P1) - empty form validation', async ({ page }) => {
    test.setTimeout(60000);

    console.log('Navigating to /');
    await page.goto('/');

    // Switch to org/email login mode
    await page.locator('#Department').click();

    // Leave fields empty and click login
    await page.locator('button', { hasText: 'Přihlaste se' }).click();

    // Verify validation error is shown (both email and password errors may be present)
    await expect(
      page.getByText(/E-mail je povinný|Heslo je povinné/i).first()
    ).toBeVisible({ timeout: 10000 });

    console.log('Validation error displayed for empty form');
  });

  test('L10 (P2) - logout clears session', async ({ browser }) => {
    test.setTimeout(60000);

    console.log('Creating authenticated context for student');
    const context = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
    const page = await context.newPage();

    try {
      await page.goto('/nabidka');
      await waitForAppLoad(page);
      console.log('App loaded, user is logged in');

      // Click logout
      await page.getByRole('link', { name: 'Odhlásit se' }).click();
      console.log('Clicked Odhlásit se');

      // Verify redirect to /
      await page.waitForURL('http://localhost:3000/', { timeout: 15000 });
      console.log('Redirected to / after logout');

      // Verify localStorage is cleared
      const user = await page.evaluate(() => localStorage.getItem('user'));
      const refreshToken = await page.evaluate(() => localStorage.getItem('refreshToken'));

      expect(user).toBeNull();
      expect(refreshToken).toBeNull();
      console.log('localStorage cleared after logout');
    } finally {
      await context.close();
    }
  });

});
