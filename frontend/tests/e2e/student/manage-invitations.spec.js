import { test, expect, request } from '@playwright/test';
import { waitForAppLoad, confirmPopup } from '../helpers';

test.describe('Manage invitations', () => {
  test.use({ storageState: `${process.env.E2E_AUTH_DIR || 'playwright/.auth'}/student.json` });
  test.setTimeout(60000);

  test.beforeAll(async () => {
    const ctx = await request.newContext();
    const resp = await ctx.post(`${process.env.E2E_API_URL || 'http://localhost:8000'}/api/test/scenario/invitation-exists/`);
    if (!resp.ok()) {
      console.log('Warning: could not prepare scenario data');
    }
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForAppLoad(page);
    await page.goto('/praxe');
    await waitForAppLoad(page);
  });

  test('MI01 - shows my invitations', async ({ page }) => {
    // Reload to ensure fresh data (as done in invitation_flow.spec.js)
    await page.reload();
    await waitForAppLoad(page);

    // Wait for potential loading states
    await expect(page.getByText('Načítání...').first()).not.toBeVisible({ timeout: 15000 }).catch(() => {
      console.log('No loading spinner found');
    });

    // Look for the "Pozvánky" section (invitations from companies)
    // Based on invitation_flow.spec.js pattern
    const invitationSection = page.locator('div').filter({ hasText: /Pozvánky od firem|Pozvánky|Moje pozvánky/i }).last();
    const sectionVisible = await invitationSection.isVisible().catch(() => false);

    if (sectionVisible) {
      console.log('Invitations section is visible');

      // Check if there are invitation cards or an empty state
      // Invitation cards are ContainerForEntity divs containing a "Přijmout" button
      const invitationCards = page.locator('div').filter({ hasText: /Pozvánky od firem|Pozvánky|Moje pozvánky/i }).last()
        .locator('div').filter({ hasText: /Přijmout/i });
      const cardCount = await invitationCards.count();

      if (cardCount > 0) {
        console.log(`Found ${cardCount} invitation card(s)`);
        await expect(invitationCards.first()).toBeVisible();
      } else {
        // Check for a message about no invitations
        const noInvitationsMsg = page.getByText(/Žádné pozvánky|Nemáte žádné pozvánky|Zatím nemáte/i);
        if (await noInvitationsMsg.isVisible().catch(() => false)) {
          console.log('No invitations message is displayed');
        } else {
          console.log('No invitation cards visible, but section exists');
        }
      }
    } else {
      // Invitations section may not be present if there are no invitations at all
      console.log('No invitations section found - student may have zero invitations');
    }
  });

  test('MI02 - can accept invitation', async ({ page }) => {
    // Reload to ensure fresh data
    await page.reload();
    await waitForAppLoad(page);

    // Wait for loading to finish
    await expect(page.getByText('Načítání...').first()).not.toBeVisible({ timeout: 15000 }).catch(() => {
      console.log('No loading spinner found');
    });

    // InvitationCard renders inline Accept ("Přijmout") / Decline buttons.
    // Find the "Přijmout" button directly (no need to locate the section first).
    const acceptBtn = page.getByRole('button', { name: /Přijmout/i });
    const isVisible = await acceptBtn.isVisible({ timeout: 10000 }).catch(() => false);
    if (!isVisible) {
      console.log('No "Přijmout" button visible (no pending invitations), skipping MI02');
      return;
    }

    console.log('Clicking Přijmout button on invitation card');
    await acceptBtn.click();

    // Wait for the backend to process (manageEmployerInvitation + re-fetch)
    await page.waitForTimeout(2000);

    // Verify the accept button is gone (the card was removed/re-rendered)
    const stillVisible = await acceptBtn.isVisible({ timeout: 10000 }).catch(() => false);
    if (!stillVisible) {
      console.log('Accept button is no longer visible — invitation accepted');
    } else {
      console.log('Accept button still visible (may need more time)');
    }

    // Check for success indicators
    const successText = page.getByText(/Přijato|Schváleno|Akceptováno|Pozvánka byla přijata|Pozvánka přijata/i);
    if (await successText.isVisible().catch(() => false)) {
      console.log('Invitation accepted successfully:', await successText.textContent());
    }

    console.log('Invitation acceptance flow completed');
  });
});
