import { test as setup, expect } from '@playwright/test';

const authFileAdmin = 'playwright/.auth/admin.json';
const authFileProfessor = 'playwright/.auth/professor.json';
const authFileCompany = 'playwright/.auth/company.json';
const authFileStudent = 'playwright/.auth/student.json';

// Helper function to login
async function loginAs(page, email, password, storageFile) {
  // Clean local storage first
  await page.goto('/');
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  await page.goto('/');

  // Wait for the bundle to load and React to render
  await page.waitForSelector('#root', { state: 'attached' });

  // Switch to "Jsem firma" (email/password login mode)
  await page.locator('#Department').click();

  // Fill credentials
  const emailInput = page.locator('input[id="email"]');
  const passwordInput = page.locator('input[id="password"]');

  await expect(emailInput).toBeVisible();
  await emailInput.fill(email);
  await passwordInput.fill(password);

  // Click login
  await page.locator('button', { hasText: 'Přihlaste se' }).click();

  // Wait for redirect to /nabidka
  await page.waitForURL('**/nabidka', { timeout: 20000 });

  // Ensure localStorage is populated
  await page.waitForFunction(() => {
    return localStorage.getItem('user') !== null && localStorage.getItem('refreshToken') !== null;
  }, { timeout: 10000 });

  // Save auth state
  await page.context().storageState({ path: storageFile });
}

setup('authenticate admin', async ({ page }) => {
  await loginAs(page, 'admin@admin.com', 'demodemo', authFileAdmin);
});

setup('authenticate professor', async ({ page }) => {
  await loginAs(page, 'professor@ujep.cz', 'password123', authFileProfessor);
});

setup('authenticate company', async ({ page }) => {
  await loginAs(page, 'hr@techcorp.cz', 'password123', authFileCompany);
});

setup('authenticate student', async ({ page }) => {
  await loginAs(page, 'tsedlacek@example.org', 'password123', authFileStudent);
});
