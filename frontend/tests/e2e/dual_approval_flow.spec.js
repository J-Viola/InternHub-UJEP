import { test, expect } from '@playwright/test';
import { navigateAndCheck, waitForAppLoad, clickNavLink, confirmPopup, safeClick } from './helpers';

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
    await companyPage.getByLabel('Náplň práce').fill('Testing, clicking, approving.');
    // BL-07/PBUG-01: mentor_name + contact_email jsou povinné na serveru (PracticeSerializer)
    await companyPage.locator('input[id="mentor_name"]').fill('Mentor E2E');
    await companyPage.locator('input[id="contact_email"]').fill('mentor.e2e@example.com');

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

    await safeClick(companyPage.getByRole('button', { name: 'Vytvořit' }));

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
    // BL-07/FE-004 fix: `div.filter().first()` matchuje NEJVNITŘNĚJŠÍ ancestor
    // (grid) bez onClick → klik ne naviguje. Klikáme kartu přes její heading
    // (bubluje na onClick kořenového ContainerForEntity nabídky).
    await studentPage.getByRole('heading', { name: practiceTitle }).click();
    await studentPage.waitForURL(/.*\/nabidka\/\d+/);

    await safeClick(studentPage.getByRole('button', { name: 'Podat přihlášku' }));
    // In NabidkaDetailPage, the popup uses "Ano"
    await safeClick(studentPage.getByRole('button', { name: 'Ano', exact: true }));
    await expect(studentPage.getByRole('button', { name: 'Podat přihlášku' })).not.toBeVisible();
    await studentContext.close();


    // --- STEP 4: KATEDRA (PROFESSOR) APPROVES APP — první osa ---
    // Dvouosý model (BL-03): APPLIED → PRELIMINARY_APPROVED patří katedře
    // (student_practices docstring + services.py:334); organizace může až
    // z PRELIMINARY_APPROVED (→ AWAITING_CONTRACT).
    console.log('--- Step 4: Professor (katedra) approving application ---');
    const profContext2 = await browser.newContext({ storageState: 'playwright/.auth/professor.json' });
    const profPage2 = await profContext2.newPage();

    await profPage2.goto('/');
    await waitForAppLoad(profPage2);
    await clickNavLink(profPage2, null, 'Správa stáží');
    await waitForAppLoad(profPage2);
    await expect(profPage2.getByText('Načítání stáží...')).not.toBeVisible({ timeout: 15000 });

    // Otevřít AKTIVNÍ nabídku z přehledu (očíčko „Zobrazit detail" → detail nabídky)
    const activeOfferCard = profPage2.locator('div[id^="practice-offer-"]').filter({ hasText: practiceTitle }).first();
    await expect(activeOfferCard).toBeVisible({ timeout: 15000 });
    await activeOfferCard.getByTitle('Zobrazit detail').click();
    await profPage2.waitForURL(/.*\/nabidka\/\d+/);
    await waitForAppLoad(profPage2);

    // → seznam přihlášených studentů (NabidkaDetailPage: 'Zobrazit přihlášené')
    await safeClick(profPage2.getByRole('button', { name: 'Zobrazit přihlášené' }));
    await profPage2.waitForURL(/.*\/students\/\d+/);

    await profPage2.reload();
    await waitForAppLoad(profPage2);
    await expect(profPage2.getByText('Načítání studentů...')).not.toBeVisible({ timeout: 15000 });

    const studentRow = profPage2.locator('div[id^="user-entity-"]').filter({ hasText: /tsedlacek|Ignác/i }).first();
    await expect(studentRow).toBeVisible({ timeout: 15000 });
    const appDocBtn = studentRow.getByTitle('Zobrazit kartu praxe');
    await expect(appDocBtn).toBeVisible({ timeout: 15000 });
    await appDocBtn.click();

    await profPage2.waitForURL(/.*\/karta-praxe\/.*/);
    await waitForAppLoad(profPage2);

    await safeClick(profPage2.getByRole('button', { name: 'Spravovat' }));
    // Popup na kartě praxe má titulek „Správa přihlášky" (practice_detail.manage_app);
    // starý waypoint „Změnit stav přihlášky" patří PrihlaskyPage (org/osobní).
    await confirmPopup(profPage2, 'Správa přihlášky');
    await profContext2.close();


    // --- STEP 5: ORGANIZACE (COMPANY) APPROVES APP — druhá osa ---
    console.log('--- Step 5: Company approving application ---');
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


    // --- VERIFY: STUDENT SEES APPROVED STATE ---
    console.log('--- Verification: Student sees approved state ---');
    const studentContext2 = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
    const studentPage2 = await studentContext2.newPage();

    await studentPage2.goto('/');
    await waitForAppLoad(studentPage2);
    await studentPage2.goto('/praxe');

    const finalAppCard = studentPage2.locator('div').filter({ hasText: practiceTitle }).first();
    await expect(finalAppCard).toBeVisible();

    // Po obou schváleních (katedra + organizace) je SP v AWAITING_CONTRACT
    // (state_badge = „Čeká na zasmluvnění") — staré „Probíhá" je zastaralý waypoint.
    await expect(finalAppCard.getByText('Čeká na zasmluvnění')
        .or(finalAppCard.getByText('AWAITING_CONTRACT'))
        .or(finalAppCard.getByText('Schváleno'))
        .or(finalAppCard.getByText('Probíhá'))
        .first()).toBeVisible();
    await studentContext2.close();
  });
});
