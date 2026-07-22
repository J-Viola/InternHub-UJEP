import { test, expect } from '@playwright/test';
import { waitForAppLoad, clickNavLink } from '../helpers';

test.describe('Notification flow across roles', () => {
  test.setTimeout(120000);

  test('NF01 - notification bell is visible for logged-in user', async ({ browser }) => {
    // Use student context to verify the notification bell is visible
    console.log('--- Setting up student context ---');
    const studentContext = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
    const studentPage = await studentContext.newPage();

    await studentPage.goto('/');
    await waitForAppLoad(studentPage);

    // The NotificationBell component renders a button with aria-label "Oznámení"
    // (from translations, notifications.label = "Oznámení")
    // It contains a bell icon (<i className="fa-solid fa-bell"></i>)
    console.log('Checking for notification bell...');

    // Check by aria-label
    const notificationBell = studentPage.getByRole('button', { name: 'Oznámení' });
    await expect(notificationBell).toBeVisible({ timeout: 10000 });

    // Also verify the bell icon is present inside the button
    const bellIcon = notificationBell.locator('i.fa-bell');
    await expect(bellIcon).toBeVisible({ timeout: 5000 });

    console.log('Notification bell is visible for logged-in student');

    await studentContext.close();
  });
});
