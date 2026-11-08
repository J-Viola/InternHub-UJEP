const { defineConfig, devices } = require('@playwright/test');
const path = require('node:path');
const authDir = path.resolve(__dirname, process.env.E2E_AUTH_DIR || 'playwright/.auth');

module.exports = defineConfig({
  globalSetup: require.resolve('./playwright.global-setup.js'),
  testDir: './tests/e2e',
  fullyParallel: false, // Run serially to avoid database locks or too much load
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Use 1 worker to ensure stability in dev environment
  reporter: 'list',
  timeout: 60000,
  expect: {
    timeout: 10000,
  },
  use: {
    // BL-07: E2E_BASE_URL umožní namířit běh na izolovaný stack (disposable DB),
    // výchozí hodnota se nemění (CI/local default zůstává localhost:3000).
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    locale: 'cs',                // Czech locale for consistent date/number formatting
    timezoneId: 'Europe/Prague',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    // Setup project for authentication
    {
      name: 'setup',
      testMatch: 'auth.setup.js',
    },
    // Firefox smoke
    {
      name: 'Firefox Smoke',
      testMatch: /smoke\/critical-paths\.spec\.js/,
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup'],
    },
    // Admin Tests
    {
      name: 'Admin Role',
      testMatch: 'admin.spec.js',
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(authDir, 'admin.json'),
      },
      dependencies: ['setup'],
    },
    // Professor Tests
    {
      name: 'Professor Role',
      testMatch: 'professor.spec.js',
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(authDir, 'professor.json'),
      },
      dependencies: ['setup'],
    },
    // Company Tests
    {
      name: 'Company Role',
      testMatch: 'company.spec.js',
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(authDir, 'company.json'),
      },
      dependencies: ['setup'],
    },
    // Student Tests
    {
      name: 'Student Role',
      testMatch: ['student.spec.js', 'profile_management.spec.js'],
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(authDir, 'student.json'),
      },
      dependencies: ['setup'],
    },
    // Cross-Role Flows (e.g. Dual Approval)
    {
      name: 'Cross-Role Flows',
      testMatch: /.*_flow\.spec\.js|search_filter\.spec\.js|scenario_.*\.spec\.js|.*-lifecycle\.spec\.js|auto-close\.spec\.js/,
      // BL-07/PBUG-04: podadresářové specy vlastní projekt "… (Extended)" —
      // bez ignore matchoval practice-lifecycle.spec.js oba projekty (2× běh).
      testIgnore: /cross-role\//,
      use: {
        ...devices['Desktop Chrome'],
      },
      dependencies: ['setup'],
    },
    // Security
    {
      name: 'Security Role Tests',
      testMatch: 'security_roles.spec.js',
      use: {
        ...devices['Desktop Chrome'],
      },
      dependencies: ['setup'],
    },
    // === NEW SUITES (subdirectory-based) ===
    // Auth Tests (login, registration, password reset)
    {
      name: 'Auth Tests',
      testMatch: /auth\/.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
      },
      dependencies: ['setup'],
    },
    // Student Extended Tests
    {
      name: 'Student Tests (Extended)',
      testMatch: /student\/.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(authDir, 'student.json'),
      },
      dependencies: ['setup'],
    },
    // Company Extended Tests
    {
      name: 'Company Tests (Extended)',
      testMatch: /company\/.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(authDir, 'company.json'),
      },
      dependencies: ['setup'],
    },
    // Professor Extended Tests
    {
      name: 'Professor Tests (Extended)',
      testMatch: /professor\/.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(authDir, 'professor.json'),
      },
      dependencies: ['setup'],
    },
    // Admin Extended Tests
    {
      name: 'Admin Tests (Extended)',
      testMatch: /admin\/.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(authDir, 'admin.json'),
      },
      dependencies: ['setup'],
    },
    // Cross-Role Flow Tests (subdirectory)
    {
      name: 'Cross-Role Flows (Extended)',
      testMatch: /cross-role\/.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
      },
      dependencies: ['setup'],
    },
    // Security Tests (subdirectory)
    {
      name: 'Security Tests (Extended)',
      testMatch: /security\/.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
      },
      dependencies: ['setup'],
    },
    // Smoke Tests
    {
      name: 'Smoke Tests',
      testMatch: /smoke\/.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
      },
      dependencies: ['setup'],
    },
  ],
});
