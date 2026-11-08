import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink, confirmPopup, safeClick } from './helpers';
import path from 'path';

test.describe('Scenario B: Document Lifecycle Flow', () => {
  test.setTimeout(150000);

  const uniqueId = Date.now().toString();
  const practiceTitle = `Doc Test Practice ${uniqueId}`;
  // BL-07/PBUG-BL07-09 (repo data): default_documents/default_contract.docx je
  // v repozitáři prázdný (0 B) → server oprávněně odmítne prázdný upload (400
  // EMPTY). Pro tuto journey používáme platný, v repozitáři trackovaný docx.
  const docFilePath = path.join(__dirname, '../../../backend/storage/documents/contract_eccbc87e_20250723081241.docx');

  test('Upload -> Reject -> Re-upload -> Approve document', async ({ browser }) => {

    // --- STEP 1: SETUP APPROVED PRACTICE ---
    // (Company creates, Professor approves offer, Student applies, Company approves app, Professor approves app)
    // We'll follow the dual approval flow pattern but streamlined

    console.log('--- Step 1: Setting up approved practice ---');
    const companyContext = await browser.newContext({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/company.json` });
    const companyPage = await companyContext.newPage();
    await companyPage.goto('/');
    await waitForAppLoad(companyPage);
    await clickNavLink(companyPage, 'Správa organizace', 'Stáže');
    await companyPage.getByText('Založit stáž').click();
    await companyPage.getByLabel('Název').fill(practiceTitle);
    await companyPage.getByLabel('Popis stáže').fill('Doc test desc');
    await companyPage.getByLabel('Náplň práce').fill('Doc test resp');
    // BL-07/PBUG-01: mentor_name + contact_email jsou povinné na serveru (PracticeSerializer)
    await companyPage.locator('input[id="mentor_name"]').fill('Mentor E2E');
    await companyPage.locator('input[id="contact_email"]').fill('mentor.e2e@example.com');
    await expect(companyPage.locator('select[id="subject_id"] option').nth(1)).toBeAttached();
    await companyPage.locator('.react-datepicker__input-container input').nth(0).fill('01.01.2027');
    await companyPage.locator('.react-datepicker__input-container input').nth(0).press('Enter');
    await companyPage.locator('select[id="coefficient"]').selectOption('1');
    await companyPage.locator('select[id="contact_user"]').selectOption({ index: 1 });
    await companyPage.locator('select[id="subject_id"]').selectOption({ label: 'KI/PRAX1 - Odborná praxe 1' });
    await companyPage.locator('select[id="available_positions"]').selectOption('2');
    await companyPage.getByLabel('Název').click();
    await expect(companyPage.locator('input[id="end_date"]')).not.toHaveValue('', { timeout: 15000 });
    await safeClick(companyPage.getByRole('button', { name: 'Vytvořit' }));
    await expect(companyPage).toHaveURL(/.*\/praxe/);
    await companyContext.close();

    const profContext = await browser.newContext({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/professor.json` });
    const profPage = await profContext.newPage();
    await profPage.goto('/');
    await waitForAppLoad(profPage);
    await clickNavLink(profPage, null, 'Správa stáží');
    const gearBtn = profPage.locator('div[id^="practice-offer-"]').filter({ hasText: practiceTitle }).getByTitle('Změnit stav nabídky');
    await gearBtn.click();
    await confirmPopup(profPage, 'změnit stav nabídky');

    const studentContext = await browser.newContext({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/student.json` });
    const studentPage = await studentContext.newPage();
    await studentPage.goto('/');
    await waitForAppLoad(studentPage);
    await clickNavLink(studentPage, null, 'Nabídka praxí');
    await studentPage.locator('input[id="title"]').fill(practiceTitle);
    // BL-07/FE-004 fix: klik přes heading karty (div.filter().first() = ancestor bez onClick).
    await studentPage.getByRole('heading', { name: practiceTitle }).click();
    await studentPage.waitForURL(/.*\/nabidka\/\d+/);
    await safeClick(studentPage.getByRole('button', { name: 'Podat přihlášku' }));
    await safeClick(studentPage.getByRole('button', { name: 'Ano', exact: true }));

    // --- SCHVÁLENÍ DVĚMA OSAMI (BL-03 dvouosý model) ---
    // 1) KATEDRA (professor): APPLIED → PRELIMINARY_APPROVED patří katedře.
    //    Cesta: aktivní nabídka v přehledu → „Zobrazit přihlášené" → studenti
    //    → karta praxe → Spravovat → popup „Správa přihlášky".
    await profPage.reload();
    await clickNavLink(profPage, null, 'Správa stáží');
    await expect(profPage.getByText('Načítání stáží...')).not.toBeVisible({ timeout: 15000 });
    const offerCardScen = profPage.locator('div[id^="practice-offer-"]').filter({ hasText: practiceTitle }).first();
    await expect(offerCardScen).toBeVisible({ timeout: 15000 });
    await offerCardScen.getByTitle('Zobrazit detail').click();
    await profPage.waitForURL(/.*\/nabidka\/\d+/);
    await waitForAppLoad(profPage);
    await safeClick(profPage.getByRole('button', { name: 'Zobrazit přihlášené' }));
    await profPage.waitForURL(/.*\/students\/\d+/);
    await profPage.reload();
    await waitForAppLoad(profPage);
    const studentRowScen = profPage.locator('div[id^="user-entity-"]').filter({ hasText: /tsedlacek|Ignác/i }).first();
    await expect(studentRowScen).toBeVisible({ timeout: 15000 });
    await studentRowScen.getByTitle('Zobrazit kartu praxe').click();
    await profPage.waitForURL(/.*\/karta-praxe\/.*/);
    await waitForAppLoad(profPage);
    await safeClick(profPage.getByRole('button', { name: 'Spravovat' }));
    // BL-07: titulek popupu na kartě praxe = „Správa přihlášky" (practice_detail.manage_app);
    // staré „Změnit stav přihlášky" patří PrihlaskyPage.
    await confirmPopup(profPage, 'Správa přihlášky');

    // 2) ORGANIZACE (company): PRELIMINARY_APPROVED → AWAITING_CONTRACT.
    //    (bez této opravy pořadí končil první pokus 400 — osa katedry)
    const companyPage2 = await (await browser.newContext({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/company.json` })).newPage();
    await companyPage2.goto('/');
    await clickNavLink(companyPage2, 'Správa organizace', 'Přihlášky');
    await companyPage2.locator('div[id^="application-entity-"]').filter({ hasText: practiceTitle }).locator('button').first().click();
    await confirmPopup(companyPage2, 'Změnit stav přihlášky');
    await companyPage2.context().close();

    // --- STEP 2: STUDENT UPLOADS DOCUMENT ---
    console.log('--- Step 2: Student uploading document ---');
    await studentPage.goto('/');
    // BL-07: vlastní SP vede /moje-prihlasky → StudentApplicationCard (onClick
    // /karta-praxe/{sp}). Starý klik na /praxe přes div.filter().first()
    // matchoval ancestor bez onClick → žádná navigace → chybělo tlačítko 'Nahrát'.
    await studentPage.goto('/moje-prihlasky');
    await waitForAppLoad(studentPage);
    // BL-07: StudentApplicationCard používá Headings sizeTag="h5-bold" → po
    // PBUG-BL07-08 opravě vykreslí skutečný <h5> (heading role funguje).
    await studentPage.getByRole('heading', { name: practiceTitle }).click();
    await studentPage.waitForURL(/.*\/karta-praxe\/\d+/);
    await waitForAppLoad(studentPage);

    // Find "Návrh smlouvy" section and click Upload
    const contractSection = studentPage.locator('div').filter({ hasText: 'Návrh smlouvy' }).last();
    const fileChooserPromise = studentPage.waitForEvent('filechooser');
    await safeClick(studentPage.getByRole('button', { name: 'Nahrát' }).first()); // First upload button is usually for the first doc
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(docFilePath);

    // BL-07: kanonický text toastu po úspěšném uploadu = „Dokument úspěšně nahrán"
    // (practice_detail.upload_success); staré „Uloženo" se v překladu nevyskytuje.
    await expect(studentPage.getByText('Dokument úspěšně nahrán')).toBeVisible({ timeout: 15000 });
    await expect(studentPage.getByText('Čeká na schválení')).toBeVisible();

    // --- STEP 3: PROFESSOR REJECTS DOCUMENT ---
    console.log('--- Step 3: Professor rejecting document ---');
    await profPage.reload();
    await waitForAppLoad(profPage);
    // BL-07: DocsPanel má na kartě dokumentu přímo tlačítka Schválit/Zamítnout
    // (žádný popup „KONTROLA DOKUMENTŮ"/„Spravovat" — ten by jen překryl stránku
    // overlayem a zablokoval kliky). Poznámka k zamítnutí jde přes window.prompt.
    profPage.once('dialog', (dialog) => dialog.accept('Please fix the date in the contract.'));
    await safeClick(profPage.getByRole('button', { name: 'Zamítnout' }).first());
    // docs.status_rejected = „Vráceno k opravě" (kanonický label)
    await expect(profPage.getByText('Vráceno k opravě').first()).toBeVisible({ timeout: 15000 });
    // --- STEP 4: STUDENT RE-UPLOADS ---
    console.log('--- Step 4: Student re-uploading document ---');
    await studentPage.reload();
    await waitForAppLoad(studentPage);
    // BL-07: kanonický label zamítnutého dokumentu = „Vráceno k opravě"
    // (docs.status_rejected); poznámka se zobrazuje z review_note na kartě.
    await expect(studentPage.getByText('Vráceno k opravě').first()).toBeVisible({ timeout: 15000 });
    await expect(studentPage.getByText('Please fix the date in the contract.').first()).toBeVisible();

    const fileChooserPromise2 = studentPage.waitForEvent('filechooser');
    await safeClick(studentPage.getByRole('button', { name: 'Nahrát' }).first());
    const fileChooser2 = await fileChooserPromise2;
    await fileChooser2.setFiles(docFilePath);

    // Re-upload resetuje status na PENDING (upload update()) → potvrzení
    // toastem practice_detail.upload_success (jako v kroku 2).
    await expect(studentPage.getByText('Dokument úspěšně nahrán')).toBeVisible({ timeout: 15000 });

    // --- STEP 5: PROFESSOR APPROVES ---
    console.log('--- Step 5: Professor approving document ---');
    await profPage.reload();
    await waitForAppLoad(profPage);
    await safeClick(profPage.getByRole('button', { name: 'Schválit' }).first());
    // docs.status_approved = „Schváleno"
    await expect(profPage.getByText('Schváleno').first()).toBeVisible({ timeout: 15000 });

    await studentContext.close();
    await profContext.close();
  });
});
