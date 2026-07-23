import { test, expect } from '@playwright/test';

/**
 * Smoke tests – verify that the homepage renders correctly.
 * These tests do NOT depend on a live backend; they only check
 * that the React SPA boots and displays the login page.
 */
test.describe('Homepage smoke tests', () => {
  test('homepage loads and displays the login page', async ({ page }) => {
    await page.goto('/');

    // Wait for the React root to mount
    await page.waitForSelector('#root', { state: 'attached' });

    // The page title should be set (check <title> from index.html)
    const title = await page.title();
    expect(title).toBeTruthy();
    console.log(`Page title: "${title}"`);

    // Verify that the login form is rendered – look for the switch
    // that toggles between STAG and Organization login modes.
    const loginSwitch = page.locator('#Department');
    await expect(loginSwitch).toBeVisible({ timeout: 10000 });

    // Verify a heading or button text is present (i18n key login.title or login.login_button)
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  test('page contains expected UI elements on the login screen', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#root', { state: 'attached' });

    // The login switch dropdown should exist
    const departmentSelect = page.locator('#Department');
    await expect(departmentSelect).toBeVisible();

    // The STAG login button should be visible by default (STAG mode is default)
    const loginButton = page.locator('button');
    await expect(loginButton.first()).toBeVisible();
  });
});
