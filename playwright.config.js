// @ts-check
import { defineConfig, devices } from '@playwright/test';

const BASE_URL = process.env.SITE_URL || 'http://127.0.0.1:19191';

export default defineConfig({
  testDir: './tests/playwright',
  timeout: 30_000,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: BASE_URL,
    headless: true,
    // Capture console + network for every test
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Start Hugo dev server before tests, stop after
  webServer: {
    command: `cd hugo/site && hugo server --bind 127.0.0.1 --port 19191 --baseURL ${BASE_URL}/ --disableFastRender --quiet`,
    url: BASE_URL,
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
