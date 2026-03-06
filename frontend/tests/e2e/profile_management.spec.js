import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink } from './helpers';
import path from 'path';
import fs from 'fs';

test.describe('Student Profile Management (E2E)', () => {
  test.use({ storageState: 'playwright/.auth/student.json' });

  test('can edit student profile, add skills, and upload CV', async ({ page }) => {
    await page.goto('/');
    await waitForAppLoad(page);
    await clickNavLink(page, null, 'Profil');
    await waitForAppLoad(page);

    // Enter edit mode
    await page.getByRole('button', { name: 'Upravit profil' }).click();
    await expect(page).toHaveURL(/.*edit=true/);

    const uniqueBio = `I am a student researcher ${Date.now()}`;
    const uniqueSkill = `Skill ${Date.now()}`;

    // 2. Edit basic fields
    await page.getByLabel('Telefonní číslo').fill('777888999');
    await page.getByLabel('O mě').fill(uniqueBio);

    // 3. Add a skill
    // Check if we need to click "Přidat dovednost" or if an empty row exists
    const skillInputs = page.locator('input[placeholder^="Dovednost"]');
    const skillCount = await skillInputs.count();

    if (skillCount < 5) {
        await page.getByRole('button', { name: 'Přidat dovednost' }).click();
        const newSkillInputs = page.locator('input[placeholder^="Dovednost"]');
        await newSkillInputs.last().fill(uniqueSkill);
    } else {
        await skillInputs.first().fill(uniqueSkill);
    }

    // 4. Upload CV
    // Create a dummy pdf file if it doesn't exist
    const filePath = path.join(__dirname, 'test-cv.pdf');
    fs.writeFileSync(filePath, 'dummy pdf content');

    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.getByText('Nahrát CV/Životopis (PDF)').click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);

    // 5. Submit form
    await page.getByRole('button', { name: 'Uložit' }).click();

    // Wait for a success message or for the URL to change back (it usually removes edit=true)
    console.log('Waiting for save to complete...');
    await expect(page).not.toHaveURL(/.*edit=true/, { timeout: 15000 });

    // 6. Verify persistence
    await page.reload();
    await waitForAppLoad(page);

    try {
        await expect(page.getByText('777888999')).toBeVisible();
        await expect(page.getByText(uniqueBio)).toBeVisible();

        // Verify the skill is present
        await expect(page.getByText(uniqueSkill)).toBeVisible();
    } catch (e) {
        console.error('Persistence verification failed! Current page content:', await page.innerText('body'));
        throw e;
    }

    // Cleanup dummy file
    fs.unlinkSync(filePath);
  });
});
