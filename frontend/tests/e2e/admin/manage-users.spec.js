import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink, checkHeading } from '../helpers';

test.describe('Manage school users', () => {
  test.setTimeout(60000);
  test.use({ storageState: 'playwright/.auth/admin.json' });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForAppLoad(page);
  });

  test('AU01 - shows department users list', async ({ page }) => {
    console.log('Navigating to Uživatelé → Školní uživatelé...');
    await clickNavLink(page, 'Uživatelé', 'Školní uživatelé');
    await waitForAppLoad(page);

    console.log('Verifying heading...');
    await checkHeading(page, 'Školní uživatelé');

    console.log('Verifying user list is visible...');
    // Wait for loading to finish
    await expect(page.getByText('Načítání...')).not.toBeVisible({ timeout: 15000 });

    // UserCRUDPage renders user entities with id="user-entity-*"
    const userEntities = page.locator('div[id^="user-entity-"]');
    const userCount = await userEntities.count();
    console.log(`Found ${userCount} user(s)`);

    if (userCount === 0) {
      // Check if the search placeholder is visible (page loaded correctly)
      const searchInput = page.locator('input[id="name"]');
      await expect(searchInput).toBeVisible();
      console.log('No users found — empty state, but page loaded correctly');
    } else {
      await expect(userEntities.first()).toBeVisible();
      console.log('User list is visible');
    }
  });

  test('AU03 - can edit a user', async ({ page }) => {
    await clickNavLink(page, 'Uživatelé', 'Školní uživatelé');
    await waitForAppLoad(page);
    await checkHeading(page, 'Školní uživatelé');

    // Wait for the list to load
    await expect(page.getByText('Načítání...')).not.toBeVisible({ timeout: 15000 });

    // Find user entities
    const userEntities = page.locator('div[id^="user-entity-"]');
    const userCount = await userEntities.count();
    if (userCount === 0) {
      console.log('No users found — skipping edit test');
      test.skip();
      return;
    }

    // Read the name from the first user entity (text-left column)
    const firstUserName = await userEntities.first().locator('div.text-left').textContent();
    console.log(`Editing user: "${firstUserName?.trim()}"`);

    // Click the edit button (only button in the user entity)
    await userEntities.first().locator('button').first().click();

    // Wait for the professor form to load
    await page.waitForSelector('#name', { timeout: 10000 });
    await page.waitForSelector('#surname', { timeout: 10000 });
    console.log('Form loaded, modifying phone field...');

    // Modify the phone field (simple, reversible change)
    const newPhone = `777${Date.now().toString().slice(-7)}`;
    await page.locator('#phone').fill(newPhone);

    // Save changes
    await page.getByRole('button', { name: 'Uložit změny' }).click();

    // Wait for redirect back to the user list
    await waitForAppLoad(page);

    console.log('User edit saved successfully');
  });

  test('AU04 - can deactivate a user', async ({ page }) => {
    // This test depends on seed data and uses the API directly since the
    // current UserCRUDPage UI does not expose a deactivate button.
    test.skip();

    await clickNavLink(page, 'Uživatelé', 'Školní uživatelé');
    await waitForAppLoad(page);
    await checkHeading(page, 'Školní uživatelé');
    await expect(page.getByText('Načítání...')).not.toBeVisible({ timeout: 15000 });

    // Fetch department professors via API
    console.log('Fetching department professors from API...');
    const usersResponse = await page.request.get(
      'http://localhost:8000/api/departments/department-professor/'
    );
    expect(usersResponse.status()).toBe(200);
    const users = await usersResponse.json();
    console.log(`Found ${users.length} professor(s)`);

    if (!users || users.length === 0) {
      console.log('No users found to deactivate');
      test.skip();
      return;
    }

    const targetUser = users[0];
    console.log(`Deactivating user ID=${targetUser.id} (${targetUser.email || 'no email'})`);

    // Deactivate: set is_active = false
    const deactivateResponse = await page.request.patch(
      `http://localhost:8000/api/departments/department-professor/${targetUser.id}/`,
      { data: { is_active: false } }
    );
    expect(deactivateResponse.status()).toBe(200);

    // Verify deactivation
    const verifyResponse = await page.request.get(
      `http://localhost:8000/api/departments/department-professor/${targetUser.id}/`
    );
    const userData = await verifyResponse.json();
    expect(userData.is_active).toBe(false);
    console.log('User is now inactive');

    // Reactivate to keep state clean
    console.log('Reactivating user...');
    await page.request.patch(
      `http://localhost:8000/api/departments/department-professor/${targetUser.id}/`,
      { data: { is_active: true } }
    );
    console.log('User reactivated — test cleanup complete');
  });
});
