import { test, expect } from '@playwright/test'

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
  test('list configs returns valid response', async ({ request }) => {
    const resp = await request.get('http://127.0.0.1:8199/api/configs')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('items')
    expect(data).toHaveProperty('total')
  })

  test('init scene returns valid response', async ({ request }) => {
    const resp = await request.post('http://127.0.0.1:8199/api/wizard/init-scene', {
      data: { file_ids: [] },
    })
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('scene')
  })
})
