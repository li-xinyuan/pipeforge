import { chromium } from 'playwright'

const BASE = 'http://localhost:8000'
let passed = 0
let failed = 0

async function test(name: string, fn: () => Promise<void>) {
  try {
    await fn()
    passed++
    console.log(`  ✓ ${name}`)
  } catch (e) {
    failed++
    console.log(`  ✕ ${name}`)
    console.log(`    ${(e as Error).message.split('\n')[0]}`)
  }
}

async function main() {
  console.log('\nConfigForge E2E Tests\n')

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } })
  await context.addInitScript(() => localStorage.clear())

  async function newPage() {
    const page = await context.newPage()
    await page.goto(BASE, { waitUntil: 'networkidle' })
    return page
  }

  // Test 1: Home page loads
  await test('home page loads with title', async () => {
    const page = await newPage()
    const h1 = await page.locator('h1').textContent()
    if (h1 !== 'ConfigForge') throw new Error(`Expected ConfigForge, got "${h1}"`)
    await page.close()
  })

  // Test 2: Click "开始创建新配置" navigates to step 1
  await test('click start navigates to step 1', async () => {
    const page = await newPage()
    await page.click('a:has-text("开始创建新配置")')
    await page.waitForURL('**/step/1')
    const heading = page.getByRole('heading', { name: '场景信息' })
    if (!(await heading.isVisible())) throw new Error('Scene info heading not visible')
    await page.close()
  })

  // Test 3: Next button starts disabled
  await test('next button disabled with empty name', async () => {
    const page = await newPage()
    await page.goto(`${BASE}/step/1`, { waitUntil: 'networkidle' })
    const nextBtn = page.locator('button').filter({ hasText: '下一步' })
    await nextBtn.waitFor({ state: 'visible', timeout: 5000 })
    const isDisabled = await nextBtn.isDisabled()
    if (!isDisabled) throw new Error('Next button should be disabled when name is empty')
    await page.close()
  })

  // Test 4: Fill name enables next button
  await test('filling name enables next button', async () => {
    const page = await newPage()
    await page.goto(`${BASE}/step/1`, { waitUntil: 'networkidle' })
    await page.fill('#scene-name', '测试场景')
    const nextBtn = page.locator('button').filter({ hasText: '下一步' })
    const isEnabled = await nextBtn.isEnabled()
    if (!isEnabled) throw new Error('Next button should be enabled after filling name')
    await page.close()
  })

  // Test 5: Full Step 1 form fill and navigate to Step 2
  await test('step 1 form fill -> step 2', async () => {
    const page = await newPage()
    await page.goto(`${BASE}/step/1`, { waitUntil: 'networkidle' })
    await page.fill('#scene-name', '月度考勤报表')
    await page.fill('#scene-version', '1.2')
    await page.fill('#scene-description', '汇总数据生成月度统计')
    await page.click('button:has-text("下一步")')
    await page.waitForURL('**/step/2')
    const indicator = page.locator('text=数据源配置').first()
    if (!(await indicator.isVisible())) throw new Error('Step 2 indicator not visible')
    await page.close()
  })

  // Helper: add an Excel input source on step 2 (required before "下一步" is enabled)
  async function addInputSource(page: any) {
    await page.click('button:has-text("添加输入源")')
    await page.waitForTimeout(300)
    await page.click('button:has-text("Excel")')
    await page.waitForTimeout(300)
  }

  // Helper: configure output on step 3 (required before "下一步" is enabled)
  async function configureOutput(page: any) {
    await page.click('button:has-text("输出配置")')
    await page.waitForTimeout(300)
    // Click "+ 添加列" to add a column mapping
    await page.click('button:has-text("+ 添加列")')
    await page.waitForTimeout(300)
  }

  // Test 6: Back navigation step 2 -> step 1 (back is <router-link> rendered as <a>)
  await test('step 2 back to step 1', async () => {
    const page = await newPage()
    await page.goto(`${BASE}/step/1`, { waitUntil: 'networkidle' })
    await page.fill('#scene-name', '测试')
    await page.click('button:has-text("下一步")')
    await page.waitForURL('**/step/2')
    await page.click('a:has-text("上一步")')
    await page.waitForURL('**/step/1')
    const value = await page.inputValue('#scene-name')
    if (value !== '测试') throw new Error(`Expected preserved name "测试", got "${value}"`)
    await page.close()
  })

  // Test 7: Navigate to Step 3, verify tab layout
  await test('step 3 tab layout and SQL input', async () => {
    const page = await newPage()
    await page.goto(`${BASE}/step/1`, { waitUntil: 'networkidle' })
    await page.fill('#scene-name', '测试')
    await page.click('button:has-text("下一步")')
    await page.waitForURL('**/step/2')
    await addInputSource(page)
    await page.click('button:has-text("下一步")')
    await page.waitForURL('**/step/3')

    const sqlTab = page.getByText('SQL 处理').first()
    const outputTab = page.getByText('输出配置').first()
    if (!(await sqlTab.isVisible())) throw new Error('SQL tab not visible')
    if (!(await outputTab.isVisible())) throw new Error('Output tab not visible')

    await page.fill('textarea', 'SELECT * FROM person')
    await page.close()
  })

  // Test 8: Complete flow to Step 4, verify YAML preview
  await test('full flow to step 4 with YAML preview', async () => {
    const page = await newPage()
    await page.goto(`${BASE}/step/1`, { waitUntil: 'networkidle' })
    await page.fill('#scene-name', '测试场景')
    await page.click('button:has-text("下一步")')
    await page.waitForURL('**/step/2')
    await addInputSource(page)
    await page.click('button:has-text("下一步")')
    await page.waitForURL('**/step/3')
    await page.fill('textarea', 'SELECT * FROM person')
    await configureOutput(page)
    await page.click('button:has-text("下一步")')
    await page.waitForURL('**/step/4')

    const yamlBlock = page.locator('pre')
    await yamlBlock.waitFor({ state: 'visible', timeout: 5000 })
    const yaml = await yamlBlock.textContent()
    if (!yaml?.includes('scene:')) throw new Error('YAML missing scene section')
    if (!yaml?.includes('inputs:')) throw new Error('YAML missing inputs section')
    if (!yaml?.includes('测试场景')) throw new Error('YAML missing scene name')
    await page.close()
  })

  // Test 9: Finish returns to home
  await test('finish returns to home', async () => {
    const page = await newPage()
    await page.goto(`${BASE}/step/1`, { waitUntil: 'networkidle' })
    await page.fill('#scene-name', '测试')
    await page.click('button:has-text("下一步")')
    await page.waitForURL('**/step/2')
    await addInputSource(page)
    await page.click('button:has-text("下一步")')
    await page.waitForURL('**/step/3')
    await page.fill('textarea', 'SELECT 1')
    await configureOutput(page)
    await page.click('button:has-text("下一步")')
    await page.waitForURL('**/step/4')
    await page.click('a:has-text("完成")')
    await page.waitForURL(BASE + '/')
    await page.close()
  })

  await browser.close()

  console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed\n`)
  process.exit(failed > 0 ? 1 : 0)
}

main()
