import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  retries: 0,
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: [
    {
      command: 'CONFIGFORGE_JWT_SECRET=e2e-test-secret-key-at-least-32-chars uv run python -m uvicorn configforge.server:app --host 127.0.0.1 --port 8199',
      port: 8199,
      cwd: '../',
      reuseExistingServer: true,
    },
    {
      command: 'npm run dev',
      port: 5173,
      reuseExistingServer: true,
    },
  ],
})
