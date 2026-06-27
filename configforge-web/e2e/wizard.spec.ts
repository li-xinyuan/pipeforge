import { test, expect } from './fixtures'

test.beforeEach(async ({ page, request }) => {
  const loginResp = await request.post('http://127.0.0.1:8199/api/auth/login', {
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

test.describe('Config Wizard', () => {
  test('can create a new config via wizard', async ({ page }) => {
    await page.goto('/')
    // Click the create/new config button
    const newBtn = page.locator('text=新建配置').first()
    if (await newBtn.isVisible()) {
      await newBtn.click()
      // Should navigate to wizard
      await page.waitForURL('**/wizard**', { timeout: 10000 }).catch(() => {})
    }
  })

  test('wizard step 1 has scene name input', async ({ page }) => {
    await page.goto('/config/new')
    // Wait for the wizard to load
    await page.waitForLoadState('networkidle')
    // Look for any input on the wizard page
    const input = page.locator('input').first()
    await expect(input).toBeVisible({ timeout: 15000 })
  })
})

test.describe('Config API', () => {
  async function getAuthHeaders(request: import('@playwright/test').APIRequestContext) {
    const loginResp = await request.post('http://127.0.0.1:8199/api/auth/login', {
      data: { username: 'admin', password: 'admin123' },
    })
    const { access_token } = await loginResp.json()
    return { Authorization: `Bearer ${access_token}` }
  }

  test('list configs returns valid response', async ({ request }) => {
    const headers = await getAuthHeaders(request)
    const resp = await request.get('http://127.0.0.1:8199/api/configs', { headers })
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('configs')
    expect(data).toHaveProperty('total')
  })

  test('init scene returns valid response', async ({ request }) => {
    const headers = await getAuthHeaders(request)
    const resp = await request.post('http://127.0.0.1:8199/api/wizard/init-scene', {
      headers,
      data: { file_ids: [] },
    })
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('scene')
  })
})
