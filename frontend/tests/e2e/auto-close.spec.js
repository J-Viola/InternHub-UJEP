import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink, confirmPopup, safeClick } from './helpers';
import { execSync } from 'child_process';

test.describe('Auto-Close Practices (E2E)', () => {
  test.setTimeout(120000);

  test('Auto-close uzavře praxi 14 dní před start_date', async ({ browser }) => {
    const uniqueId = Date.now().toString();
    const practiceTitle = `E2E AutoClose ${uniqueId}`;

    // --- STEP 1: COMPANY vytvoří praxi se start_date za 5 dní ---
    const companyContext = await browser.newContext({ storageState: 'playwright/.auth/company.json' });
    const companyPage = await companyContext.newPage();

    await companyPage.goto('/');
    await waitForAppLoad(companyPage);
    await clickNavLink(companyPage, 'Správa organizace', 'Stáže');

    await safeClick(companyPage.getByText('Založit stáž'));
    await companyPage.waitForURL('**/vytvorit-nabidku');

    await companyPage.getByLabel('Název').fill(practiceTitle);
    await companyPage.getByLabel('Popis stáže').fill('Auto-close test practice.');
    await companyPage.getByLabel('Náplň práce').fill('Testing auto-close management command.');

    await expect(companyPage.locator('select[id="contact_user"] option').nth(1)).toBeAttached({ timeout: 10000 });
    await expect(companyPage.locator('select[id="subject_id"] option').nth(1)).toBeAttached({ timeout: 10000 });

    const dateInputs = companyPage.locator('.react-datepicker__input-container input');
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 5);
    const dateStr = futureDate.toLocaleDateString('cs-CZ', { day: '2-digit', month: '2-digit', year: 'numeric' });
    await dateInputs.nth(0).fill(dateStr);
    await dateInputs.nth(0).press('Enter');

    await companyPage.locator('select[id="coefficient"]').selectOption('1');
    await companyPage.locator('select[id="contact_user"]').selectOption({ index: 1 });
    await companyPage.locator('select[id="subject_id"]').selectOption({ index: 1 });
    await companyPage.locator('select[id="available_positions"]').selectOption('2');

    await companyPage.getByLabel('Název').click();

    await expect(companyPage.locator('input[id="end_date"]')).not.toHaveValue('', { timeout: 15000 });
    await safeClick(companyPage.getByRole('button', { name: 'Vytvořit' }));
    await expect(companyPage).toHaveURL(/.*\/praxe/, { timeout: 20000 });
    await companyContext.close();

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
    await profContext.close();

    // --- STEP 3: Transition na OPEN_FOR_APPLICATIONS přes API ---
    // (Starý approve endpoint dává CONTENT_APPROVED; pro auto-close potřebujeme OPEN_FOR_APPLICATIONS)
    const adminContext = await browser.newContext({ storageState: 'playwright/.auth/admin.json' });
    const adminPage = await adminContext.newPage();
    const res = await adminPage.request.get('http://localhost:8000/api/practices/?search=' + encodeURIComponent(practiceTitle));
    const data = await res.json();
    const practiceId = data.results?.[0]?.practice_id;
    if (!practiceId) throw new Error('Practice not found via API');

    // BL-07/FE-004: schválení garantem nabídku automaticky aktivuje
    // (SRS analysis.txt:2248 → OPEN_FOR_APPLICATIONS), takže pomocný přechod
    // přes API už obvykle není potřeba; ponechán jen jako fallback.
    if (Number(data.results?.[0]?.workflow_state) !== 3) {
      const transitionRes = await adminPage.request.post(
        `http://localhost:8000/api/practices/${practiceId}/transition/`,
        { data: { target_state: 3 } } // OPEN_FOR_APPLICATIONS = 3
      );
      if (transitionRes.status() !== 200) {
        throw new Error(`Fallback transition to OPEN_FOR_APPLICATIONS failed: ${transitionRes.status()}`);
      }
    }
    await adminContext.close();

    // --- STEP 4: Spustit auto_close management command ---
    execSync(
      'cd /media/F/Github/InternHub-UJEP/backend && python manage.py auto_close_practices',
      { encoding: 'utf-8' }
    );

    // --- STEP 5: Ověřit CLOSED_FOR_APPLICATIONS v UI ---
    const companyContext2 = await browser.newContext({ storageState: 'playwright/.auth/company.json' });
    const companyPage2 = await companyContext2.newPage();
    await companyPage2.goto('/praxe');
    await waitForAppLoad(companyPage2);

    const card = companyPage2.locator('div').filter({ hasText: practiceTitle }).first();
    await expect(card).toBeVisible();
    await expect(
      card.getByText('Uzavřeno pro přihlášky').or(card.getByText('CLOSED_FOR_APPLICATIONS'))
    ).toBeVisible();
    await companyContext2.close();
  });
});
