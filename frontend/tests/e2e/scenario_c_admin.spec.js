import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink, confirmPopup, safeClick } from './helpers';

test.describe('Scenario C: Admin Offer Management', () => {
  test.setTimeout(90000);

  const uniqueId = Date.now().toString();
  const practiceTitle = `Admin Management Test ${uniqueId}`;

  test('Admin approves a pending offer from company', async ({ browser }) => {

    // --- STEP 1: COMPANY CREATES PENDING PRACTICE ---
    console.log('--- Step 1: Company creating practice ---');
    const companyContext = await browser.newContext({ storageState: 'playwright/.auth/company.json' });
    const companyPage = await companyContext.newPage();

    await companyPage.goto('/');
    await waitForAppLoad(companyPage);
    await clickNavLink(companyPage, 'Správa organizace', 'Stáže');

    await companyPage.getByText('Založit stáž').click();
    await companyPage.getByLabel('Název').fill(practiceTitle);
    await companyPage.getByLabel('Popis stáže').fill('Admin should see this.');
    await companyPage.getByLabel('Náplň práce').fill('Testing admin approval.');

    await expect(companyPage.locator('select[id="subject_id"] option').nth(1)).toBeAttached();
    await companyPage.locator('.react-datepicker__input-container input').nth(0).fill('01.01.2027');
    await companyPage.locator('.react-datepicker__input-container input').nth(0).press('Enter');

    await companyPage.locator('select[id="coefficient"]').selectOption('1');
    await companyPage.locator('select[id="contact_user"]').selectOption({ index: 1 });
    await companyPage.locator('select[id="subject_id"]').selectOption({ index: 1 });
    await companyPage.locator('select[id="available_positions"]').selectOption('5');

    await companyPage.getByLabel('Název').click();
    await expect(companyPage.locator('input[id="end_date"]')).not.toHaveValue('', { timeout: 15000 });

    await safeClick(companyPage.getByRole('button', { name: 'Vytvořit' }));
    await expect(companyPage).toHaveURL(/.*\/praxe/);
    await companyContext.close();

    // --- STEP 2: ADMIN APPROVES ---
    console.log('--- Step 2: Admin approving practice ---');
    const adminContext = await browser.newContext({ storageState: 'playwright/.auth/admin.json' });
    const adminPage = await adminContext.newPage();

    await adminPage.goto('/');
    await waitForAppLoad(adminPage);
    await clickNavLink(adminPage, 'Správa stáží', 'Schvalovací kolečko');

    // Wait for the list to load
    await expect(adminPage.getByText('Načítání stáží...')).not.toBeVisible({ timeout: 15000 });

    // Find our practice in the 'Schvalovací kolečko' section
    const pendingSection = adminPage.locator('div').filter({ hasText: 'Schvalovací kolečko' }).last();
    const practiceCard = adminPage.locator('div[id^="practice-offer-"]').filter({ hasText: practiceTitle }).first();

    await expect(practiceCard).toBeVisible({ timeout: 10000 });

    // Click management icon
    const manageBtn = practiceCard.getByTitle('Změnit stav nabídky');
    await manageBtn.click();

    // Confirm in popup
    await confirmPopup(adminPage, 'změnit stav nabídky');

    // Verify it moved or is no longer pending
    await expect(practiceCard).not.toBeVisible({ timeout: 10000 });

    // Check 'Probíhající stáže' section
    const ongoingSection = adminPage.locator('div').filter({ hasText: 'Probíhající stáže' }).first();
    await expect(ongoingSection.locator('div').filter({ hasText: practiceTitle }).first()).toBeVisible();

    await adminContext.close();
  });
});
