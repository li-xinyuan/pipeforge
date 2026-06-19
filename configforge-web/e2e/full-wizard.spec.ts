import { test, expect } from '@playwright/test'

// Helpers for Naive UI: NInput wrapper puts id on a div, not the <input>
// Use the .n-input__input-el class to target the real input inside
async function fillNInput(page: import('@playwright/test').Page, id: string, value: string) {
  const input = page.locator(`#${id} .n-input__input-el, #${id} input, input[id="${id}"]`).first()
  await input.waitFor({ state: 'visible', timeout: 5000 })
  await input.fill(value)
}

async function clickNext(page: import('@playwright/test').Page) {
  const btn = page.locator('button:has-text("下一步")')
  await btn.click()
}

test.describe('Full Wizard Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
  })

  test('home page loads with title', async ({ page }) => {
    await page.goto('/')
    const h1 = page.locator('h1')
    await expect(h1).toHaveText('ConfigForge')
  })

  test('click start navigates to step 1', async ({ page }) => {
    await page.locator('button:has-text("开始创建新配置")').click()
    await page.waitForURL('**/step/1')
    await expect(page.getByText('场景信息').first()).toBeVisible()
  })

  test('next button disabled with empty name', async ({ page }) => {
    await page.goto('/step/1')
    const nextBtn = page.locator('button').filter({ hasText: '下一步' })
    await nextBtn.waitFor({ state: 'visible', timeout: 5000 })
    await expect(nextBtn).toBeDisabled()
  })

  test('filling name enables next button', async ({ page }) => {
    await page.goto('/step/1')
    await fillNInput(page, 'scene-name', '测试场景')
    const nextBtn = page.locator('button').filter({ hasText: '下一步' })
    await expect(nextBtn).toBeEnabled()
  })

  test('step 1 form fill -> step 2', async ({ page }) => {
    await page.goto('/step/1')
    await fillNInput(page, 'scene-name', '月度考勤报表')
    await fillNInput(page, 'scene-version', '1.2')
    await fillNInput(page, 'scene-description', '汇总数据生成月度统计')
    await clickNext(page)
    await page.waitForURL('**/step/2')
    await expect(page.locator('text=数据源配置').first()).toBeVisible()
  })

  test('step 2 back to step 1', async ({ page }) => {
    await page.goto('/step/1')
    await fillNInput(page, 'scene-name', '测试')
    await clickNext(page)
    await page.waitForURL('**/step/2')
    await page.locator('button:has-text("上一步")').click()
    await page.waitForURL('**/step/1')
    const input = page.locator('#scene-name .n-input__input-el').first()
    await expect(input).toHaveValue('测试')
  })

  test('step 3 SQL input visible', async ({ page }) => {
    await page.goto('/step/1')
    await fillNInput(page, 'scene-name', '测试')
    await clickNext(page)
    await page.waitForURL('**/step/2')
    // Add input source
    await page.locator('button:has-text("添加输入源")').click()
    await page.waitForTimeout(500)
    await page.locator('.n-card:has-text("Excel")').first().click()
    await page.waitForTimeout(500)
    await clickNext(page)
    await page.waitForURL('**/step/3')
    await expect(page.locator('text=数据转换/处理').first()).toBeVisible()
  })

  test('full flow to step 5 with YAML preview', async ({ page }) => {
    await page.goto('/step/1')
    await fillNInput(page, 'scene-name', '测试场景')
    await clickNext(page)
    await page.waitForURL('**/step/2')
    await page.locator('button:has-text("添加输入源")').click()
    await page.waitForTimeout(500)
    await page.locator('.n-card:has-text("Excel")').first().click()
    await page.waitForTimeout(500)
    await clickNext(page)
    await page.waitForURL('**/step/3')
    await page.locator('textarea').first().fill('SELECT * FROM person')
    await clickNext(page)
    await page.waitForURL('**/step/4')
    await page.locator('button:has-text("+ 添加列")').first().click()
    await page.waitForTimeout(300)
    await clickNext(page)
    await page.waitForURL('**/step/5')
    const yamlBlock = page.locator('pre')
    await yamlBlock.waitFor({ state: 'visible', timeout: 5000 })
    const yaml = await yamlBlock.textContent()
    expect(yaml).toContain('scene:')
    expect(yaml).toContain('inputs:')
    expect(yaml).toContain('测试场景')
  })

  test('finish returns to home', async ({ page }) => {
    await page.goto('/step/1')
    await fillNInput(page, 'scene-name', '测试')
    await clickNext(page)
    await page.waitForURL('**/step/2')
    await page.locator('button:has-text("添加输入源")').click()
    await page.waitForTimeout(500)
    await page.locator('.n-card:has-text("Excel")').first().click()
    await page.waitForTimeout(500)
    await clickNext(page)
    await page.waitForURL('**/step/3')
    await page.locator('textarea').first().fill('SELECT 1')
    await clickNext(page)
    await page.waitForURL('**/step/4')
    await page.locator('button:has-text("+ 添加列")').first().click()
    await page.waitForTimeout(300)
    await clickNext(page)
    await page.waitForURL('**/step/5')
    await page.locator('button:has-text("完成")').click()
    await page.waitForURL('**/')
  })
})
