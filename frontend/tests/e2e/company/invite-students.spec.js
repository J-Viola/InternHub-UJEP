import { test, expect, request } from '@playwright/test';
import { waitForAppLoad } from '../helpers';

test.describe('Invite students to practice', () => {
  test.use({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/company.json` });
  test.setTimeout(90000);

  test.beforeAll(async () => {
    const ctx = await request.newContext();
    await ctx.post(`${process.env.E2E_API_URL || 'http://localhost:8000'}/api/test/scenario/application-ready/`);
    await ctx.dispose();
  });

  // Note: The permission fix adds IsOrganizationUser to AllStudentsListView so
  // company users can now search students for invitations.
  test('CI01 - can search for a student', async ({ page }) => {
    // Navigate directly to /students (nav link text is "Studentské účty", not "Studenti")
    await page.goto('/students');
    await waitForAppLoad(page);

    // Wait for the student search page to fully load
    // Check heading to confirm we are on the right page
    await expect(page.getByRole('heading', { name: 'Studenti', exact: true })).toBeVisible({ timeout: 15000 });
    console.log('Student page loaded');

    // Search for student "Ignác" using the name input field
    const searchInput = page.locator('input[id="name"]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    await searchInput.fill('Ignác');

    // Wait for search results – the debounce or API call should complete
    await page.waitForTimeout(1500);

    // Verify the student appears in the results
    const studentCard = page.locator('div[id^="user-entity-"]').filter({ hasText: 'Ignác' }).first();
    try {
      await expect(studentCard).toBeVisible({ timeout: 15000 });
      console.log('Student Ignác found in search results');
    } catch (e) {
      console.error('Student Ignác not found! Current page content:');
      console.error(await page.innerText('body'));
      // Fallback check – maybe the student data is loaded differently
      const allCards = await page.locator('div[id^="user-entity-"]').allTextContents();
      console.log('All user entity cards found:', allCards);
      throw e;
    }
  });
});
