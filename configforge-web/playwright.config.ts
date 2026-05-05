import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  retries: 0,
  workers: 1,
  use: {
    baseURL: 'http://localhost:8000',
    headless: true,
  },
  webServer: {
    command: 'cd /Users/lixinyuan/code/CCTEST && PYTHONPATH=/Users/lixinyuan/code/CCTEST python3 -m uvicorn configforge.server:app --port 8000',
    url: 'http://localhost:8000/api/health',
    reuseExistingServer: true,
  },
})
