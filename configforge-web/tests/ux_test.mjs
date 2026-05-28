import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';

const SCREENSHOT_DIR = '/tmp/cf_ux_test';
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

async function main() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const issues = [];

  console.log('=== Step 1: Load wizard ===');
  await page.goto('http://localhost:5173/config/new', { waitUntil: 'networkidle' });
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_initial.png') });

  const stepCards = await page.locator('.wizard-step-card').count();
  console.log(`  Step cards visible: ${stepCards}`);
  if (stepCards > 1) {
    issues.push({ step: '整体', severity: 'medium', issue: '所有步骤同时显示', detail: `页面同时显示 ${stepCards} 个步骤卡片，用户可能感到信息过载。建议分步显示，只展开当前步骤。` });
  }

  // Check locked step overlay
  const lockedCards = await page.locator('.wizard-step-card--locked').count();
  console.log(`  Locked step cards: ${lockedCards}`);
  if (lockedCards > 0) {
    // Check if locked cards still show interactive elements
    for (let i = 0; i < lockedCards; i++) {
      const lockedCard = page.locator('.wizard-step-card--locked').nth(i);
      const buttons = await lockedCard.locator('button').count();
      const inputs = await lockedCard.locator('input, textarea').count();
      if (buttons > 0 || inputs > 0) {
        issues.push({ step: '整体', severity: 'medium', issue: '锁定步骤仍显示交互元素', detail: `锁定的步骤卡片中仍有 ${buttons} 个按钮和 ${inputs} 个输入框，用户可能困惑是否可以操作。` });
      }
    }
  }

  // Check language consistency
  const bodyText = await page.locator('body').innerText();
  const pleaseInputCount = (bodyText.match(/Please Input/g) || []).length;
  if (pleaseInputCount > 0) {
    issues.push({ step: 'Step 4', severity: 'medium', issue: '输出配置使用英文占位符 "Please Input"', detail: `发现 ${pleaseInputCount} 处 "Please Input"，应替换为中文占位符。` });
  }

  // Fill step 1
  const nameInput = page.locator('input[placeholder="例如：销售报表生成"]');
  await nameInput.fill('测试Python处理器');
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_step1_filled.png') });

  const saveBtn = page.locator('button:has-text("保存并继续")').first();
  await saveBtn.click({ force: true });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_step2.png') });

  // Step 2: Add Excel input and upload file
  console.log('=== Step 2: Input source ===');
  const addInputBtn = page.locator('button:has-text("添加输入源")');
  if (await addInputBtn.count() > 0) {
    await addInputBtn.first().click({ force: true });
    await page.waitForTimeout(500);
    const excelBtn = page.locator('button:has-text("Excel")').first();
    if (await excelBtn.count() > 0) {
      await excelBtn.click({ force: true });
      await page.waitForTimeout(500);
    }
  }
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_step2_excel.png') });

  // Upload a real xlsx file
  // First create one via the API
  const createXlsxScript = `
import openpyxl
import os
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Sheet1'
ws.append(['name', 'age', 'dept'])
ws.append(['Alice', '30', 'Engineering'])
ws.append(['Bob', '25', 'Marketing'])
ws.append(['Charlie', '35', 'Engineering'])
p = '/tmp/ux_test_real.xlsx'
wb.save(p)
wb.close()
print(p)
  `;

  // Use file chooser to upload
  const xlsxPath = '/tmp/ux_test_real.xlsx';
  // Create the file first via a separate process
  const { execSync } = await import('child_process');
  try {
    execSync(`python3 -c "
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Sheet1'
ws.append(['name', 'age', 'dept'])
ws.append(['Alice', '30', 'Engineering'])
ws.append(['Bob', '25', 'Marketing'])
wb.save('${xlsxPath}')
wb.close()
"`, { stdio: 'pipe' });
  } catch (e) {
    console.log('  Failed to create test xlsx, skipping upload');
  }

  if (fs.existsSync(xlsxPath)) {
    const fileInput = page.locator('input[type="file"]').first();
    if (await fileInput.count() > 0) {
      await fileInput.setInputFiles(xlsxPath);
      await page.waitForTimeout(2000);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_step2_uploaded.png') });
    }
  }

  // Complete step 2
  const saveBtn2 = page.locator('.wizard-step-card:nth-child(3) button:has-text("保存并继续")').first();
  if (await saveBtn2.count() > 0 && await saveBtn2.isEnabled()) {
    await saveBtn2.click({ force: true });
    await page.waitForTimeout(1000);
  }
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_step3.png') });

  // Step 3: Check processor type selector
  console.log('=== Step 3: Processor ===');
  const step3Card = page.locator('.wizard-step-card').nth(2);
  const isStep3Locked = await step3Card.evaluate(el => el.classList.contains('wizard-step-card--locked'));
  console.log(`  Step 3 locked: ${isStep3Locked}`);

  // Check SQL/Python selector
  const sqlNCard = page.locator('.n-card:has-text("SQL")');
  const pythonNCard = page.locator('.n-card:has-text("Python")');
  const hasSqlOption = await sqlNCard.count() > 0;
  const hasPythonOption = await pythonNCard.count() > 0;
  console.log(`  SQL option: ${hasSqlOption}, Python option: ${hasPythonOption}`);

  if (!isStep3Locked && hasPythonOption) {
    await pythonNCard.first().click({ force: true });
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_step3_python.png') });

    // Check Python textarea
    const pyTextarea = page.locator('textarea[placeholder*="def process(ctx)"]');
    const hasPyTextarea = await pyTextarea.count() > 0;
    console.log(`  Python textarea: ${hasPyTextarea}`);
    if (!hasPyTextarea) {
      issues.push({ step: 'Step 3', severity: 'high', issue: 'Python 脚本输入框不存在', detail: '选择 Python 处理后未出现脚本输入框。' });
    }

    // Check AI generate button
    const aiGenBtn = page.locator('button:has-text("AI 生成")');
    const hasAiGenBtn = await aiGenBtn.count() > 0;
    if (hasAiGenBtn) {
      issues.push({ step: 'Step 3', severity: 'low', issue: 'Python 区域仍有"AI 生成"按钮', detail: '根据设计，Python 处理器不应有 AI 生成按钮。' });
    }

    // Fill Python script
    if (hasPyTextarea) {
      await pyTextarea.fill('def process(ctx):\n    conn = ctx.db.connection\n    conn.execute("CREATE TABLE result AS SELECT 1 as value")');
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08_step3_python_filled.png') });
    }

    // Check output table auto-fill
    const outputTableInput = page.locator('input[placeholder="输出表名"]');
    const hasOutputTable = await outputTableInput.count() > 0;
    console.log(`  Output table input: ${hasOutputTable}`);

    // Check preview button
    const previewBtn = page.locator('button:has-text("预览结果")');
    const hasPreviewBtn = await previewBtn.count() > 0;
    console.log(`  Preview button: ${hasPreviewBtn}`);
  }

  // Step 4
  console.log('=== Step 4: Output config ===');
  const step4Card = page.locator('.wizard-step-card').nth(3);
  await step4Card.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '09_step4.png') });

  // Step 5
  console.log('=== Step 5: Preview & Export ===');
  const step5Card = page.locator('.wizard-step-card').nth(4);
  await step5Card.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '10_step5.png') });

  // AI panel
  console.log('=== AI Panel ===');
  const aiToggle = page.locator('.wizard__toggle-switch input[type="checkbox"]');
  if (await aiToggle.count() > 0) {
    await aiToggle.click({ force: true });
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11_ai_panel.png') });
  }

  // Check AI quick actions
  const orchestrateBtn = page.locator('button:has-text("AI 编排步骤链")');
  const hasOrchestrate = await orchestrateBtn.count() > 0;
  console.log(`  AI orchestrate button: ${hasOrchestrate}`);

  // Mobile viewport
  console.log('=== Mobile viewport ===');
  await page.setViewportSize({ width: 375, height: 812 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '12_mobile.png') });

  // Check mobile nav hidden
  const mobileNavLinks = page.locator('.wizard__nav-link');
  const mobileNavVisible = await mobileNavLinks.count();
  if (mobileNavVisible > 0) {
    const anyVisible = await mobileNavLinks.first().isVisible().catch(() => false);
    if (anyVisible) {
      issues.push({ step: '移动端', severity: 'medium', issue: '移动端导航链接仍可见', detail: '在小屏幕下，导航链接应该隐藏。' });
    }
  }

  // Check mobile FAB
  const fabBtn = page.locator('.wizard__ai-fab');
  const hasFab = await fabBtn.count() > 0 && await fabBtn.isVisible().catch(() => false);
  console.log(`  Mobile FAB visible: ${hasFab}`);

  // Dark mode
  console.log('=== Dark mode ===');
  await page.setViewportSize({ width: 1440, height: 900 });
  const themeBtn = page.locator('button:has-text("🌙")');
  if (await themeBtn.count() > 0) {
    await themeBtn.click({ force: true });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '13_dark_mode.png') });
  }

  // Print results
  console.log('\n========================================');
  console.log('UX Issues Found');
  console.log('========================================');
  for (const issue of issues) {
    console.log(`[${issue.severity.toUpperCase()}] ${issue.step}: ${issue.issue}`);
    console.log(`  → ${issue.detail}`);
  }
  if (issues.length === 0) {
    console.log('No UX issues found during automated scan.');
  }
  console.log(`\nScreenshots saved to: ${SCREENSHOT_DIR}`);

  await browser.close();
}

main().catch(e => { console.error(e); process.exit(1); });
