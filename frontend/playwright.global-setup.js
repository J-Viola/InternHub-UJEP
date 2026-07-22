/**
 * Global setup for Playwright E2E tests.
 *
 * Resets the database to a known seed state before running any tests.
 * This ensures each test run starts from a clean, reproducible state.
 *
 * Requires the Docker stack to be running (`make up`).
 */
const { request } = require('@playwright/test');

async function globalSetup() {
  const BACKEND_URL = process.env.E2E_API_URL || 'http://localhost:8000';

  console.log(`[globalSetup] Resetting database via ${BACKEND_URL}/api/test/reset-db/ ...`);

  try {
    const apiContext = await request.newContext({ baseURL: BACKEND_URL });
    const response = await apiContext.post('/api/test/reset-db/');
    const body = await response.json();

    if (!response.ok()) {
      throw new Error(`Reset failed (${response.status()}): ${JSON.stringify(body)}`);
    }

    console.log(`[globalSetup] Database reset complete:`, body);
  } catch (err) {
    console.error(`[globalSetup] FATAL: Could not reset database.`, err.message);
    console.error(`[globalSetup] Make sure the Docker stack is running: make up`);
    process.exit(1);
  }
}

module.exports = globalSetup;
