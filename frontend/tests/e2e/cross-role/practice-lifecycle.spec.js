import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink, confirmPopup } from '../helpers';

test.describe('Practice cancellation cascade', () => {
  test.setTimeout(120000);

  const uniqueId = Date.now().toString();
  const practiceTitle = `E2E Cancel Test ${uniqueId}`;

  test('PL02 - cancelling a practice cancels all applications', async ({ browser }) => {

    // --- STEP 1: COMPANY CREATES PRACTICE ---
    console.log('--- Step 1: Company creating practice ---');
    const companyContext = await browser.newContext({ storageState: 'playwright/.auth/company.json' });
    const companyPage = await companyContext.newPage();

    await companyPage.goto('/');
    await waitForAppLoad(companyPage);
    await clickNavLink(companyPage, 'Správa organizace', 'Stáže');

    // Click Založit stáž
    await companyPage.getByText('Založit stáž').click();
    await companyPage.waitForURL('**/vytvorit-nabidku');

    // Fill the form
    await companyPage.getByLabel('Název').fill(practiceTitle);
    await companyPage.getByLabel('Popis stáže').fill('This is a test practice for E2E cancellation cascade.');
    await companyPage.getByLabel('Odpovědnost stáže').fill('Testing cancellation flow.');

    // Wait for dropdowns to be populated
    await expect(companyPage.locator('select[id="contact_user"] option').nth(1)).toBeAttached({ timeout: 10000 });
    await expect(companyPage.locator('select[id="subject_id"] option').nth(1)).toBeAttached({ timeout: 10000 });

    // Fill dates
    const dateInputs = companyPage.locator('.react-datepicker__input-container input');
    await dateInputs.nth(0).fill('01.01.2027');
    await dateInputs.nth(0).press('Enter');

    // Select options
    await companyPage.locator('select[id="coefficient"]').selectOption('1');
    await companyPage.locator('select[id="contact_user"]').selectOption({ index: 1 });
    await companyPage.locator('select[id="subject_id"]').selectOption({ index: 1 });
    await companyPage.locator('select[id="available_positions"]').selectOption('2');

    await companyPage.getByLabel('Název').click(); // to blur and trigger end_date calc

    // Wait for end date to populate
    await expect(companyPage.locator('input[id="end_date"]')).not.toHaveValue('', { timeout: 15000 });

    await companyPage.getByRole('button', { name: 'Vytvořit' }).click();

    // Wait for success message or redirect
    console.log('Waiting for redirect to /praxe...');
    try {
        await expect(companyPage).toHaveURL(/.*\/praxe/, { timeout: 20000 });
    } catch (e) {
        console.error('Redirect to /praxe failed. Current URL:', companyPage.url());
        const bodyText = await companyPage.innerText('body');
        console.log('Page text on failure:', bodyText);
        throw e;
    }
    await companyContext.close();


    // --- STEP 2: PROFESSOR APPROVES PRACTICE ---
    console.log('--- Step 2: Professor approving practice ---');
    const profContext1 = await browser.newContext({ storageState: 'playwright/.auth/professor.json' });
    const profPage1 = await profContext1.newPage();

    await profPage1.goto('/');
    await waitForAppLoad(profPage1);
    await clickNavLink(profPage1, null, 'Správa stáží');
    await waitForAppLoad(profPage1);

    // Wait for the specific page loader to disappear
    await expect(profPage1.getByText('Načítání stáží...')).not.toBeVisible({ timeout: 15000 });
    await expect(profPage1.getByText('Schvalovací kolečko')).toBeVisible({ timeout: 10000 });

    const practiceCardProf = profPage1.locator('div[id^="practice-offer-"]').filter({ hasText: practiceTitle }).first();
    try {
        await expect(practiceCardProf).toBeVisible({ timeout: 15000 });
    } catch (e) {
        console.error(`Could not find practice card with title ${practiceTitle}. Current page text:`, await profPage1.innerText('body'));
        throw e;
    }

    // Check if the 'gear' button is present using the title
    const gearBtn = practiceCardProf.getByTitle('Změnit stav nabídky');
    await expect(gearBtn).toBeVisible();
    await gearBtn.click();
    await confirmPopup(profPage1, 'změnit stav nabídky');
    await profContext1.close();


    // --- STEP 3: STUDENT APPLIES ---
    console.log('--- Step 3: Student applying ---');
    const studentContext = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
    const studentPage = await studentContext.newPage();

    await studentPage.goto('/');
    await waitForAppLoad(studentPage);
    await clickNavLink(studentPage, null, 'Nabídka praxí');

    await studentPage.locator('input[id="title"]').fill(practiceTitle);
    const practiceCardStudent = studentPage.locator('div').filter({ hasText: practiceTitle }).first();
    await expect(practiceCardStudent).toBeVisible();
    await practiceCardStudent.click();

    await studentPage.getByRole('button', { name: 'Podat přihlášku' }).click();
    // In NabidkaDetailPage, the popup uses "Ano"
    await studentPage.getByRole('button', { name: 'Ano', exact: true }).click();
    await expect(studentPage.getByRole('button', { name: 'Podat přihlášku' })).not.toBeVisible();
    await studentContext.close();


    // --- STEP 4: PROFESSOR REJECTS PRACTICE (cancels the practice offer) ---
    // Note: In the current UI, practice cancellation is performed by the professor
    // via the detail page, since the company view does not expose a cancel/close button.
    // The professor navigates to the practice offer detail and uses the manage (gear)
    // button to reject the practice, which cascades to all applications.
    console.log('--- Step 4: Professor cancelling practice ---');
    const profContext2 = await browser.newContext({ storageState: 'playwright/.auth/professor.json' });
    const profPage2 = await profContext2.newPage();

    await profPage2.goto('/');
    await waitForAppLoad(profPage2);

    // Go to NabidkaPage (offers for students) to find the practice
    await clickNavLink(profPage2, null, 'Nabídka praxí');
    await waitForAppLoad(profPage2);

    // Search for the practice by title
    await profPage2.locator('input[id="title"]').fill(practiceTitle);

    // Wait for debounced search to complete and result to appear
    await expect(profPage2.getByText('Načítání nabídek...')).not.toBeVisible({ timeout: 15000 });

    // Find and click the practice card to navigate to detail page
    const profPracticeCard = profPage2.locator('div').filter({ hasText: practiceTitle }).first();
    await expect(profPracticeCard).toBeVisible({ timeout: 15000 });
    await profPracticeCard.click();

    // Now on NabidkaDetailPage — wait for it to load
    await profPage2.waitForURL(/.*\/nabidka\/\d+/);
    await waitForAppLoad(profPage2);

    // Click the "Spravovat" (gear/manage) button that professors see
    const manageBtn = profPage2.getByRole('button', { name: 'Spravovat' });
    await expect(manageBtn).toBeVisible({ timeout: 10000 });
    await manageBtn.click();

    // Wait for the popup to appear and click the reject button ("Zamítnout")
    // The popup has id="popup-reject-button" for the reject action
    await expect(profPage2.locator('#popup-reject-button')).toBeVisible({ timeout: 10000 });
    console.log('Clicking reject button to cancel practice');
    await profPage2.locator('#popup-reject-button').click();

    // Wait for the popup to dismiss (backend processes, popup closes)
    await expect(profPage2.locator('#popup-reject-button')).not.toBeVisible({ timeout: 15000 });
    await profContext2.close();


    // --- STEP 5: VERIFY STUDENT SEES CANCELLED STATUS ---
    console.log('--- Step 5: Verify student sees cancellation ---');
    const studentContext2 = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
    const studentPage2 = await studentContext2.newPage();

    await studentPage2.goto('/');
    await waitForAppLoad(studentPage2);
    await studentPage2.goto('/praxe');

    // Find the practice card on the student's Praxe page
    const cancelledAppCard = studentPage2.locator('div').filter({ hasText: practiceTitle }).first();
    await expect(cancelledAppCard).toBeVisible({ timeout: 15000 });

    // Verify the status shows as cancelled or rejected
    // Accepted status texts: "Zrušeno" (CANCELLED), "Zamítnuto" (REJECTED),
    // or "Obsah zamítnut" (CONTENT_REJECTED)
    await expect(
        cancelledAppCard.getByText('Zrušeno')
            .or(cancelledAppCard.getByText('Zamítnuto'))
            .or(cancelledAppCard.getByText('Obsah zamítnut'))
            .first()
    ).toBeVisible({ timeout: 10000 });

    console.log('Verified: student sees cancelled/rejected status');
    await studentContext2.close();
  });
});
