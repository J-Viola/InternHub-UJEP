import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink, confirmPopup, safeClick } from '../helpers';

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
    // BL-07: 'Odpovědnost stáže' je zastaralý label — formulář používá
    // t('form.responsibilities') = 'Náplň práce' (jako ostatní specy).
    await companyPage.getByLabel('Náplň práce').fill('Testing cancellation flow.');
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
    // BL-07/FE-004 fix: klik přes heading karty (div.filter().first() = ancestor bez onClick).
    await expect(studentPage.getByRole('heading', { name: practiceTitle })).toBeVisible();
    await studentPage.getByRole('heading', { name: practiceTitle }).click();
    await studentPage.waitForURL(/.*\/nabidka\/\d+/);

    await studentPage.getByRole('button', { name: 'Podat přihlášku' }).click();
    // In NabidkaDetailPage, the popup uses "Ano"
    await studentPage.getByRole('button', { name: 'Ano', exact: true }).click();
    await expect(studentPage.getByRole('button', { name: 'Podat přihlášku' })).not.toBeVisible();
    await studentContext.close();


    // --- STEP 4: STORNO NABÍDKY — reálná UI akce „Zrušit nabídku" ---
    // Backend CanCancelPractice: admin / vedoucí katedry / garant. E2E profesor
    // je záměrně „vy" (TestResetDBView._create_e2e_test_users) → storno tedy
    // provádí admin. Stará cesta (professor popup „Spravovat" → Zamítnout)
    // končila 400 PRACTICE_ALREADY_FINALIZED a žádné UI pro storno neexistovalo
    // (PBUG-BL07-07).
    console.log('--- Step 4: Admin cancelling the offer ---');
    const adminContext = await browser.newContext({ storageState: 'playwright/.auth/admin.json' });
    const adminPage = await adminContext.newPage();

    await adminPage.goto('/');
    await waitForAppLoad(adminPage);
    // Admin končí po přihlášení rovnou v katalogu (viz index.js) a boční
    // navigace na /nabidka nemusí obsahovat link — jdeme na route přímo.
    await adminPage.goto('/nabidka');
    await waitForAppLoad(adminPage);

    // Najít nabídku v katalogu a otevřít detail
    await adminPage.locator('input[id="title"]').fill(practiceTitle);
    await expect(adminPage.getByText('Načítání nabídek...')).not.toBeVisible({ timeout: 15000 });
    await expect(adminPage.getByRole('heading', { name: practiceTitle })).toBeVisible({ timeout: 15000 });
    await adminPage.getByRole('heading', { name: practiceTitle }).click();
    await adminPage.waitForURL(/.*\/nabidka\/\d+/);
    await waitForAppLoad(adminPage);

    // Reálná akce „Zrušit nabídku" (na detailu viditelná jen pro oprávněné roly)
    await safeClick(adminPage.getByRole('button', { name: 'Zrušit nabídku' }));
    await adminPage.locator('#cancel-reason').fill('E2E: storno nabídky pro ověření kaskády přihlášek.');
    await safeClick(adminPage.locator('#popup-confirm-button'));

    // Úspěch = popup se zavře (při chybě zůstává otevřený a volá error resolver)
    await expect(adminPage.locator('[data-testid="popup-con"]')).not.toBeVisible({ timeout: 15000 });
    await adminContext.close();


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
    // BL-07: po stornu nabídky má SP `workflow_status="CANCELLED"` (is_cancelled
    // předchází workflow_state) → StateBadge/label = „Stornováno" (kanonický
    // workflow_status_label). Ostatní texty ponechány pro ostatní cesty.
    await expect(
        cancelledAppCard.getByText('Stornováno')
            .or(cancelledAppCard.getByText('Zrušeno'))
            .or(cancelledAppCard.getByText('Zamítnuto'))
            .or(cancelledAppCard.getByText('Obsah zamítnut'))
            .first()
    ).toBeVisible({ timeout: 10000 });

    console.log('Verified: student sees cancelled/rejected status');
    await studentContext2.close();
  });
});
