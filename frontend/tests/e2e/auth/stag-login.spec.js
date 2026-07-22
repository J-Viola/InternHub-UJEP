import { test, expect } from '@playwright/test';

test.describe('STAG login scenarios', () => {

  test('ST01 - student can log in via STAG mock ticket', async ({ page }) => {
    test.setTimeout(60000);

    console.log('Navigating to / with STAG student ticket');
    await page.goto('/?stagUserTicket=student-ticket');

    // Wait for login processing + redirect to /nabidka
    await page.waitForURL('**/nabidka', { timeout: 20000 });
    console.log('Redirected to /nabidka');

    // Verify localStorage has user data (refreshToken is in httpOnly cookie, not localStorage)
    const userStr = await page.evaluate(() => localStorage.getItem('user'));
    expect(userStr).not.toBeNull();
    const user = JSON.parse(userStr);
    expect(user.email).toBe('jan.novak@ujep.cz');
    expect(user.role).toBe('st');
    console.log('STAG student user verified in localStorage');
  });

  test('ST02 - professor can log in via STAG mock ticket', async ({ page }) => {
    test.setTimeout(60000);

    console.log('Navigating to / with STAG teacher ticket');
    await page.goto('/?stagUserTicket=teacher-ticket');

    // Wait for login processing + redirect to /nabidka
    await page.waitForURL('**/nabidka', { timeout: 20000 });
    console.log('Redirected to /nabidka');

    // Verify localStorage has user data
    const userStr = await page.evaluate(() => localStorage.getItem('user'));
    expect(userStr).not.toBeNull();
    const user = JSON.parse(userStr);
    expect(user.email).toBe('professor@ujep.cz');
    expect(user.role).toBe('vy');
    console.log('STAG professor user verified in localStorage');
  });

  test('ST03 - invalid ticket shows error', async ({ page }) => {
    test.setTimeout(60000);

    console.log('Navigating to / with invalid STAG ticket');
    await page.goto('/?stagUserTicket=INVALID_TICKET');

    // Should stay on login page (no redirect to /nabidka)
    // The app cleans STAG params from URL on error, so URL should be base /
    await expect(page).not.toHaveURL(/nabidka/, { timeout: 15000 });
    console.log('Stayed on login page, not redirected to /nabidka');

    // Verify error message is visible
    // On invalid ticket, the backend returns 401 and the frontend shows:
    // "Chyba při STAG přihlášení: Chyba při komunikaci se serverem."
    await expect(
      page.getByText(/Chyba při STAG přihlášení/i)
    ).toBeVisible({ timeout: 15000 });
    console.log('Error message displayed for invalid ticket');
  });

  test('ST04 - custom student via mock-student ticket', async ({ page }) => {
    test.setTimeout(60000);

    console.log('Navigating to / with mock-student:CUSTOM123 ticket');
    await page.goto('/?stagUserTicket=mock-student:CUSTOM123');

    // Wait for login processing + redirect to /nabidka
    await page.waitForURL('**/nabidka', { timeout: 20000 });
    console.log('Redirected to /nabidka');

    // Verify login succeeded
    const userStr = await page.evaluate(() => localStorage.getItem('user'));
    expect(userStr).not.toBeNull();
    const user = JSON.parse(userStr);
    // MockStagClient returns email "student_{osCislo.lower()}@ujep.cz"
    expect(user.email).toBe('student_custom123@ujep.cz');
    expect(user.role).toBe('st');
    console.log('Custom mock student user verified in localStorage');
  });

  test('ST05 - already logged in user visiting STAG URL', async ({ page }) => {
    test.setTimeout(60000);

    // First login normally with email/password
    console.log('Logging in with email/password first');
    await page.goto('/');

    // Switch to org/email login mode
    await page.locator('#Department').click();

    // Fill credentials
    await page.locator('input[id="email"]').fill('tsedlacek@example.org');
    await page.locator('input[id="password"]').fill('password123');

    // Click login
    await page.locator('button', { hasText: 'Přihlaste se' }).click();

    // Wait for redirect to /nabidka
    await page.waitForURL('**/nabidka', { timeout: 20000 });
    console.log('Logged in and redirected to /nabidka');

    // Now navigate to STAG URL while already authenticated
    await page.goto('/?stagUserTicket=student-ticket');

    // Should stay on /nabidka (already authenticated, LoginPage redirects back)
    await expect(page).toHaveURL(/.*\/nabidka/, { timeout: 15000 });
    console.log('Stayed on /nabidka after visiting STAG URL');

    // User should still be logged in
    const userStr = await page.evaluate(() => localStorage.getItem('user'));
    expect(userStr).not.toBeNull();
    console.log('User still logged in');
  });

});
