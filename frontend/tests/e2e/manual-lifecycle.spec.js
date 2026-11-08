import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink, safeClick, confirmPopup } from './helpers';

test.describe('Manual External Practice Lifecycle (E2E)', () => {
  test.setTimeout(120000);

  test('Externí praxe: vytvoření → content approval flow', async ({ browser }) => {
    const uniqueId = Date.now().toString();
    const practiceTitle = `E2E External ${uniqueId}`;

    // --- STEP 1: STUDENT vytvoří externí praxi ---
    const studentContext = await browser.newContext({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/student.json` });
    const studentPage = await studentContext.newPage();

    await studentPage.goto('/vytvorit-externi-praxi');
    await waitForAppLoad(studentPage);

    await studentPage.getByLabel('Název organizace').fill('Externí Test Org');
    await studentPage.getByLabel('Kontaktní osoba').fill('Jan Test');
    await studentPage.getByLabel('Kontaktní email').fill('test@example.com');
    await studentPage.getByLabel('Kontaktní telefon').fill('123456789');

    await expect(studentPage.locator('select[id="subject_id"] option').nth(1)).toBeAttached({ timeout: 10000 });
    await studentPage.locator('select[id="subject_id"]').selectOption({ label: 'KI/PRAX1 - Odborná praxe 1' });

    // BL-07/PBUG-02: 'Název' musí být exact — na stránce je i 'Název organizace'
    // (getByLabel s podřetězcem matchoval 2 elementy → strict-mode violation).
    await studentPage.getByLabel('Název', { exact: true }).fill(practiceTitle);
    await studentPage.getByLabel('Popis stáže').fill('External practice test');
    await studentPage.getByLabel('Náplň práce').fill('Testing external flow');

    const dateInputs = studentPage.locator('.react-datepicker__input-container input');
    // BL-07: deterministický dd.mm.rrrr — toLocaleDateString('cs-CZ') vrací
    // "11. 11. 2026" (s mezerami), které react-datepicker neparsuje → start_date
    // se nikdy nenastavil a end_date auto-výpočet nikdy nespustil.
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 30);
    const pad = (n) => String(n).padStart(2, '0');
    const dateStr = `${pad(futureDate.getDate())}.${pad(futureDate.getMonth() + 1)}.${futureDate.getFullYear()}`;
    await dateInputs.nth(0).fill(dateStr);
    await dateInputs.nth(0).press('Enter');

    await studentPage.locator('select[id="coefficient"]').selectOption('1');
    await studentPage.locator('select[id="available_positions"]').selectOption('2');

    // BL-07/PBUG-01 (externí větev): povinná příloha + čekání na auto-vypočtený
    // end_date — bez obojího klientská validace zabrání odeslání.
    const detailsPdf = '/tmp/e2e_external_details.pdf';
    require('fs').writeFileSync(detailsPdf, '%PDF-1.4\n% E2E synthetic practice details\n');
    await studentPage.locator('input[type="file"]').setInputFiles(detailsPdf);
    await expect(studentPage.locator('input[id="end_date"]')).not.toHaveValue('', { timeout: 15000 });

    await safeClick(studentPage.getByRole('button', { name: 'Vytvořit praxi' }));
    await expect(studentPage).toHaveURL(/.*\/nabidka/, { timeout: 20000 });

    // Ověřit AWAITING_CONTENT_APPROVAL (PENDING_CONTENT_APPROVAL) v /praxe
    await studentPage.goto('/praxe');
    await waitForAppLoad(studentPage);
    const appCard = studentPage.locator('div').filter({ hasText: practiceTitle }).first();
    await expect(appCard).toBeVisible();
    await expect(
      appCard.getByText('Čeká na schválení obsahu').or(appCard.getByText('PENDING_CONTENT_APPROVAL'))
    ).toBeVisible();
    await studentContext.close();

    // --- STEP 2: PROFESSOR schválí obsah praxe ---
    const profContext = await browser.newContext({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/professor.json` });
    const profPage = await profContext.newPage();

    await profPage.goto('/');
    await waitForAppLoad(profPage);
    await clickNavLink(profPage, null, 'Správa stáží');
    await waitForAppLoad(profPage);
    await expect(profPage.getByText('Načítání stáží...')).not.toBeVisible({ timeout: 15000 });

    const practiceCard = profPage.locator('div[id^="practice-offer-"]').filter({ hasText: practiceTitle }).first();
    await expect(practiceCard).toBeVisible({ timeout: 15000 });
    const gearBtn = practiceCard.getByTitle('Změnit stav nabídky');
    await expect(gearBtn).toBeVisible();
    await gearBtn.click();
    await confirmPopup(profPage, 'změnit stav nabídky');

    // --- STEP 3: PO schválení je nabídka automaticky AKTIVNÍ ---
    // SRS oracle: analysis.txt:2248 — „Garant může inzerát schválit (přechod do
    // stavu „Aktivní", kdy je viditelný pro studenty)". Žádný manuální krok.
    await profPage.reload();
    await waitForAppLoad(profPage);
    await expect(profPage.getByText('Načítání stáží...')).not.toBeVisible({ timeout: 15000 });

    // 1) nabídka zůstává viditelná v přehledu katedry (FE-004: nesmí zmizet)
    const updatedCard = profPage.locator('div[id^="practice-offer-"]').filter({ hasText: practiceTitle }).first();
    await expect(updatedCard).toBeVisible({ timeout: 15000 });

    // 2) je viditelná pro studenty v katalogu — katalog filtruje VÝHRADNĚ
    //    OPEN_FOR_APPLICATIONS, takže samotná přítomnost karty = důkaz aktivace
    //    (StateBadge se studentům v katalogu nezobrazí — NabidkaEntity jej
    //    renderuje jen pro department/admin/org role).
    const studentCtx2 = await browser.newContext({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/student.json` });
    const studentPage2 = await studentCtx2.newPage();
    await studentPage2.goto('/');
    await waitForAppLoad(studentPage2);
    await clickNavLink(studentPage2, null, 'Nabídka praxí');
    await studentPage2.locator('input[id="title"]').fill(practiceTitle);
    await expect(studentPage2.getByRole('heading', { name: practiceTitle })).toBeVisible({ timeout: 15000 });
    await studentCtx2.close();

    await profContext.close();
  });
});
