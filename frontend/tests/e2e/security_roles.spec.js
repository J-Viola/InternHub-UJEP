import { test, expect } from '@playwright/test';
import { waitForAppLoad } from './helpers';

test.describe('Security and Role Boundaries (E2E)', () => {

  test('Student cannot access admin routes', async ({ browser }) => {
    const studentContext = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
    const studentPage = await studentContext.newPage();

    // Attempt to visit admin-only pages
    const adminRoutes = ['/departments', '/companies', '/users/department_users'];

    for (const route of adminRoutes) {
        await studentPage.goto(route);
        await waitForAppLoad(studentPage);
        // Should be redirected to root or home
        await expect(studentPage.url()).not.toContain(route);
    }

    await studentContext.close();
  });

  test('Professor cannot access company-only routes', async ({ browser }) => {
    const profContext = await browser.newContext({ storageState: 'playwright/.auth/professor.json' });
    const profPage = await profContext.newPage();

    // Company only routes
    const companyRoutes = ['/users/org_users'];

    for (const route of companyRoutes) {
        await profPage.goto(route);
        await waitForAppLoad(profPage);
        await expect(profPage.url()).not.toContain(route);
    }

    await profContext.close();
  });

  test('Unauthenticated user is redirected to login', async ({ page }) => {
    // New context with NO storage state
    await page.goto('/nabidka');
    // React Router redirects to root '/'
    await expect(page).toHaveURL('http://localhost:3000/');
    await expect(page.getByRole('heading', { name: 'Přihlášení' })).toBeVisible();
  });
});
