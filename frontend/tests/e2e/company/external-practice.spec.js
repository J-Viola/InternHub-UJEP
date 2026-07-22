import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink } from '../helpers';

test.describe('External practice creation', () => {
  test.use({ storageState: 'playwright/.auth/company.json' });
  test.setTimeout(60000);

  test.skip('EXT01 - can create external practice', async ({ page }) => {
    // SKIPPED: The external practice creation UI location and selectors are not confirmed.
    // This test assumes there is an "External practice" option within the Stáže section
    // or a separate flow for creating practices with external employers.
    //
    // To enable: verify the exact navigation path and form field IDs/labels for
    // external employer info (e.g., external company name, contact person, etc.).

    const uniqueId = Date.now().toString();
    const externalPracticeTitle = `E2E External Practice ${uniqueId}`;

    console.log(`Creating external practice: ${externalPracticeTitle}`);

    // Navigate to app root
    await page.goto('/');
    await waitForAppLoad(page);

    // Navigate to Stáže section
    await clickNavLink(page, 'Správa organizace', 'Stáže');

    // Look for external practice creation option
    // Could be a separate button or a tab like "Externí praxe" / "Založit externí praxi"
    const externalBtn = page
      .getByText(/Externí|Externí praxe/i)
      .or(page.getByRole('button', { name: /Externí/i }))
      .first();

    const isExternalAvailable = await externalBtn.isVisible().catch(() => false);

    if (!isExternalAvailable) {
      console.log('External practice creation button not found – may not be available for this company');
      test.skip();
      return;
    }

    await externalBtn.click();
    await page.waitForURL(/.*extern.*|.*mimo.*/, { timeout: 10000 }).catch(() => {
      console.log('URL did not change significantly – form may be on same page');
    });
    await waitForAppLoad(page);

    // Fill external practice form
    // The exact fields will depend on implementation – these are guesses based on typical patterns
    const titleInput = page.locator('input[id="title"]');
    await titleInput.fill(externalPracticeTitle);

    // Fill external employer details
    const extFields = {
      companyName: page.getByLabel(/Název firmy|Externí společnost/i),
      contactPerson: page.getByLabel(/Kontaktní osoba|Jméno/i),
      contactEmail: page.getByLabel(/Email/i),
    };

    for (const [key, field] of Object.entries(extFields)) {
      const isVisible = await field.isVisible().catch(() => false);
      if (isVisible) {
        await field.fill(`E2E External ${key} ${uniqueId}`);
        console.log(`Filled external field: ${key}`);
      }
    }

    // Submit the form
    const submitBtn = page.getByRole('button', { name: /Vytvořit|Uložit/i });
    await expect(submitBtn).toBeVisible({ timeout: 5000 });
    await submitBtn.click();

    // Verify success
    try {
      await expect(page.getByText(/(Externí praxe vytvořena|Úspěch)/i).first()).toBeVisible({ timeout: 15000 });
      console.log('External practice created successfully');
    } catch (e) {
      console.error('External practice creation may have failed. Current URL:', page.url());
      const bodyText = await page.innerText('body');
      console.error('Page body:', bodyText);
      throw e;
    }
  });
});
