import { test as base, expect } from '@playwright/test'

/**
 * Extended Playwright test fixture that forces zh-CN locale before each test.
 *
 * The i18n system detects browser language via navigator.language, which
 * defaults to en-US in headless Chromium. This fixture sets localStorage
 * to zh-CN so the UI renders in Chinese, matching e2e test assertions.
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.addInitScript(() => {
      try {
        localStorage.setItem('configforge_locale', 'zh-CN')
      } catch {
        // Ignore storage errors
      }
    })
    await use(page)
  },
})

export { expect }
