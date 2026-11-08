import { test, expect } from '@playwright/test';
import { waitForAppLoad, checkHeading } from '../helpers';

test.describe('Edit practice offer', () => {
  test.use({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/company.json` });
  test.setTimeout(60000);

  // Store the practice ID from the scenario for direct navigation
  let practiceId = null;

  test.beforeAll(async ({ request }) => {
    const resp = await request.post(`${process.env.E2E_API_URL || 'http://localhost:8000'}/api/test/scenario/practice-editable/`);
    const data = await resp.json();
    practiceId = data.result.practice_id;
    console.log(`Practice ${practiceId} ready for edit tests`);
  });

  /**
   * Helper to find an existing practice and navigate to its edit page.
   * Navigates directly to avoid event bubbling / API resource issues.
   */
  async function findAndEditFirstPractice(page) {
    // Nejdřív seznam (aby navigate(-1) po uložení vrátil na /praxe), pak editace.
    await page.goto('/praxe');
    await waitForAppLoad(page);
    await page.goto(`/upravit-nabidku/${practiceId}`);
    console.log(`Navigated to /upravit-nabidku/${practiceId}`);

    // Wait for the loading state to clear — the page shows
    // "Načítání formuláře..." while initFetch() calls 3 APIs.
    // The loading text translates to t('form.loading_form').
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        await page.waitForTimeout(3000);
        await expect(page.getByText('Načítání formuláře')).not.toBeVisible({ timeout: 20000 });
        console.log('Loading state cleared, form should be ready');
        break;
      } catch (loadingErr) {
        console.log(`Loading state did not clear on attempt ${attempt + 1}. Reloading...`);
        await page.reload();
      }
    }

    // Debug: check what's in the DOM after loading cleared
    const currentUrl = page.url();
    console.log(`URL after loading cleared: ${currentUrl}`);
    const titleCount = await page.locator('input[id="title"]').count();
    console.log(`input[id="title"] count: ${titleCount}`);
    const allInputs = await page.locator('input').evaluateAll(inputs => inputs.map(i => ({id: i.id, name: i.name, type: i.type, placeholder: i.placeholder}))).catch(() => 'ERROR');
    console.log(`All inputs: ${JSON.stringify(allInputs)}`);
    const bodyText = await page.locator('body').innerText().catch(() => 'ERROR');
    console.log(`Page body (first 400 chars): ${bodyText.substring(0, 400)}`);

    // Wait for the form to fully load
    const titleInput = page.locator('input[id="title"]');
    await expect(titleInput).toBeVisible({ timeout: 15000 });
  }

  test('EP01 - can edit practice title', async ({ page }) => {
    // SKIPPED: CRA dev server proxy connection pool exhaustion.
    // The UpravitNabidku page calls 3 API endpoints simultaneously
    // through the CRA proxy (port 3000). After ~5 test cases the
    // proxy's HMR WebSocket exhausts Chromium's per-origin connection
    // pool, causing all 3 API calls to fail with "Network Error".
    // The page then navigates back and the form never renders.
    //
    // This is an infrastructure limitation (dev-mode CRA proxy), not
    // a code bug. With a production build or when run as the sole
    // test, the edit flow works correctly.

    const newTitle = `E2E Updated Title ${Date.now()}`;
    console.log(`Updating practice title to: ${newTitle}`);

    await findAndEditFirstPractice(page);

    // Change the title
    const titleInput = page.locator('input[id="title"]');
    await titleInput.clear();
    await titleInput.fill(newTitle);

    // Save
    await page.getByRole('button', { name: /Uložit|Upravit|Vytvořit/i }).click();

    // Verify success – expect redirect back to practice list or a success message
    try {
      await expect(page.getByText(/(Stáž upravena|Změny uloženy|Úspěch)/i).first()).toBeVisible({ timeout: 15000 });
      console.log('Edit title success message visible');
    } catch (e) {
      console.log('No explicit success message, checking for redirect...');
      await expect(page).toHaveURL(/.*\/praxe/, { timeout: 15000 });
    }
  });

  test('EP02 - can edit practice description', async ({ page }) => {
    // SKIPPED: same CRA dev server proxy limitation as EP01.

    const newDescription = `E2E Updated Description ${Date.now()}`;
    console.log(`Updating practice description to: ${newDescription}`);

    await findAndEditFirstPractice(page);

    // Change the description
    const descInput = page.getByLabel('Popis stáže');
    await descInput.clear();
    await descInput.fill(newDescription);

    // Save
    await page.getByRole('button', { name: /Uložit|Upravit|Vytvořit/i }).click();

    // Verify success
    try {
      await expect(page.getByText(/(Stáž upravena|Změny uloženy|Úspěch)/i).first()).toBeVisible({ timeout: 15000 });
      console.log('Edit description success message visible');
    } catch (e) {
      console.log('No explicit success message, checking for redirect...');
      await expect(page).toHaveURL(/.*\/praxe/, { timeout: 15000 });
    }
  });
});
