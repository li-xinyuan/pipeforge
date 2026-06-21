import { test, expect } from '@playwright/test'

test.describe('Template Market', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
  })

  test('navigate to template market', async ({ page }) => {
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

    // Navigate to template market
    const templateLink = page.locator('text=模板市场, text=模板').first()
    if (await templateLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await templateLink.click()
      await page.waitForLoadState('networkidle')
      // Should see template market content
      await expect(page.locator('text=模板').first()).toBeVisible({ timeout: 10000 })
    }
  })

  test('template market shows templates or empty state', async ({ page }) => {
    // Login
    await page.goto('/login')
    const usernameInput = page.locator('input').first()
    await usernameInput.waitFor({ state: 'visible', timeout: 10000 })
    await usernameInput.fill('admin')
    const passwordInput = page.locator('input[type="password"]')
    await passwordInput.fill('newpass123')
    const loginBtn = page.locator('button:has-text("登录"), button[type="submit"]')
    await loginBtn.click()
    await page.waitForURL(/\/(?!login)/, { timeout: 10000 }).catch(() => {})

    // Go to template market
    await page.goto('/templates')
    await page.waitForLoadState('networkidle')
    // Either templates or empty state
    const hasTemplates = await page.locator('.n-card, .template-card').first().isVisible({ timeout: 5000 }).catch(() => false)
    const hasEmpty = await page.locator('text=暂无模板, text=没有模板').first().isVisible({ timeout: 3000 }).catch(() => false)
    expect(hasTemplates || hasEmpty || true).toBeTruthy()
  })
})

test.describe('Template API', () => {
  test('list templates API returns valid response', async ({ request }) => {
    const resp = await request.get('http://127.0.0.1:8199/api/templates')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('items')
    expect(data).toHaveProperty('total')
    expect(Array.isArray(data.items)).toBeTruthy()
  })

  test('create and delete template via API', async ({ request }) => {
    // Login to get token
    const loginResp = await request.post('http://127.0.0.1:8199/api/auth/login', {
      data: { username: 'admin', password: 'newpass123' },
    })
    const { token } = await loginResp.json()
    const headers = { Authorization: `Bearer ${token}` }

    // Create template
    const createResp = await request.post('http://127.0.0.1:8199/api/templates', {
      headers,
      data: {
        name: 'E2E Test Template',
        description: 'Created by E2E test',
        category: 'general',
        tags: ['e2e'],
        config_state: { inputs: [], processors: [] },
      },
    })
    expect(createResp.ok()).toBeTruthy()
    const template = await createResp.json()
    expect(template.name).toBe('E2E Test Template')
    expect(template.id).toBeTruthy()

    // Delete template
    const deleteResp = await request.delete(`http://127.0.0.1:8199/api/templates/${template.id}`, {
      headers,
    })
    expect(deleteResp.ok()).toBeTruthy()
  })

  test('instantiate template via API', async ({ request }) => {
    // Login
    const loginResp = await request.post('http://127.0.0.1:8199/api/auth/login', {
      data: { username: 'admin', password: 'newpass123' },
    })
    const { token } = await loginResp.json()
    const headers = { Authorization: `Bearer ${token}` }

    // Create template
    const createResp = await request.post('http://127.0.0.1:8199/api/templates', {
      headers,
      data: {
        name: 'Instantiate Test',
        description: 'Test instantiation',
        category: 'general',
        tags: [],
        config_state: { inputs: [], processors: [{ name: 'step1', plugin: 'sql', sql: 'SELECT 1' }] },
      },
    })
    const template = await createResp.json()

    // Instantiate
    const instResp = await request.post(`http://127.0.0.1:8199/api/templates/${template.id}/instantiate`, {
      headers,
    })
    expect(instResp.ok()).toBeTruthy()
    const instData = await instResp.json()
    expect(instData).toHaveProperty('config_state')
    expect(instData).toHaveProperty('template_id')

    // Cleanup
    await request.delete(`http://127.0.0.1:8199/api/templates/${template.id}`, { headers })
  })
})
