import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests',
  timeout: 45000,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:5173', browserName: 'chromium', launchOptions: { executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium', args: ['--no-sandbox'] }, trace: 'retain-on-failure' },
})
