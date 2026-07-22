import { test, expect } from '@playwright/test';

test.describe('System settings and health', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('AS02 - health check API responds', async ({ page }) => {
    console.log('Calling health check endpoint...');
    const response = await page.request.get('http://localhost:8000/api/health/');

    console.log(`Health check response status: ${response.status()}`);
    expect(response.status()).toBe(200);

    const body = await response.json();
    console.log('Health check body:', JSON.stringify(body));
    expect(body).toBeDefined();
  });
});
