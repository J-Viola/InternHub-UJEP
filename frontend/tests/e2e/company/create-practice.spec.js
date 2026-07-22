import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink, checkHeading } from '../helpers';

test.describe('Create internship offer', () => {
  test.use({ storageState: 'playwright/.auth/company.json' });
  test.setTimeout(90000);

  test('CP01 - creates a new practice successfully', async ({ page }) => {
    const uniqueId = Date.now().toString();
    const practiceTitle = `E2E Create Test ${uniqueId}`;

    console.log(`Creating practice with title: ${practiceTitle}`);

    // Navigate to app root
    await page.goto('/');
    await waitForAppLoad(page);

    // Navigate via Správa organizace → Stáže
    await clickNavLink(page, 'Správa organizace', 'Stáže');
    await checkHeading(page, 'Vytvořené stáže');

    // Click "Založit stáž"
    await page.getByText('Založit stáž').click();
    await page.waitForURL('**/vytvorit-nabidku', { timeout: 15000 });
    await waitForAppLoad(page);

    // Fill the form
    await page.getByLabel('Název').fill(practiceTitle);
    await page.getByLabel('Popis stáže').fill(`Popis stáže pro E2E test ${uniqueId}`);
    await page.getByLabel('Náplň práce').fill(`Náplň práce pro E2E test ${uniqueId}`);

    // Wait for dropdowns to be populated
    await expect(page.locator('select[id="contact_user"] option').nth(1)).toBeAttached({ timeout: 10000 });
    await expect(page.locator('select[id="subject_id"] option').nth(1)).toBeAttached({ timeout: 10000 });

    // Fill start date
    const dateInputs = page.locator('.react-datepicker__input-container input');
    await dateInputs.nth(0).fill('01.01.2027');
    await dateInputs.nth(0).press('Enter');

    // Select options
    await page.locator('select[id="coefficient"]').selectOption('1');
    await page.locator('select[id="contact_user"]').selectOption({ index: 1 });
    await page.locator('select[id="subject_id"]').selectOption({ index: 1 });
    await page.locator('select[id="available_positions"]').selectOption('2');

    // Click title field to trigger end_date calculation
    await page.getByLabel('Název').click();

    // Wait for end date to populate
    await expect(page.locator('input[id="end_date"]')).not.toHaveValue('', { timeout: 15000 });
    console.log('End date populated successfully');

    // Submit the form
    await page.getByRole('button', { name: 'Vytvořit' }).click();

    // Verify redirect to /praxe (the practices list)
    console.log('Waiting for redirect to /praxe...');
    try {
      await expect(page).toHaveURL(/.*\/praxe/, { timeout: 20000 });
      console.log('Redirect successful');
    } catch (e) {
      console.error('Redirect to /praxe failed. Current URL:', page.url());
      const bodyText = await page.innerText('body');
      console.error('Page text on failure:', bodyText);
      throw e;
    }
  });

  test('CP03 - shows validation for empty required fields', async ({ page }) => {
    // Navigate directly to create practice form
    await page.goto('/vytvorit-nabidku');
    await waitForAppLoad(page);

    // Click "Vytvořit" without filling anything
    await page.getByRole('button', { name: 'Vytvořit' }).click();

    // Verify validation errors appear – look for common validation markers
    // Option A: browser native validation (input[required] message)
    // Option B: custom error messages rendered in the DOM
    try {
      // Check if any validation error messages are visible
      const validationErrors = page.locator('.error-message, .invalid-feedback, [class*="error"], [class*="invalid"]').first();
      const hasCustomErrors = await validationErrors.isVisible().catch(() => false);

      if (hasCustomErrors) {
        await expect(validationErrors).toBeVisible();
        console.log('Custom validation errors visible');
      } else {
        // Fallback: check for HTML5 validation by confirming we are still on the form page
        // and no redirect occurred
        await expect(page).toHaveURL(/.*\/vytvorit-nabidku/, { timeout: 5000 });
        console.log('No redirect – validation prevented form submission');
      }
    } catch (e) {
      console.error('Validation test failed. Current URL:', page.url());
      const bodyText = await page.innerText('body');
      console.error('Page body:', bodyText);
      throw e;
    }
  });
});
