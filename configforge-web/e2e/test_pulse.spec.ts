import { test } from '@playwright/test';
test('Step 3 pulse check', async ({ page }) => {
  await page.goto('http://localhost:5173/config/new', { waitUntil: 'networkidle' });
  await page.fill('input[placeholder*="场景名称"]', 'Test');
  await page.click('button:has-text("保存并继续")');
  await page.waitForTimeout(500);
  // Step 2: skip by clicking save
  const btns2 = page.locator('button:has-text("保存并继续")');
  if (await btns2.count() > 0) await btns2.last().click();
  await page.waitForTimeout(500);
  // Step 3: check element classes
  const sqlCard = page.locator('div:has-text("SQLite 查询处理")').first();
  const classes = await sqlCard.getAttribute('class');
  console.log('Step 3 SQL card classes:', classes);
  const style = await sqlCard.evaluate(el => {
    const cs = getComputedStyle(el);
    return { animation: cs.animation, outline: cs.outline, transform: cs.transform };
  });
  console.log('Step 3 SQL card computed:', JSON.stringify(style));
  // Also check if pulse-cta is on any parent
  const parent = page.locator('div:has-text("SQLite 查询处理")').locator('..').first();
  const parentTag = await parent.evaluate(el => el.tagName);
  const parentClasses = await parent.getAttribute('class');
  console.log('Parent tag:', parentTag, 'Parent classes:', parentClasses);
});
