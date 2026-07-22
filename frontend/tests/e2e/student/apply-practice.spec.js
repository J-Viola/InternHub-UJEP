import { test, expect, request } from '@playwright/test';
import { waitForAppLoad } from '../helpers';

test.describe('Apply to practice', () => {
  test.use({ storageState: 'playwright/.auth/student.json' });
  test.setTimeout(60000);

  test.beforeAll(async () => {
    const ctx = await request.newContext();
    const resp = await ctx.post('http://localhost:8000/api/test/scenario/application-ready/');
    if (!resp.ok()) {
      console.log('Warning: could not prepare scenario data');
    }
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/nabidka');
    await waitForAppLoad(page);
    // Wait for offers to finish loading
    await expect(page.getByText('Načítání nabídek...')).not.toBeVisible({ timeout: 15000 });
  });

  test('AP01 - can apply to a practice', async ({ page }) => {
    // Click on the first visible practice card
    const firstCard = page.locator('[data-testid="nabidka-entity"]').first();
    await expect(firstCard).toBeVisible({ timeout: 10000 });
    await firstCard.click();

    // Wait for detail page to load
    await expect(page).toHaveURL(/\/nabidka\/\d+/, { timeout: 10000 });
    await page.waitForTimeout(1000);
    console.log('On detail page:', page.url());

    // Look for the apply button
    const applyButton = page.getByRole('button', { name: 'Podat přihlášku' });

    // Click "Podat přihlášku"
    console.log('Clicking Podat přihlášku');
    await applyButton.click();

    // Wait for confirmation popup
    await page.waitForTimeout(500);

    // Click "Ano" to confirm the application
    const confirmBtn = page.getByRole('button', { name: 'Ano', exact: true });
    await expect(confirmBtn).toBeVisible({ timeout: 10000 });
    console.log('Clicking Ano to confirm application');
    await confirmBtn.click();

    // Wait for the backend to process the application
    await page.waitForTimeout(1500);

    // Verify the button no longer shows "Podat přihlášku" (state changed)
    await expect(page.getByRole('button', { name: 'Podat přihlášku' })).not.toBeVisible({ timeout: 10000 });
    console.log('Application successfully submitted - apply button is gone');
  });

  test('AP02 - cancels application on popup No', async ({ page }) => {
    // The 'application-ready' scenario creates an application on the practice with
    // the lowest ID. We need to find a practice WITHOUT an existing application.
    // Try cards in order until we find one with the "Podat přihlášku" button.
    const cardLocator = page.locator('[data-testid="nabidka-entity"]');
    await expect(cardLocator.first()).toBeVisible({ timeout: 10000 });
    const cardCount = await cardLocator.count();

    let currentCardIndex = 0;
    let onDetailPage = false;

    while (currentCardIndex < cardCount) {
      // If we're already on the detail page (from a previous attempt), go back
      if (onDetailPage) {
        await page.goto('/nabidka');
        await waitForAppLoad(page);
        await expect(page.getByText('Načítání nabídek...')).not.toBeVisible({ timeout: 15000 });
      }

      const card = cardLocator.nth(currentCardIndex);
      await expect(card).toBeVisible({ timeout: 10000 });
      await card.click();

      // Wait for detail page to load
      await expect(page).toHaveURL(/\/nabidka\/\d+/, { timeout: 10000 });
      await page.waitForTimeout(1000);
      console.log(`On detail page (attempt ${currentCardIndex + 1}):`, page.url());

      // Check if the apply button exists on this page
      const applyButton = page.getByRole('button', { name: 'Podat přihlášku' });
      const applyVisible = await applyButton.isVisible().catch(() => false);

      if (applyVisible) {
        console.log(`Found practice without existing application (card ${currentCardIndex + 1})`);
        break;
      }

      console.log(`Practice ${currentCardIndex + 1} already has an application, trying next...`);
      currentCardIndex++;
      onDetailPage = true;
    }

    // Ensure we found a practice with the apply button
    const applyButton = page.getByRole('button', { name: 'Podat přihlášku' });
    await expect(applyButton).toBeVisible({ timeout: 10000 });

    // Click "Podat přihlášku"
    console.log('Clicking Podat přihlášku');
    await applyButton.click();

    // Wait for confirmation popup to appear
    await page.waitForTimeout(500);

    // The popup should be visible with "Ano" and "Ne" buttons
    const popupText = page.getByText(/Podat přihlášku|opravdu/i);
    await expect(popupText.first()).toBeVisible({ timeout: 10000 });
    console.log('Confirmation popup is visible');

    // Click "Ne" to cancel (or look for cancel/close button)
    const noButton = page.getByRole('button', { name: 'Ne', exact: true });
    const noBtnVisible = await noButton.isVisible().catch(() => false);

    if (noBtnVisible) {
      console.log('Clicking Ne to cancel');
      await noButton.click();
    } else {
      // Fallback: try to close the popup via cancel/close button or Escape
      console.log('No button not found, trying close/cancel');
      const cancelBtn = page.getByRole('button', { name: /Zrušit|Storno|Close/i });
      if (await cancelBtn.isVisible().catch(() => false)) {
        await cancelBtn.click();
      } else {
        // Try pressing Escape to dismiss
        await page.keyboard.press('Escape');
      }
    }

    // Wait for popup to close
    await page.waitForTimeout(1000);

    // Verify the button still shows "Podat přihlášku" (application was not submitted)
    await expect(page.getByRole('button', { name: 'Podat přihlášku' })).toBeVisible({ timeout: 10000 });
    console.log('Cancel worked - Podat přihlášku button is still visible');
  });
});
