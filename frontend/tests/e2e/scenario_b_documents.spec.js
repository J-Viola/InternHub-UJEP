import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink, confirmPopup, safeClick } from './helpers';
import path from 'path';

test.describe('Scenario B: Document Lifecycle Flow', () => {
  test.setTimeout(150000);

  const uniqueId = Date.now().toString();
  const practiceTitle = `Doc Test Practice ${uniqueId}`;
  const docFilePath = path.join(__dirname, '../../../backend/storage/default_documents/default_contract.docx');

  test('Upload -> Reject -> Re-upload -> Approve document', async ({ browser }) => {

    // --- STEP 1: SETUP APPROVED PRACTICE ---
    // (Company creates, Professor approves offer, Student applies, Company approves app, Professor approves app)
    // We'll follow the dual approval flow pattern but streamlined

    console.log('--- Step 1: Setting up approved practice ---');
    const companyContext = await browser.newContext({ storageState: 'playwright/.auth/company.json' });
    const companyPage = await companyContext.newPage();
    await companyPage.goto('/');
    await waitForAppLoad(companyPage);
    await clickNavLink(companyPage, 'Správa organizace', 'Stáže');
    await companyPage.getByText('Založit stáž').click();
    await companyPage.getByLabel('Název').fill(practiceTitle);
    await companyPage.getByLabel('Popis stáže').fill('Doc test desc');
    await companyPage.getByLabel('Náplň práce').fill('Doc test resp');
    await expect(companyPage.locator('select[id="subject_id"] option').nth(1)).toBeAttached();
    await companyPage.locator('.react-datepicker__input-container input').nth(0).fill('01.01.2027');
    await companyPage.locator('.react-datepicker__input-container input').nth(0).press('Enter');
    await companyPage.locator('select[id="coefficient"]').selectOption('1');
    await companyPage.locator('select[id="contact_user"]').selectOption({ index: 1 });
    await companyPage.locator('select[id="subject_id"]').selectOption({ index: 1 });
    await companyPage.locator('select[id="available_positions"]').selectOption('2');
    await companyPage.getByLabel('Název').click();
    await expect(companyPage.locator('input[id="end_date"]')).not.toHaveValue('', { timeout: 15000 });
    await safeClick(companyPage.getByRole('button', { name: 'Vytvořit' }));
    await expect(companyPage).toHaveURL(/.*\/praxe/);
    await companyContext.close();

    const profContext = await browser.newContext({ storageState: 'playwright/.auth/professor.json' });
    const profPage = await profContext.newPage();
    await profPage.goto('/');
    await waitForAppLoad(profPage);
    await clickNavLink(profPage, null, 'Správa stáží');
    const gearBtn = profPage.locator('div[id^="practice-offer-"]').filter({ hasText: practiceTitle }).getByTitle('Změnit stav nabídky');
    await gearBtn.click();
    await confirmPopup(profPage, 'změnit stav nabídky');

    const studentContext = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
    const studentPage = await studentContext.newPage();
    await studentPage.goto('/');
    await waitForAppLoad(studentPage);
    await clickNavLink(studentPage, null, 'Nabídka praxí');
    await studentPage.locator('input[id="title"]').fill(practiceTitle);
    await studentPage.locator('div').filter({ hasText: practiceTitle }).first().click();
    await safeClick(studentPage.getByRole('button', { name: 'Podat přihlášku' }));
    await safeClick(studentPage.getByRole('button', { name: 'Ano', exact: true }));

    // Quick approve by company and prof
    await companyPage.context().storageState({ path: 'playwright/.auth/company.json' }); // reuse
    const companyPage2 = await (await browser.newContext({ storageState: 'playwright/.auth/company.json' })).newPage();
    await companyPage2.goto('/');
    await clickNavLink(companyPage2, 'Správa organizace', 'Přihlášky');
    await companyPage2.locator('div[id^="application-entity-"]').filter({ hasText: practiceTitle }).locator('button').first().click();
    await confirmPopup(companyPage2, 'Změnit stav přihlášky');
    await companyPage2.context().close();

    await profPage.reload();
    await clickNavLink(profPage, null, 'Správa stáží');
    await profPage.locator('div').filter({ hasText: practiceTitle }).filter({ visible: true }).first().click();
    await safeClick(profPage.getByRole('button', { name: 'Přihlášení studenti' }));
    const studentRow = profPage.locator('div[id^="user-entity-"]').filter({ hasText: /tsedlacek/i }).first();
    await studentRow.getByTitle('Zobrazit kartu praxe').click();
    await safeClick(profPage.getByRole('button', { name: 'Spravovat' }));
    await confirmPopup(profPage, 'Změnit stav přihlášky');

    // --- STEP 2: STUDENT UPLOADS DOCUMENT ---
    console.log('--- Step 2: Student uploading document ---');
    await studentPage.goto('/');
    await studentPage.goto('/praxe');
    await studentPage.locator('div').filter({ hasText: practiceTitle }).first().click();

    // Find "Návrh smlouvy" section and click Upload
    const contractSection = studentPage.locator('div').filter({ hasText: 'Návrh smlouvy' }).last();
    const fileChooserPromise = studentPage.waitForEvent('filechooser');
    await safeClick(studentPage.getByRole('button', { name: 'Nahrát' }).first()); // First upload button is usually for the first doc
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(docFilePath);

    await expect(studentPage.getByText('Uloženo')).toBeVisible();
    await expect(studentPage.getByText('Čeká na schválení')).toBeVisible();

    // --- STEP 3: PROFESSOR REJECTS DOCUMENT ---
    console.log('--- Step 3: Professor rejecting document ---');
    await profPage.reload();
    await waitForAppLoad(profPage);
    // Should still be on the Karta praxe page. DocsPanel should show the document.
    const docReviewBtn = profPage.getByRole('button', { name: 'KONTROLA DOKUMENTŮ' });
    await docReviewBtn.click();

    // In DocsPanel, click Manage for the first document
    await safeClick(profPage.getByRole('button', { name: 'Spravovat' }).first());

    // Fill rejection note and click Reject
    await profPage.getByPlaceholder('Poznámka k dokumentu (nepovinné)').fill('Please fix the date in the contract.');
    await safeClick(profPage.getByRole('button', { name: 'Zamítnout' }));

    await expect(profPage.getByText('Zamítnuto')).toBeVisible();

    // --- STEP 4: STUDENT RE-UPLOADS ---
    console.log('--- Step 4: Student re-uploading document ---');
    await studentPage.reload();
    await expect(studentPage.getByText('Zamítnuto')).toBeVisible();
    await expect(studentPage.getByText('Please fix the date in the contract.')).toBeVisible();

    const fileChooserPromise2 = studentPage.waitForEvent('filechooser');
    await safeClick(studentPage.getByRole('button', { name: 'Nahrát' }).first());
    const fileChooser2 = await fileChooserPromise2;
    await fileChooser2.setFiles(docFilePath);

    await expect(studentPage.getByText('Čeká na schválení')).toBeVisible();

    // --- STEP 5: PROFESSOR APPROVES ---
    console.log('--- Step 5: Professor approving document ---');
    await profPage.reload();
    await safeClick(profPage.getByRole('button', { name: 'KONTROLA DOKUMENTŮ' }));
    await safeClick(profPage.getByRole('button', { name: 'Spravovat' }).first());
    await safeClick(profPage.getByRole('button', { name: 'Schválit' }));

    await expect(profPage.getByText('Schváleno')).toBeVisible();

    await studentContext.close();
    await profContext.close();
  });
});
