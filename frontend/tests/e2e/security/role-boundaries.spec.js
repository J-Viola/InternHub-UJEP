import { test, expect } from '@playwright/test';

test.describe('Role-based access boundaries', () => {
  test.setTimeout(60000);

  /**
   * RB01 (P0) - Student cannot access admin pages
   *
   * Verifies that a student is redirected away from admin-only routes:
   *   /departments, /companies, /users/department_users
   */
  test('RB01 - student cannot access admin pages', async ({ page }) => {
    // Login directly with email/password
    await page.goto('/');
    await page.locator('#Department').click();
    await page.locator('input[id="email"]').fill('tsedlacek@example.org');
    await page.locator('input[id="password"]').fill('password123');
    await page.locator('button', { hasText: 'Přihlaste se' }).click();
    await page.waitForURL('**/nabidka', { timeout: 20000 });

    const adminRoutes = ['/departments', '/companies', '/users/department_users'];
    for (const route of adminRoutes) {
      await page.goto(route);
      await page.waitForTimeout(2000); // wait for redirect
      // Student should be redirected away from the admin route
      await expect(page.url()).not.toContain(route);
    }
  });

  /**
   * RB02 (P0) - Company cannot access professor pages
   *
   * Verifies that a company user is redirected away from professor-only routes:
   *   /sprava-stazi (allowedRoles: ['VY', 'VK', 'admin'])
   */
  test('RB02 - company cannot access professor pages', async ({ page }) => {
    await page.goto('/');
    await page.locator('#Department').click();
    await page.locator('input[id="email"]').fill('hr@techcorp.cz');
    await page.locator('input[id="password"]').fill('password123');
    await page.locator('button', { hasText: 'Přihlaste se' }).click();
    await page.waitForURL('**/nabidka', { timeout: 20000 });

    const professorRoute = '/sprava-stazi';
    await page.goto(professorRoute);
    await page.waitForTimeout(2000);
    await expect(page.url()).not.toContain(professorRoute);
  });

  /**
   * RB04 (P1) - Unauthenticated user redirected to login
   *
   * Verifies that a visitor with no storage state is redirected to /
   * and sees the login heading.
   */
  test('RB04 - unauthenticated user redirected to login', async ({ page }) => {
    // No storage state — fully unauthenticated
    await page.goto('/nabidka');

    // React Router should redirect to root /
    await expect(page).toHaveURL('http://localhost:3000/');
    await expect(page.getByRole('heading', { name: 'Přihlášení' })).toBeVisible();
  });
});
