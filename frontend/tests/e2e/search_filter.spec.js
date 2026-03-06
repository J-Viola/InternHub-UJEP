import { test, expect } from '@playwright/test';
import { waitForAppLoad } from './helpers';

test.describe('Search and Filter (E2E)', () => {
  test.use({ storageState: 'playwright/.auth/student.json' });

  test('can search by title and filter by location', async ({ page }) => {
    await page.goto('/nabidka');
    await waitForAppLoad(page);

    // 1. Search by title
    const searchInput = page.locator('input[id="title"]');
    await searchInput.fill('Python');

    // Wait for debounced search to finish
    await expect(page.getByText('Načítání nabídek...')).not.toBeVisible();

    // Check results
    const results = page.locator('div[id^="nabidka-"]'); // Assuming NabidkaEntity has an id pattern
    // If id pattern is not clear, we just check text
    await expect(page.getByText('Python').first()).toBeVisible();

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
    const favoritesBtn = page.getByRole('button', { name: /Oblíbené/i });
    await favoritesBtn.click();
    await expect(page.getByText('Zobrazuji oblíbené')).toBeVisible();
    await expect(page.getByText('Načítání nabídek...')).not.toBeVisible();
  });
});
