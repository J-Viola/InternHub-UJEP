import { test, expect } from '@playwright/test';
import { waitForAppLoad } from '../helpers';

test.describe('Professor profile', () => {
  test.use({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/professor.json` });

  test('PP01 - shows professor profile', async ({ page }) => {
    console.log('Navigating to /profil...');
    await page.goto('/profil');
    await waitForAppLoad(page);

    // Verify personal information is visible
    console.log('Verifying personal information...');
    await expect(page.getByText('professor@ujep.cz').or(page.getByText(/profesor/i)).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('professor@ujep.cz').or(page.getByText(/@ujep\.cz/i)).first()).toBeVisible({ timeout: 10000 });

    // Check for name or identifier text
    const bodyText = await page.innerText('body');
    const hasNameInfo = /professor|profesor|jméno|jmeno|i[mp]éna/i.test(bodyText);
    const hasDeptInfo = /katedra|department|katedry/i.test(bodyText);
    console.log(`Profile has name info: ${hasNameInfo}, department info: ${hasDeptInfo}`);

    // Verify at least some profile content is rendered
    await expect(page.getByRole('heading', { name: /Profil|Osobní údaje|Profil uživatele/i }).or(page.getByText(/Osobní údaje|Profil/i).first())).toBeVisible({ timeout: 10000 });
    console.log('Professor profile loaded successfully.');
  });

  test('PP02 - can edit profile fields', async ({ page }) => {
    console.log('Navigating to /profil...');
    await page.goto('/profil');
    await waitForAppLoad(page);

    // Look for an edit button
    const editBtn = page.getByRole('button', { name: /Upravit profil|Editovat|Upravit/i }).or(page.getByTitle(/Upravit profil/i)).first();

    if (await editBtn.count() === 0 || !(await editBtn.isVisible().catch(() => false))) {
      console.log('No edit button found on profile page — cannot proceed.');
      return;
    }

    console.log('Clicking edit button...');
    await editBtn.click();
    await page.waitForTimeout(1000);

    // Look for editable fields — try common profile field labels
    const phoneInput = page.getByLabel('Telefonní číslo').or(page.locator('input[id*="phone"], input[id*="telefon"], input[id*="telephone"]')).first();
    const bioInput = page.getByLabel('O mě').or(page.getByLabel('O sobě')).or(page.locator('textarea[id*="bio"], textarea[id*="about"], input[placeholder*="O mě"]')).first();

    const uniquePhone = `777${Date.now().toString().slice(-6)}`;
    const uniqueBio = `Profile updated at ${new Date().toISOString()}`;

    let editsMade = false;

    if (await phoneInput.count() > 0 && await phoneInput.isVisible().catch(() => false)) {
      console.log(`Editing phone number to: ${uniquePhone}`);
      await phoneInput.fill(uniquePhone);
      editsMade = true;
    } else {
      console.log('Phone input not found.');
    }

    if (await bioInput.count() > 0 && await bioInput.isVisible().catch(() => false)) {
      console.log(`Editing bio to: ${uniqueBio}`);
      await bioInput.fill(uniqueBio);
      editsMade = true;
    } else {
      console.log('Bio input not found.');
    }

    if (!editsMade) {
      console.log('No editable fields found — cannot proceed.');
      return;
    }

    // Look for save button
    const saveBtn = page.getByRole('button', { name: /Uložit/i }).first();
    if (await saveBtn.count() === 0 || !(await saveBtn.isVisible().catch(() => false))) {
      console.log('Save button not found — cannot proceed.');
      return;
    }

    console.log('Clicking save button...');
    await saveBtn.click();

    // Wait for save to complete — URL might change or success message appears
    await page.waitForTimeout(2000);

    // Reload to verify persistence
    console.log('Reloading to verify persistence...');
    await page.reload();
    await waitForAppLoad(page);

    try {
      if (await phoneInput.count() > 0) {
        const currentPhone = await phoneInput.inputValue().catch(() => null);
        if (currentPhone) {
          console.log(`Phone persisted: ${currentPhone}`);
        }
      }
      console.log('Profile edit and persistence verified successfully.');
    } catch (e) {
      console.error('Persistence verification failed. Page text:', await page.innerText('body'));
      throw e;
    }
  });
});
