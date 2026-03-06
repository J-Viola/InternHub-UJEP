import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink, confirmPopup } from './helpers';

test.describe('Invitation Flow (E2E)', () => {
  test.setTimeout(90000);

  test('Company invites student -> Student accepts', async ({ browser }) => {

    // --- STEP 1: COMPANY SENDS INVITATION ---
    console.log('--- Step 1: Company sending invitation ---');
    const companyContext = await browser.newContext({ storageState: 'playwright/.auth/company.json' });
    const companyPage = await companyContext.newPage();

    await companyPage.goto('/');
    await waitForAppLoad(companyPage);
    await clickNavLink(companyPage, null, 'Studenti');
    await waitForAppLoad(companyPage);

    // Search for student Ignác
    await companyPage.locator('input[id="name"]').fill('Ignác');
    // Wait for search result
    const studentCard = companyPage.locator('div[id^="user-entity-"]').filter({ hasText: 'Ignác Čech' }).first();
    await expect(studentCard).toBeVisible();

    // Click the "+" button to select student using title
    const plusButton = studentCard.getByTitle('Vybrat pro pozvánku');
    await plusButton.click();

    // Check if the Pozvat button now shows (1) student selected
    const inviteBtn = companyPage.getByRole('button', { name: /Pozvat \(1\)/ });
    await expect(inviteBtn).toBeVisible({ timeout: 10000 });
    await inviteBtn.click();

    // Wait for the invitation page to load
    await companyPage.waitForURL(/.*\/pozvanka.*/, { timeout: 20000 });
    await waitForAppLoad(companyPage);

    // Wait for the list of practices to load
    await expect(companyPage.getByText('Načítání...')).not.toBeVisible({ timeout: 15000 });

    // Select a specific practice from the list
    const practiceToSelect = companyPage.locator('div[id^="nabidka-inline-"]').filter({ hasText: 'React Frontend Trainee' }).first();
    await expect(practiceToSelect).toBeVisible({ timeout: 10000 });
    await practiceToSelect.click();

    // Click "Vytvořit pozvánku"
    await companyPage.getByRole('button', { name: 'Vytvořit pozvánku' }).click();

    // Confirm in popup
    await companyPage.getByRole('button', { name: 'Vytvořit', exact: true }).click();

    // Should redirect to /pozvanky-list
    await expect(companyPage).toHaveURL(/.*\/pozvanky-list/, { timeout: 15000 });
    await companyContext.close();


    // --- STEP 2: STUDENT ACCEPTS INVITATION ---
    console.log('--- Step 2: Student accepting invitation ---');
    const studentContext = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
    const studentPage = await studentContext.newPage();

    await studentPage.goto('/');
    await waitForAppLoad(studentPage);
    await clickNavLink(studentPage, null, 'Praxe');
    await waitForAppLoad(studentPage);

    // Explicitly reload to fetch fresh invitations and wait for the section to appear
    await studentPage.reload();
    await waitForAppLoad(studentPage);

    // Wait for the "Pozvánky" section heading
    const invitationSection = studentPage.locator('div').filter({ hasText: /Pozvánky od firem/ }).last();
    await expect(invitationSection).toBeVisible({ timeout: 15000 });

    // Find invitation card by text within the invitation section
    const invitationCard = invitationSection.locator('div').filter({ hasText: 'React Frontend Trainee' }).first();
    await expect(invitationCard).toBeVisible({ timeout: 10000 });

    // Click on the card itself to open the manage popup
    await invitationCard.click();

    // Use confirmPopup helper with full unique heading
    await confirmPopup(studentPage, 'Správa pozvánky');
    await studentContext.close();
  });
});
