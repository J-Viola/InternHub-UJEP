import { test, expect } from '@playwright/test';
import { navigateAndCheck, waitForAppLoad, clickNavLink, confirmPopup } from './helpers';

test.describe('Dual Approval Flow (E2E)', () => {
  // Use a long timeout as this is a complex multi-step test
  test.setTimeout(120000);

  // We will generate a unique title for the practice to find it easily
  const uniqueId = Date.now().toString();
  const practiceTitle = `E2E Test Practice ${uniqueId}`;

  test('Complete lifecycle: Create -> Approvable -> Apply -> Dual Approve', async ({ browser }) => {

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
    await companyPage.getByLabel('Popis stáže').fill('This is a test practice for E2E dual approval.');
    await companyPage.getByLabel('Odpovědnost stáže').fill('Testing, clicking, approving.');

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
    // Select first available subject option
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


    // --- STEP 4: COMPANY APPROVES APP ---
    console.log('--- Step 4: Company approving application ---');
    const companyContext2 = await browser.newContext({ storageState: 'playwright/.auth/company.json' });
    const companyPage2 = await companyContext2.newPage();

    await companyPage2.goto('/');
    await waitForAppLoad(companyPage2);
    await clickNavLink(companyPage2, 'Správa organizace', 'Přihlášky');

    const appCardCompany = companyPage2.locator('div[id^="application-entity-"]').filter({ hasText: practiceTitle }).first();
    await expect(appCardCompany).toBeVisible();

    // Use title for the manage button in PrihlaskaEntity
    const manageBtnComp = appCardCompany.locator('button').filter({ hasText: '' }).first();
    await manageBtnComp.click();

    await confirmPopup(companyPage2, 'Změnit stav přihlášky');
    await companyContext2.close();


    // --- STEP 5: PROFESSOR APPROVES APP ---
    console.log('--- Step 5: Professor approving application ---');
    const profContext2 = await browser.newContext({ storageState: 'playwright/.auth/professor.json' });
    const profPage2 = await profContext2.newPage();

    await profPage2.goto('/');
    await waitForAppLoad(profPage2);
    await clickNavLink(profPage2, null, 'Správa stáží');
    await waitForAppLoad(profPage2);

    // Search globally for the practice card by title
    const profAppCardPractice = profPage2.locator('div').filter({ hasText: practiceTitle }).filter({ visible: true }).first();
    await expect(profAppCardPractice).toBeVisible({ timeout: 15000 });
    await profAppCardPractice.click();

    // Wait for the detail or students list to load
    await expect(profPage2.getByText(/Přihlášení k praxi|Kontaktní osoba/i).first()).toBeVisible({ timeout: 15000 });

    // Handle navigation to NabidkaDetailPage if needed
    if (profPage2.url().includes('/nabidka/')) {
        const studentsBtn = profPage2.getByRole('button', { name: 'Přihlášení studenti' });
        await expect(studentsBtn).toBeVisible({ timeout: 10000 });
        await studentsBtn.click();
        await waitForAppLoad(profPage2);
    }

    // Now on StudentsPage. Force reload to ensure can_approve is latest.
    await profPage2.reload();
    await waitForAppLoad(profPage2);
    await expect(profPage2.getByText('Načítání studentů...')).not.toBeVisible({ timeout: 15000 });

    // Debug: List all student names/emails visible
    const studentEntities = await profPage2.locator('div[id^="user-entity-"]').all();
    console.log(`Found ${studentEntities.length} student rows.`);
    for (const entity of studentEntities) {
        console.log('Row text:', await entity.innerText());
    }

    // Find the row for our student and click the doc icon
    const studentRow = profPage2.locator('div[id^="user-entity-"]').filter({ hasText: /tsedlacek|Ignác/i }).first();
    await expect(studentRow).toBeVisible({ timeout: 15000 });
    const appDocBtn = studentRow.getByTitle('Zobrazit kartu praxe');
    await expect(appDocBtn).toBeVisible({ timeout: 15000 });
    await appDocBtn.click();

    // Wait for the specific student practice card to load and show the Spravovat button
    await profPage2.waitForURL(/.*\/karta-praxe\/.*/);
    await waitForAppLoad(profPage2);

    await profPage2.getByRole('button', { name: 'Spravovat' }).click();

    await confirmPopup(profPage2, 'Změnit stav přihlášky');
    await profContext2.close();


    // --- VERIFY: STUDENT SEES APPROVED STATE ---
    console.log('--- Verification: Student sees approved state ---');
    const studentContext2 = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
    const studentPage2 = await studentContext2.newPage();

    await studentPage2.goto('/');
    await waitForAppLoad(studentPage2);
    await clickNavLink(studentPage2, null, 'Praxe');

    const finalAppCard = studentPage2.locator('div').filter({ hasText: practiceTitle }).first();
    await expect(finalAppCard).toBeVisible();

    await expect(finalAppCard.getByText('Probíhá').or(finalAppCard.getByText('Schváleno')).first()).toBeVisible();
    await studentContext2.close();
  });
});
