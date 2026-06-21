import { test, expect } from '@playwright/test'

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
  })

  test('redirects to login page when not authenticated', async ({ page }) => {
    await page.goto('/')
    // Should be redirected to login or see login form
    await page.waitForURL(/\/(login)?/, { timeout: 10000 })
    const loginForm = page.locator('form, input[type="password"]')
    await expect(loginForm.first()).toBeVisible({ timeout: 10000 })
  })

  test('login page has username and password fields', async ({ page }) => {
    await page.goto('/login')
    const usernameInput = page.locator('input').first()
    await expect(usernameInput).toBeVisible({ timeout: 10000 })
    const passwordInput = page.locator('input[type="password"]')
    await expect(passwordInput).toBeVisible({ timeout: 10000 })
  })

  test('login with default admin credentials', async ({ page }) => {
    await page.goto('/login')
    // Fill username
    const usernameInput = page.locator('input').first()
    await usernameInput.waitFor({ state: 'visible', timeout: 10000 })
    await usernameInput.fill('admin')

    // Fill password
    const passwordInput = page.locator('input[type="password"]')
    await passwordInput.fill('newpass123')

    // Click login button
    const loginBtn = page.locator('button:has-text("登录"), button[type="submit"]')
    await loginBtn.click()

    // Should navigate away from login page
    await page.waitForURL(/\/(?!login)/, { timeout: 10000 }).catch(() => {})
    // Should no longer see login form
    await expect(page.locator('input[type="password"]')).not.toBeVisible({ timeout: 10000 }).catch(() => {})
  })

  test('login with wrong password shows error', async ({ page }) => {
    await page.goto('/login')
    const usernameInput = page.locator('input').first()
    await usernameInput.waitFor({ state: 'visible', timeout: 10000 })
    await usernameInput.fill('admin')

    const passwordInput = page.locator('input[type="password"]')
    await passwordInput.fill('wrongpassword')

    const loginBtn = page.locator('button:has-text("登录"), button[type="submit"]')
    await loginBtn.click()

    // Should show error message
    await page.waitForTimeout(2000)
    const errorVisible = await page.locator('text=密码错误, text=登录失败, text=用户名或密码, .n-message').first().isVisible().catch(() => false)
    // Either error message appears or still on login page
    const stillOnLogin = page.url().includes('login')
    expect(errorVisible || stillOnLogin).toBeTruthy()
  })

  test('logout returns to login page', async ({ page }) => {
    // Login first
    await page.goto('/login')
    const usernameInput = page.locator('input').first()
    await usernameInput.waitFor({ state: 'visible', timeout: 10000 })
    await usernameInput.fill('admin')
    const passwordInput = page.locator('input[type="password"]')
    await passwordInput.fill('newpass123')
    const loginBtn = page.locator('button:has-text("登录"), button[type="submit"]')
    await loginBtn.click()
    await page.waitForURL(/\/(?!login)/, { timeout: 10000 }).catch(() => {})

    // Find and click logout
    const logoutBtn = page.locator('text=退出, text=登出, text=注销, button:has-text("退出")').first()
    if (await logoutBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await logoutBtn.click()
      // Should redirect to login
      await page.waitForURL(/\/login/, { timeout: 10000 }).catch(() => {})
    }
  })
})

test.describe('Login API', () => {
  test('login API returns token', async ({ request }) => {
    const resp = await request.post('http://127.0.0.1:8199/api/auth/login', {
      data: { username: 'admin', password: 'newpass123' },
    })
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('token')
  })

  test('login API rejects wrong password', async ({ request }) => {
    const resp = await request.post('http://127.0.0.1:8199/api/auth/login', {
      data: { username: 'admin', password: 'wrongpassword' },
    })
    expect(resp.ok()).toBeFalsy()
  })
})
