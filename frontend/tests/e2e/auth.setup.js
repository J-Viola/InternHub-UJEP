import { test as setup, expect } from '@playwright/test';
import path from 'node:path';

const authDir = path.resolve(__dirname, '../..', process.env.E2E_AUTH_DIR || 'playwright/.auth');
const authFileAdmin = path.join(authDir, 'admin.json');
const authFileProfessor = path.join(authDir, 'professor.json');
const authFileCompany = path.join(authDir, 'company.json');
const authFileStudent = path.join(authDir, 'student.json');

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

  // Ensure user is stored in localStorage (refreshToken is in httpOnly cookie)
  await page.waitForFunction(() => {
    return localStorage.getItem('user') !== null;
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
