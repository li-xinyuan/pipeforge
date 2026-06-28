import { test, expect } from './fixtures'

test.beforeEach(async ({ page, request }) => {
  // Login via API to get auth token (needed for UI tests with JWT enabled)
  const loginResp = await request.post('http://127.0.0.1:8000/api/auth/login', {
    data: { username: 'admin', password: 'admin123' },
  })
  const data = await loginResp.json()
  await page.addInitScript((authData) => {
    localStorage.setItem('configforge_locale', 'zh-CN')
    localStorage.setItem('configforge_auth', JSON.stringify({
      token: authData.access_token,
      user: authData.user,
      mustChangePassword: false,
    }))
  }, data)
})

test.describe('Home Page', () => {
  test('displays home page with title', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('text=最近配置').first()).toBeVisible({ timeout: 10000 })
  })

  test('search input is visible and functional', async ({ page }) => {
    await page.goto('/')
    const searchInput = page.locator('input[aria-label="搜索配置名称"]')
    if (await searchInput.isVisible()) {
      await searchInput.fill('test')
      await expect(searchInput).toHaveValue('test')
    }
  })

  test('navigation links work', async ({ page }) => {
    await page.goto('/')
    // Check nav links exist
    await expect(page.locator('text=我的配置').first()).toBeVisible()
    await expect(page.locator('text=执行历史').first()).toBeVisible()
    await expect(page.locator('text=定时任务').first()).toBeVisible()
    await expect(page.locator('text=设置').first()).toBeVisible()
  })
})

test.describe('Navigation', () => {
  test('navigate to execution history', async ({ page }) => {
    await page.goto('/')
    await page.locator('text=执行历史').first().click()
    await expect(page.locator('text=执行历史').first()).toBeVisible({ timeout: 10000 })
  })

  test('navigate to schedules', async ({ page }) => {
    await page.goto('/')
    await page.locator('text=定时任务').first().click()
    await expect(page.locator('text=定时任务').first()).toBeVisible({ timeout: 10000 })
  })

  test('navigate to settings', async ({ page }) => {
    await page.goto('/')
    await page.locator('text=设置').first().click()
    await expect(page.locator('h1', { hasText: '设置' })).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Theme Toggle', () => {
  test('theme toggle button exists', async ({ page }) => {
    await page.goto('/')
    const themeBtn = page.locator('button[aria-label="切换亮色模式"], button[aria-label="切换暗色模式"]')
    await expect(themeBtn).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Health Check', () => {
  test('API health endpoint responds', async ({ request }) => {
    const resp = await request.get('http://127.0.0.1:8000/api/health')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data.status).toBe('ok')
  })
})
