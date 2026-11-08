import { test, expect } from '@playwright/test';
import { waitForAppLoad, safeClick } from './helpers';
import { execSync } from 'child_process';
import path from 'path';

test.describe('Evaluace Lifecycle (E2E)', () => {
  test.setTimeout(120000);

  test('Mentor vyplní evaluační formulář pro praxi ve stavu ENDED', async ({ browser }) => {
    const uniqueId = Date.now().toString();
    const practiceTitle = `E2E Eval ${uniqueId}`;

    // --- SETUP: fixture přes validní Python soubor (BL-07/PBUG-03) ---
    // Dřívější inline `shell -c` (nové řádky složené na jednu) byl neplatný
    // a běžel s výchozím nastavením → hrozil zápis mimo disposable DB.
    // Nyní: DJANGO_SETTINGS_MODULE + povinné E2E_DB_NAME + guard v helperu.
    const helperScript = path.join(__dirname, 'helpers', 'seed_ended_practice.py');
    // Fixture se pouští v izolovaném backend kontejneru (hostitelský python
    // nemá Django závislosti). Kontejner i disposable DB jsou konfigurovatelné.
    const container = process.env.E2E_BACKEND_CONTAINER || 'internhub-e2e-backend';
    const e2eDbName = process.env.E2E_DB_NAME || 'internhub_e2e_test';
    const shellOutput = execSync(
      `docker exec -i -e DJANGO_SETTINGS_MODULE=app.e2e_settings -e E2E_DB_NAME=${e2eDbName} ` +
        `-e E2E_PRACTICE_TITLE="${practiceTitle}" ${container} python manage.py shell --no-startup < "${helperScript}"`,
      { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'pipe'] }
    );
    const spId = shellOutput
      .trim()
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => /^\d+$/.test(line))
      .pop();
    if (!spId) {
      throw new Error('Failed to create ENDED student practice via fixture helper. Output: ' + shellOutput);
    }

    // --- STEP 1: Login jako mentor (professor) ---
    const profContext = await browser.newContext({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/professor.json` });
    const profPage = await profContext.newPage();

    await profPage.goto(`/evaluace/${spId}`);
    await waitForAppLoad(profPage);

    // --- STEP 2: Vyplnit evaluační formulář ---
    // Hodnocení: expertise, communication, initiative (range inputs)
    const ranges = profPage.locator('input[type="range"]');
    await expect(ranges.nth(0)).toBeVisible({ timeout: 10000 });
    await ranges.nth(0).fill('4');
    await ranges.nth(1).fill('5');
    await ranges.nth(2).fill('3');

    await profPage.locator('textarea[name="overall_comment"]').fill('E2E test evaluation comment');

    // --- STEP 3: Nahrát PDF protokol ---
    const pdfPath = '/tmp/e2e_eval_protocol.pdf';
    require('fs').writeFileSync(pdfPath, '%PDF-1.4 fake pdf content');
    await profPage.locator('input[type="file"]').setInputFiles(pdfPath);

    // --- STEP 4: Odeslat formulář ---
    await safeClick(profPage.getByRole('button', { name: /Odeslat|Submit|Uložit/i }));

    // --- STEP 5: Ověřit úspěch ---
    // FE-014: EvaluationForm úspěšně naviguje na kartu praxe (/karta-praxe/:id),
    // dřívější očekávání /praxe po tomto přesunu neodpovídá chování formuláře.
    await expect(profPage).toHaveURL(/.*\/karta-praxe\/\d+/, { timeout: 20000 });

    await profContext.close();
  });
});
