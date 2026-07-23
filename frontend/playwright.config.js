const { defineConfig, devices } = require('@playwright/test');

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
    baseURL: 'http://localhost:3000',
    locale: 'cs',                // Force Czech locale for i18n consistency
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
    // Admin Tests
    {
      name: 'Admin Role',
      testMatch: 'admin.spec.js',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['setup'],
    },
    // Professor Tests
    {
      name: 'Professor Role',
      testMatch: 'professor.spec.js',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/professor.json',
      },
      dependencies: ['setup'],
    },
    // Company Tests
    {
      name: 'Company Role',
      testMatch: 'company.spec.js',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/company.json',
      },
      dependencies: ['setup'],
    },
    // Student Tests
    {
      name: 'Student Role',
      testMatch: ['student.spec.js', 'profile_management.spec.js'],
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/student.json',
      },
      dependencies: ['setup'],
    },
    // Cross-Role Flows (e.g. Dual Approval)
    {
      name: 'Cross-Role Flows',
      testMatch: /.*_flow\.spec\.js|search_filter\.spec\.js|scenario_.*\.spec\.js|.*-lifecycle\.spec\.js|auto-close\.spec\.js/,
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
        storageState: 'playwright/.auth/student.json',
      },
      dependencies: ['setup'],
    },
    // Company Extended Tests
    {
      name: 'Company Tests (Extended)',
      testMatch: /company\/.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/company.json',
      },
      dependencies: ['setup'],
    },
    // Professor Extended Tests
    {
      name: 'Professor Tests (Extended)',
      testMatch: /professor\/.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/professor.json',
      },
      dependencies: ['setup'],
    },
    // Admin Extended Tests
    {
      name: 'Admin Tests (Extended)',
      testMatch: /admin\/.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/admin.json',
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
