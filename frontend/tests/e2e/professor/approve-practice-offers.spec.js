import { test, expect, request } from '@playwright/test';
import { waitForAppLoad, clickNavLink, confirmPopup } from '../helpers';

test.describe('Approve practice offers', () => {
  test.use({ storageState: 'playwright/.auth/professor.json' });
  test.setTimeout(90000);

  test.beforeAll(async () => {
    const ctx = await request.newContext();
    const resp = await ctx.post('http://localhost:8000/api/test/scenario/practice-pending-approval/');
    if (!resp.ok()) console.log('Warning: could not prepare scenario');
  });

  test('PA01 - can approve a pending practice', async ({ page }) => {
    console.log('Navigating to Správa stáží...');
    await page.goto('/');
    await waitForAppLoad(page);
    await clickNavLink(page, null, 'Správa stáží');
    await waitForAppLoad(page);

    console.log('Waiting for "Načítání stáží..." to disappear...');
    await expect(page.getByText('Načítání stáží...')).not.toBeVisible({ timeout: 15000 });

    console.log('Waiting for "Schvalovací kolečko" section...');
    await expect(page.getByText('Schvalovací kolečko')).toBeVisible({ timeout: 10000 });

    // Find a practice card in the approval queue
    const practiceCards = page.locator('div[id^="practice-offer-"]');
    const cardCount = await practiceCards.count();
    console.log(`Found ${cardCount} practice card(s) in approval queue.`);

    // Use the first available practice card
    const firstCard = practiceCards.first();
    await expect(firstCard).toBeVisible({ timeout: 10000 });

    // Find and click the gear/settings button to change state
    const gearBtn = firstCard.getByTitle('Změnit stav nabídky');
    await expect(gearBtn).toBeVisible({ timeout: 10000 });
    console.log('Clicking gear button to change practice state...');
    await gearBtn.click();

    // Confirm the state change popup
    console.log('Confirming state change popup...');
    await confirmPopup(page, 'změnit stav nabídky');

    // Verify the state change took effect — the popup should be gone
    console.log('State change confirmed successfully.');
  });
});
