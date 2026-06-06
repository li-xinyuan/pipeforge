import { test, expect } from '@playwright/test';

test('Step 4 auto-opens file picker when Excel selected', async ({ page }) => {
  let step4ChooserOpened = false;

  page.on('filechooser', async (fileChooser) => {
    step4ChooserOpened = true;
    console.log('[EVENT] File chooser dialog opened');
    await fileChooser.setFiles([]);
  });

  await page.goto('http://localhost:5173/config/new', { waitUntil: 'networkidle' });

  // Step 1
  await page.fill('input[placeholder*="场景名称"]', 'Auto Open Test');
  await page.click('button:has-text("保存并继续")');

  // Step 2 — add Excel input, wait for file chooser
  await page.waitForSelector('text=Excel');
  await page.click('text=Excel >> nth=0');
  await page.waitForTimeout(1500);

  // Step 2 file chooser should have opened. Upload a dummy file to close it.
  // Then click save to proceed
  console.log('Trying to proceed past Step 2...');
  
  // Skip to Step 4 by directly clicking step indicator or save buttons
  // Actually let's just test: navigate to Step 4 by clicking buttons
  // Click Step 2's "保存并继续"
  const step2next = page.locator('button:has-text("保存并继续")').last();
  if (await step2next.isVisible().catch(() => false)) {
    await step2next.click();
  }
  await page.waitForTimeout(500);

  // Step 3 — add a SQL processor  
  const step3next = page.locator('button:has-text("保存并继续")').last();
  if (await step3next.isVisible().catch(() => false)) {
    // Try clicking SQL
    const sqlCard = page.locator('text=SQL').first();
    if (await sqlCard.isVisible().catch(() => false)) {
      await sqlCard.click();
      await page.waitForTimeout(1000);
    }
    await step3next.click();
    await page.waitForTimeout(500);
  }

  // Step 4 — click Excel
  const step4next = page.locator('button:has-text("保存并继续")').last();
  if (await step4next.isVisible().catch(() => false)) {
    const excelCard = page.locator('text=Excel').first();
    if (await excelCard.isVisible().catch(() => false)) {
      step4ChooserOpened = false;
      console.log('Clicking Excel in Step 4...');
      await excelCard.click();
      await page.waitForTimeout(2000);
    }
  }

  console.log(`Step 4 file chooser opened: ${step4ChooserOpened}`);
  expect(step4ChooserOpened).toBe(true);
});
