import { test, expect } from './fixtures'
import type { Page } from '@playwright/test'

// Helpers for Naive UI: NInput renders <input class="n-input__input-el">
// Use placeholder-based selection since wizard inputs have no id
async function fillByPlaceholder(page: Page, placeholder: string, value: string) {
  const input = page.locator(`input[placeholder="${placeholder}"], textarea[placeholder="${placeholder}"]`).first()
  await input.waitFor({ state: 'visible', timeout: 5000 })
  await input.fill(value)
}

async function clickNext(page: Page) {
  const btn = page.locator('button:has-text("下一步")')
  await btn.click()
}

/** Add a CSV input source and upload a test file so step 2 validation passes */
async function addCsvInput(page: Page) {
  // Click CSV card in the input source selector grid
  await page.locator('div.cursor-pointer:has-text("CSV")').first().click()
  await page.waitForTimeout(500)
  // Upload a test CSV file via the hidden file input (NUpload creates one)
  const fileInput = page.locator('input[type="file"]').first()
  await fileInput.setInputFiles({
    name: 'test.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from('name,age\nAlice,30\nBob,25\n'),
  })
  // Wait for upload to complete — the file tag with the filename appears
  await expect(page.locator('.n-tag').filter({ hasText: 'test.csv' })).toBeVisible({ timeout: 10000 })
}

test.describe('Full Wizard Flow', () => {
  test.beforeEach(async ({ page, request }) => {
    // Login via API to get auth token
    const loginResp = await request.post('http://127.0.0.1:8000/api/auth/login', {
      data: { username: 'admin', password: 'admin123' },
    })
    const data = await loginResp.json()

    // Set auth state via addInitScript (runs before every navigation)
    await page.addInitScript((authData) => {
      localStorage.setItem('configforge_locale', 'zh-CN')
      localStorage.setItem('configforge_auth', JSON.stringify({
        token: authData.access_token,
        user: authData.user,
        mustChangePassword: false,
      }))
    }, data)
  })

  test('home page loads with title', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('text=最近配置').first()).toBeVisible({ timeout: 10000 })
  })

  test('click start navigates to step 1', async ({ page }) => {
    await page.goto('/')
    await page.locator('button:has-text("新建配置")').first().click()
    await page.waitForURL('**/config/new', { timeout: 10000 })
    await expect(page.getByText('场景信息').first()).toBeVisible()
  })

  test('next button disabled with empty name', async ({ page }) => {
    await page.goto('/config/new')
    const nextBtn = page.locator('button').filter({ hasText: '下一步' })
    await nextBtn.waitFor({ state: 'visible', timeout: 5000 })
    await expect(nextBtn).toBeDisabled()
  })

  test('filling name enables next button', async ({ page }) => {
    await page.goto('/config/new')
    await fillByPlaceholder(page, '例如：销售报表生成', '测试场景')
    const nextBtn = page.locator('button').filter({ hasText: '下一步' })
    await expect(nextBtn).toBeEnabled()
  })

  test('step 1 form fill -> step 2', async ({ page }) => {
    await page.goto('/config/new')
    await fillByPlaceholder(page, '例如：销售报表生成', '月度考勤报表')
    await fillByPlaceholder(page, '描述这个配置管道的用途...', '汇总数据生成月度统计')
    await clickNext(page)
    await page.waitForURL('**/step/2', { timeout: 10000 }).catch(() => {})
    await expect(page.locator('text=输入源').first()).toBeVisible({ timeout: 10000 })
  })

  test('step 2 back to step 1', async ({ page }) => {
    await page.goto('/config/new')
    await fillByPlaceholder(page, '例如：销售报表生成', '测试')
    await clickNext(page)
    await page.waitForURL('**/step/2', { timeout: 10000 }).catch(() => {})
    await page.locator('button:has-text("上一步")').click()
    const input = page.locator('input[placeholder="例如：销售报表生成"]').first()
    await expect(input).toHaveValue('测试')
  })

  test('step 3 SQL input visible', async ({ page }) => {
    await page.goto('/config/new')
    await fillByPlaceholder(page, '例如：销售报表生成', '测试')
    await clickNext(page)
    await page.waitForURL('**/step/2', { timeout: 10000 }).catch(() => {})
    await addCsvInput(page)
    await clickNext(page)
    await page.waitForURL('**/step/3', { timeout: 10000 }).catch(() => {})
    await expect(page.locator('text=处理步骤').first()).toBeVisible({ timeout: 10000 })
  })

  test('full flow to step 5 with YAML preview', async ({ page }) => {
    test.setTimeout(60000)
    await page.goto('/config/new')
    await fillByPlaceholder(page, '例如：销售报表生成', '测试场景')
    await clickNext(page)
    await page.waitForURL('**/step/2', { timeout: 10000 }).catch(() => {})
    await addCsvInput(page)
    await clickNext(page)
    await page.waitForURL('**/step/3', { timeout: 10000 }).catch(() => {})
    // Step 3 shows a SQL/Python selector first — click SQL to add a processor
    await page.locator('div.cursor-pointer:has-text("SQL")').first().click()
    await page.waitForTimeout(1000)
    // SQL is auto-filled to SELECT * FROM "test" by pickProcessor()
    await clickNext(page)
    await page.waitForURL('**/step/4', { timeout: 10000 }).catch(() => {})
    // Step 4: select Excel output type
    await page.locator('div.cursor-pointer:has-text("Excel")').first().click()
    await page.waitForTimeout(500)
    // Select source table from NSelect dropdown
    await page.locator('.n-select').first().click()
    await page.waitForTimeout(300)
    await page.locator('.n-base-select-option').first().click()
    await page.waitForTimeout(300)
    // Add a column mapping
    await page.locator('button:has-text("+ 添加列映射")').first().click()
    await page.waitForTimeout(300)
    await clickNext(page)
    await page.waitForURL('**/step/5', { timeout: 10000 }).catch(() => {})
    // YamlPreview uses CodeEditor (CodeMirror) which renders content inside .cm-content
    // Wait for the YAML to be generated by the API (yamlText ref starts empty)
    const yamlBlock = page.locator('.cm-content').first()
    await yamlBlock.waitFor({ state: 'visible', timeout: 10000 })
    // Wait until content actually contains "scene:" (API call completed)
    await expect.poll(async () => (await yamlBlock.textContent()) || '', { timeout: 15000 }).toContain('scene:')
    const yaml = await yamlBlock.textContent()
    expect(yaml).toContain('scene:')
    expect(yaml).toContain('inputs:')
    expect(yaml).toContain('测试场景')
  })

  test('finish returns to home', async ({ page }) => {
    test.setTimeout(60000)
    await page.goto('/config/new')
    await fillByPlaceholder(page, '例如：销售报表生成', '测试')
    await clickNext(page)
    await page.waitForURL('**/step/2', { timeout: 10000 }).catch(() => {})
    await addCsvInput(page)
    await clickNext(page)
    await page.waitForURL('**/step/3', { timeout: 10000 }).catch(() => {})
    // Step 3 shows a SQL/Python selector first — click SQL to add a processor
    await page.locator('div.cursor-pointer:has-text("SQL")').first().click()
    await page.waitForTimeout(1000)
    await clickNext(page)
    await page.waitForURL('**/step/4', { timeout: 10000 }).catch(() => {})
    // Step 4: select Excel output type
    await page.locator('div.cursor-pointer:has-text("Excel")').first().click()
    await page.waitForTimeout(500)
    // Select source table from NSelect dropdown
    await page.locator('.n-select').first().click()
    await page.waitForTimeout(300)
    await page.locator('.n-base-select-option').first().click()
    await page.waitForTimeout(300)
    // Add a column mapping
    await page.locator('button:has-text("+ 添加列映射")').first().click()
    await page.waitForTimeout(300)
    await clickNext(page)
    await page.waitForURL('**/step/5', { timeout: 10000 }).catch(() => {})
    await page.locator('button:has-text("保存配置")').click()
    // Click "去首页" in the confirmation dialog
    await page.locator('button:has-text("去首页")').click()
    await page.waitForURL('**/', { timeout: 10000 })
  })
})
