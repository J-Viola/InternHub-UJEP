import { expect } from '@playwright/test';

export async function waitForAppLoad(page) {
  // Listen for console messages to catch API errors
  page.on('console', msg => {
    if (msg.type() === 'error' || msg.type() === 'warning') {
      console.log(`PAGE ${msg.type().toUpperCase()}: ${msg.text()}`);
    }
  });

  try {
    // Wait for the loading screen to disappear
    await expect(page.getByText('Načítání aplikace...')).not.toBeVisible({ timeout: 20000 });

    // Wait for Nav to show we are logged in (Odhlásit se should be visible)
    // This confirms that user object was correctly loaded from localStorage
    await expect(page.getByRole('link', { name: 'Odhlásit se' })).toBeVisible({ timeout: 15000 });
  } catch (e) {
    console.error('App load failed or user not logged in! Current URL:', page.url());
    console.log('--- BODY HTML START ---');
    console.log(await page.innerHTML('body'));
    console.log('--- BODY HTML END ---');
    throw e;
  }
}

export async function clickNavLink(page, menuText, linkText) {
  if (menuText) {
    // It's a submenu
    const menuButton = page.getByRole('button', { name: menuText });
    await menuButton.hover();
    // Sometimes hover is not enough for submenus in SPAs, might need a click or small delay
    await page.waitForTimeout(500);
    await page.getByRole('link', { name: linkText }).click();
  } else {
    // Normal link
    await page.getByRole('link', { name: linkText }).click();
  }
}

export async function checkHeading(page, headingText) {
  await expect(page.getByRole('heading', { name: headingText, exact: false }).or(page.getByText(headingText))).toBeVisible();
}

export async function confirmPopup(page, headingText) {
  console.log(`Waiting for popup containing text: ${headingText}`);

  // Give it a tiny bit of time for animation
  await page.waitForTimeout(500);

  // 1. Wait for the popup area to be visible
  await expect(page.getByText(headingText, { exact: false }).first()).toBeVisible({ timeout: 15000 });

  // 2. Click the confirm button. Prefer the ID but fallback to text if needed.
  const confirmBtn = page.locator('#popup-confirm-button').or(page.getByRole('button', { name: /Schválit|Ano|Potvrdit/i }));
  await expect(confirmBtn.first()).toBeVisible({ timeout: 10000 });

  console.log('Clicking confirm button');
  await confirmBtn.click();

  // Wait a bit for the backend to process and frontend to react
  await page.waitForTimeout(1000);

  // 3. Wait for the heading text to disappear
  await expect(page.getByText(headingText, { exact: false }).first()).not.toBeVisible({ timeout: 15000 });
  }
