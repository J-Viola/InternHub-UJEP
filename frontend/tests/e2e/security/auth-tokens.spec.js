import { test, expect } from '@playwright/test';

test.describe('JWT token management', () => {
  test.setTimeout(60000);

  /**
   * AT01 (P1) - Access token is not stored in localStorage
   *
   * After a successful login, the access token is held only in memory (React state)
   * and must NOT be persisted to localStorage. Only 'user' should be present
   * in localStorage (refreshToken is in an httpOnly cookie).
   */
  test('AT01 - access token is not stored in localStorage', async ({ page }) => {
    // Login directly with email/password instead of relying on storage state
    await page.goto('/');
    await page.locator('#Department').click();
    await page.locator('input[id="email"]').fill('tsedlacek@example.org');
    await page.locator('input[id="password"]').fill('password123');
    await page.locator('button', { hasText: 'Přihlaste se' }).click();
    await page.waitForURL('**/nabidka', { timeout: 20000 });

    // Read all localStorage keys
    const localStorageKeys = await page.evaluate(() => Object.keys(localStorage));
    console.log('localStorage keys found:', localStorageKeys);

    // The access token must NOT be present in localStorage
    expect(localStorageKeys).not.toContain('accessToken');
    expect(localStorageKeys).not.toContain('access');
    expect(localStorageKeys).not.toContain('token');

    // 'refreshToken' is now in httpOnly cookie, not localStorage!
    // So only 'user' should be in localStorage
    expect(localStorageKeys).toContain('user');
  });

  /**
   * AT04 (P2) - API returns 401 for protected endpoints without auth
   *
   * Calling a protected API endpoint without any authentication should
   * return a 401 Unauthorized status.
   *
   * Note: Uses page.request directly (not axios) so no interceptor
   *       or refresh logic is involved.
   */
  test('AT04 - API returns 401 for protected endpoints without auth', async ({ page }) => {
    // No storage state — fully unauthenticated
    // Hit a protected API endpoint directly
    const response = await page.request.get('http://localhost:8000/api/student-practices/');

    console.log(`API response status: ${response.status()}`);
    expect(response.status()).toBe(401);
  });
});
