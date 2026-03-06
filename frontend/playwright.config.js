const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
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
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    // Setup project for authentication
    {
      name: 'setup',
      testMatch: /auth\.setup\.js/,
    },
    // Admin Tests
    {
      name: 'Admin Role',
      testMatch: /admin\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['setup'],
    },
    // Professor Tests
    {
      name: 'Professor Role',
      testMatch: /professor\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/professor.json',
      },
      dependencies: ['setup'],
    },
    // Company Tests
    {
      name: 'Company Role',
      testMatch: /company\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/company.json',
      },
      dependencies: ['setup'],
    },
    // Student Tests
    {
      name: 'Student Role',
      testMatch: /student\.spec\.js|profile_management\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/student.json',
      },
      dependencies: ['setup'],
    },
    // Cross-Role Flows (e.g. Dual Approval)
    {
      name: 'Cross-Role Flows',
      testMatch: /.*_flow\.spec\.js|search_filter\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
      },
      dependencies: ['setup'],
    },
    // Security
    {
      name: 'Security Role Tests',
      testMatch: /security_roles\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
      },
      dependencies: ['setup'],
    },
  ],
});
