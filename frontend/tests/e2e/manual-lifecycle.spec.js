import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink, safeClick, confirmPopup } from './helpers';

test.describe('Manual External Practice Lifecycle (E2E)', () => {
  test.setTimeout(120000);

  test('Externí praxe: vytvoření → content approval flow', async ({ browser }) => {
    const uniqueId = Date.now().toString();
    const practiceTitle = `E2E External ${uniqueId}`;

    // --- STEP 1: STUDENT vytvoří externí praxi ---
    const studentContext = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
    const studentPage = await studentContext.newPage();

    await studentPage.goto('/vytvorit-externi-praxi');
    await waitForAppLoad(studentPage);

    await studentPage.getByLabel('Název organizace').fill('Externí Test Org');
    await studentPage.getByLabel('Kontaktní osoba').fill('Jan Test');
    await studentPage.getByLabel('Kontaktní email').fill('test@example.com');
    await studentPage.getByLabel('Kontaktní telefon').fill('123456789');

    await expect(studentPage.locator('select[id="subject_id"] option').nth(1)).toBeAttached({ timeout: 10000 });
    await studentPage.locator('select[id="subject_id"]').selectOption({ index: 1 });

    await studentPage.getByLabel('Název').fill(practiceTitle);
    await studentPage.getByLabel('Popis stáže').fill('External practice test');
    await studentPage.getByLabel('Náplň práce').fill('Testing external flow');

    const dateInputs = studentPage.locator('.react-datepicker__input-container input');
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 30);
    const dateStr = futureDate.toLocaleDateString('cs-CZ', { day: '2-digit', month: '2-digit', year: 'numeric' });
    await dateInputs.nth(0).fill(dateStr);
    await dateInputs.nth(0).press('Enter');

    await studentPage.locator('select[id="coefficient"]').selectOption('1');
    await studentPage.locator('select[id="available_positions"]').selectOption('2');

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
    const profContext = await browser.newContext({ storageState: 'playwright/.auth/professor.json' });
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

    // --- STEP 3: Ověřit CONTENT_APPROVED / OPEN_FOR_APPLICATIONS ---
    await profPage.reload();
    await waitForAppLoad(profPage);
    await expect(profPage.getByText('Načítání stáží...')).not.toBeVisible({ timeout: 15000 });

    const updatedCard = profPage.locator('div[id^="practice-offer-"]').filter({ hasText: practiceTitle }).first();
    await expect(updatedCard.getByText('Obsah schválen').or(updatedCard.getByText('CONTENT_APPROVED'))
      .or(updatedCard.getByText('Otevřeno pro přihlášky')).or(updatedCard.getByText('OPEN_FOR_APPLICATIONS'))
    ).toBeVisible();

    await profContext.close();
  });
});
