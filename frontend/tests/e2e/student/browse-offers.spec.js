import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink } from '../helpers';

test.describe('Browse internship offers', () => {
  test.use({ storageState: 'playwright/.auth/student.json' });
  test.setTimeout(60000);

  test.beforeEach(async ({ page }) => {
    await page.goto('/nabidka');
    await waitForAppLoad(page);
  });

  test('SO01 - displays list of available offers', async ({ page }) => {
    // Wait for the loading state to finish
    await expect(page.getByText('Načítání nabídek...')).not.toBeVisible({ timeout: 15000 });

    // Verify that practice cards are rendered (cards have data-testid="nabidka-entity")
    const practiceCards = page.locator('[data-testid="nabidka-entity"]');
    const cardCount = await practiceCards.count();

    console.log(`Found ${cardCount} practice cards on the page`);
    expect(cardCount).toBeGreaterThan(0);

    // Also verify that at least one card is visible to the user
    await expect(practiceCards.first()).toBeVisible();
  });

  test('SO06 - can open offer detail', async ({ page }) => {
    // Wait for offers to load
    await expect(page.getByText('Načítání nabídek...')).not.toBeVisible({ timeout: 15000 });

    // Click on the first visible practice card
    const firstCard = page.locator('[data-testid="nabidka-entity"]').first();
    await expect(firstCard).toBeVisible({ timeout: 10000 });
    await firstCard.click();

    // Verify we navigated to the detail page (/nabidka/{id})
    await expect(page).toHaveURL(/\/nabidka\/\d+/, { timeout: 10000 });
    console.log('Navigated to detail page:', page.url());

    // Verify that practice title and description are visible on the detail page
    // The detail page typically shows at least a heading with the practice title
    const detailHeading = page.locator('h1, h2, h3').first();
    await expect(detailHeading).toBeVisible({ timeout: 10000 });

    // Check that some descriptive text is visible (description or body content)
    const bodyText = page.locator('body');
    await expect(bodyText).not.toBeEmpty();
  });

  test('SO07 - shows empty state for no results', async ({ page }) => {
    // Wait for offers to load
    await expect(page.getByText('Načítání nabídek...')).not.toBeVisible({ timeout: 15000 });

    // Type a search term that should match nothing
    const searchInput = page.locator('input[id="title"]');
    await searchInput.fill('ZZZZNOTEXIST');

    // Wait for debounced search to process
    await expect(page.getByText('Načítání nabídek...')).not.toBeVisible({ timeout: 15000 });

    // Give the UI a moment to render the empty state
    await page.waitForTimeout(500);

    // Verify that either an empty-state message is shown or no results are displayed
    const emptyStateVisible = await page.getByText(/Žádné nabídky|Nenalezeny|Žádné výsledky|Nebyly nalezeny/i).isVisible().catch(() => false);

    if (emptyStateVisible) {
      console.log('Empty state message is visible');
      await expect(page.getByText(/Žádné nabídky|Nenalezeny|Žádné výsledky/i).first()).toBeVisible();
    } else {
      // Fallback: verify that no practice cards are displayed
      const practiceCards = page.locator('[data-testid="nabidka-entity"]');
      const cardCount = await practiceCards.count();
      console.log(`After empty search, found ${cardCount} practice cards`);
      expect(cardCount).toBe(0);
    }
  });
});
