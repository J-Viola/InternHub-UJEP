import { test, expect } from '@playwright/test';

test.describe('Password reset flow', () => {

  test('PR01 (P1) - request password reset', async ({ page }) => {
    test.setTimeout(60000);

    console.log('Navigating to login page');
    await page.goto('/');

    // Switch to org mode to reveal the forgot-password link
    await page.locator('#Department').click();

    // Click the forgot-password link
    await page.getByText('Zapomněli jste heslo?').click();
    console.log('Clicked forgot password link');

    // Verify navigation to reset-password page
    await expect(page).toHaveURL(/.*\/reset-password/, { timeout: 10000 });
    console.log('Navigated to /reset-password');

    // Fill email of an existing non-STAG user (STAG users can't reset password)
    await page.locator('input[id="email"]').fill('hr@techcorp.cz');

    // Submit the request
    await page.getByRole('button', { name: 'Odeslat odkaz' }).click();
    console.log('Password reset request submitted');

    // Verify success message is displayed
    // The app shows success text in the submitted state
    await expect(
      page.getByText('Zkontrolujte svou emailovou schránku')
    ).toBeVisible({ timeout: 15000 });

    console.log('Password reset request success message visible');
  });

  test.skip('PR02 (P1) - confirm password reset with valid token', async ({ page }) => {
    // SKIPPED: This test requires a valid uid/token pair which cannot be generated
    // in an automated E2E test environment. To run manually:
    //   1. Request a password reset for a user
    //   2. Extract the uid and token from the email or logs
    //   3. Update the URL below
    //   4. Remove the .skip

    test.setTimeout(60000);

    const uid = 'VALID_UID_REQUIRED';
    const token = 'VALID_TOKEN_REQUIRED';

    console.log(`Navigating to reset-password confirm page`);
    await page.goto(`/reset-password/${uid}/${token}`);

    // Fill new password fields
    await page.locator('input[id="new_password"]').fill('NewPassword123!');
    await page.locator('input[id="new_password_confirm"]').fill('NewPassword123!');
    console.log('New password fields filled');

    // Submit the form
    await page.getByRole('button', { name: 'Změnit heslo' }).click();
    console.log('Password reset confirm submitted');

    // On success, user is redirected to / and a success message is shown
    // await expect(page).toHaveURL(/.*\//, { timeout: 15000 });
    // await expect(
    //   page.getByText('Heslo bylo úspěšně změněno')
    // ).toBeVisible({ timeout: 10000 });
  });

  test('PR04 (P2) - request reset for nonexistent email', async ({ page }) => {
    test.setTimeout(60000);

    console.log('Navigating to login page');
    await page.goto('/');

    // Switch to org mode to reveal the forgot-password link
    await page.locator('#Department').click();
    await page.getByText('Zapomněli jste heslo?').click();

    // Verify navigation to reset-password page
    await expect(page).toHaveURL(/.*\/reset-password/, { timeout: 10000 });
    console.log('Navigated to /reset-password');

    // Fill a nonexistent email
    await page.locator('input[id="email"]').fill('nonexistent-email-does-not-exist@example.com');

    // Submit the request
    await page.getByRole('button', { name: 'Odeslat odkaz' }).click();
    console.log('Password reset request submitted for nonexistent email');

    // Verify generic success message (API returns 200 for all requests
    // to prevent email enumeration)
    await expect(
      page.getByText('Zkontrolujte svou emailovou schránku')
    ).toBeVisible({ timeout: 15000 });

    console.log('Generic success message displayed (email not revealed)');
  });

});
