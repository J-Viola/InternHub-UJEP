import { test, expect } from '@playwright/test';
import { waitForAppLoad } from './helpers';

test.describe('Search and Filter (E2E)', () => {
  test.use({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/student.json` });

  test('can search by title and filter by location', async ({ page }) => {
    await page.goto('/nabidka');
    await waitForAppLoad(page);

    // 1. Search by title
    const searchInput = page.locator('input[id="title"]');
    await searchInput.fill('DEMO Standard');

    // Wait for debounced search to finish
    await expect(page.getByText('Načítání nabídek...')).not.toBeVisible();

    // Check results via text content (no data-testid dependency)
    await expect(page.getByText('DEMO Standard').first()).toBeVisible();

    // 2. Filter by location (dropdown)
    // First clear title to have more results
    await searchInput.fill('');
    await expect(page.getByText('Načítání nabídek...')).not.toBeVisible();

    const locationSelect = page.locator('select[id="address"]');
    if (await locationSelect.count() > 0) {
        await locationSelect.selectOption({ index: 1 }); // Select first location
        await expect(page.getByText('Načítání nabídek...')).not.toBeVisible();
    }

    // 3. Toggle Favorites
    const favoritesBtn = page.getByRole('button', { name: /Pouze oblíbené/i });
    await favoritesBtn.click();
    await expect(page.getByText('Zobrazuji oblíbené')).toBeVisible();
    await expect(page.getByText('Načítání nabídek...')).not.toBeVisible();
  });
});
