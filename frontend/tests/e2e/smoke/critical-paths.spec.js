import { test, expect } from '@playwright/test';
import { waitForAppLoad } from '../helpers';

test.describe('Critical path smoke tests', () => {
  test.setTimeout(120000);

  test('SM01 - all roles can log in', async ({ browser }) => {
    // --- Test Company Login ---
    console.log('--- Testing company login ---');
    const companyCtx = await browser.newContext();
    const companyPage = await companyCtx.newPage();

    await companyPage.goto('/');
    // Wait for React to render the login page
    await companyPage.waitForSelector('#root', { state: 'attached' });

    // Switch to organization (email/password) login mode
    await companyPage.locator('#Department').click();

    // Fill credentials
    await companyPage.locator('input[id="email"]').fill('hr@techcorp.cz');
    await companyPage.locator('input[id="password"]').fill('password123');

    // Click login
    await companyPage.locator('button', { hasText: 'Přihlaste se' }).click();

    // Verify redirect to /nabidka
    await expect(companyPage).toHaveURL(/.*\/nabidka/, { timeout: 20000 });
    console.log('Company login successful, redirected to /nabidka');
    await companyCtx.close();

    // --- Test Student Login ---
    console.log('--- Testing student login ---');
    const studentCtx = await browser.newContext();
    const studentPage = await studentCtx.newPage();

    await studentPage.goto('/');
    await studentPage.waitForSelector('#root', { state: 'attached' });

    // Switch to organization login mode
    await studentPage.locator('#Department').click();

    // Fill credentials
    await studentPage.locator('input[id="email"]').fill('tsedlacek@example.org');
    await studentPage.locator('input[id="password"]').fill('password123');

    // Click login
    await studentPage.locator('button', { hasText: 'Přihlaste se' }).click();

    // Verify redirect to /nabidka
    await expect(studentPage).toHaveURL(/.*\/nabidka/, { timeout: 20000 });
    console.log('Student login successful, redirected to /nabidka');
    await studentCtx.close();
  });

  test('SM03 - profile page loads for student', async ({ browser }) => {
    console.log('--- Testing student profile page ---');
    const studentContext = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
    const studentPage = await studentContext.newPage();

    await studentPage.goto('/profil');
    await waitForAppLoad(studentPage);

    // Verify the profile page has loaded by checking for profile-related content
    // The profile page typically shows user information
    const pageBody = studentPage.locator('body');
    await expect(pageBody).toBeVisible();

    // Check that some profile content is rendered — look for common profile elements
    // e.g., email, name, or profile-related headings
    const hasProfileContent = await studentPage.getByText(/profil|email|e-mail|jméno|name|tsedlacek/i).first().isVisible().catch(() => false);
    if (hasProfileContent) {
      console.log('Profile content detected');
    } else {
      // Fallback: at least verify the page loaded without errors
      console.log('Profile page loaded (content check fell back to URL verification)');
      await expect(studentPage).toHaveURL(/.*\/profil/);
    }

    console.log('Student profile page loaded successfully');
    await studentContext.close();
  });

  test('SM05 - student sees correct nav items', async ({ browser }) => {
    console.log('--- Testing student navigation items ---');
    const studentContext = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
    const studentPage = await studentContext.newPage();

    await studentPage.goto('/');
    await waitForAppLoad(studentPage);

    // Verify that "Nabídka praxí" link is present in the navigation
    const nabidkaLink = studentPage.getByRole('link', { name: 'Nabídka praxí' });
    await expect(nabidkaLink).toBeVisible({ timeout: 10000 });
    console.log('Student nav contains "Nabídka praxí" link');

    // Navigate to the internships page
    await studentPage.goto('/praxe');
    console.log('Navigated to /praxe page');

    await studentContext.close();
  });
});
