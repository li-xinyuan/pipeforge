import { test, expect } from '@playwright/test'

const BASE = 'http://localhost:8000'

test.describe('ConfigForge 4-step wizard', () => {
  test('complete full wizard flow', async ({ page }) => {
    // Home page
    await page.goto(BASE)
    await expect(page.locator('h1')).toHaveText('ConfigForge')

    // Click "开始创建新配置"
    await page.click('text=开始创建新配置')
    await expect(page).toHaveURL(/\/step\/1/)

    // Step 1: Scene info
    await expect(page.locator('text=场景信息')).toBeVisible()

    // Fill form fields by their labels
    await page.getByLabel('场景名称').fill('月度考勤报表')
    await page.getByLabel('版本').fill('1.2')
    await page.getByLabel('场景描述').fill('汇总人员明细和考勤数据生成月度统计')

    // Click next
    await page.click('text=下一步')
    await expect(page).toHaveURL(/\/step\/2/)

    // Step 2: Input sources
    await expect(page.locator('text=数据源配置')).toBeVisible()

    // Click "+ 添加输入源" to reveal type selector
    await page.click('text=添加输入源')

    // Click Excel type card
    await page.locator('.type-selector-grid >> text=Excel').first().click()

    // Fill input source card
    await page.locator('input[placeholder="输入源名称"]').first().fill('人员明细')
    await page.locator('input[placeholder="表名"]').first().fill('person')
    await page.locator('input[placeholder="参数键"]').first().fill('person_file')
    await page.locator('input[placeholder="Sheet 名称"]').first().fill('人员列表')

    // Click next
    await page.click('text=下一步')
    await expect(page).toHaveURL(/\/step\/3/)

    // Step 3: SQL editor + Output config
    await expect(page.locator('text=SQL 处理')).toBeVisible()

    // Fill SQL
    const sqlTextarea = page.locator('textarea')
    await sqlTextarea.fill(`CREATE TABLE monthly_report AS
    SELECT p.工号, p.姓名, p.部门, a.出勤天数, a.加班小时
    FROM person p
    JOIN attendance a ON p.工号 = a.工号`)

    // Add output table
    await page.click('text=添加表名')
    // Handle prompt dialog
    page.on('dialog', dialog => dialog.accept('monthly_report'))
    await page.click('text=添加表名')

    // Switch to output config tab
    await page.click('text=输出配置')
    await expect(page.locator('text=输出配置')).toBeVisible()

    // Fill output config
    await page.locator('input[placeholder*="模板"]').first().fill('templates/report_template.xlsx')
    await page.locator('input[placeholder*="Sheet"]').first().fill('月度报表')
    await page.locator('input[placeholder*="文件名"]').first().fill('report_{{date:%Y%m%d}}.xlsx')

    // Click next
    await page.click('text=下一步')
    await expect(page).toHaveURL(/\/step\/4/)

    // Step 4: YAML preview
    await expect(page.locator('text=pipeline.yaml')).toBeVisible()

    // Verify YAML content
    const yamlBlock = page.locator('pre')
    await expect(yamlBlock).toContainText('scene:')
    await expect(yamlBlock).toContainText('月度考勤报表')
    await expect(yamlBlock).toContainText('inputs:')
    await expect(yamlBlock).toContainText('processors:')
    await expect(yamlBlock).toContainText('output:')
    await expect(yamlBlock).toContainText('person')
    await expect(yamlBlock).toContainText('monthly_report')
    await expect(yamlBlock).toContainText('output_tables')

    // Test copy button
    await page.click('text=复制')

    // Test refresh button
    await page.click('text=刷新预览')

    // Click finish
    await page.click('text=完成')
    await expect(page).toHaveURL('/')
  })

  test('step indicator shows correct progress', async ({ page }) => {
    await page.goto(`${BASE}/step/1`)

    // Verify all 4 step labels present
    const indicator = page.locator('text=场景信息').first()
    await expect(indicator).toBeVisible()

    // Fill scene name and go to step 2
    await page.getByLabel('场景名称').fill('测试')
    await page.click('text=下一步')
    await expect(page).toHaveURL(/\/step\/2/)

    // Go back
    await page.click('text=上一步')
    await expect(page).toHaveURL(/\/step\/1/)
  })

  test('validation prevents proceeding with empty scene name', async ({ page }) => {
    await page.goto(`${BASE}/step/1`)

    // Next button should be disabled when name is empty
    const nextBtn = page.locator('button:has-text("下一步")')
    await expect(nextBtn).toBeDisabled()

    // Fill name and button should enable
    await page.getByLabel('场景名称').fill('测试场景')
    await expect(nextBtn).toBeEnabled()
  })
})
