// @ts-check
const { defineConfig, devices } = require('@playwright/test');

const PORT = process.env.E2E_PORT || '5055';
const BASE_URL = `http://localhost:${PORT}`;

/**
 * Playwright config for the blockchain simulator E2E tests.
 *
 * The webServer block boots the real Flask + Socket.IO app on a dedicated port
 * (5055, separate from any dev instance) so the browser exercises the genuine
 * WebSocket mining round-trip. Flask + Socket.IO can take a few seconds to come
 * up, hence the generous timeout.
 */
module.exports = defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  timeout: 60 * 1000,
  expect: { timeout: 15 * 1000 },
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'venv/bin/python app.py',
    url: BASE_URL,
    env: { PORT },
    reuseExistingServer: !process.env.CI,
    timeout: 60 * 1000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
