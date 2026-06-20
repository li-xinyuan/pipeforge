import { chromium } from '/Users/lixinyuan/code/CCTEST/configforge-web/node_modules/playwright/index.mjs';
const b = await chromium.launch({ headless: true, executablePath: '/Users/lixinyuan/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing' });
const p1 = await b.newPage({ viewport: { width: 1440, height: 900 } });
const p2 = await b.newPage({ viewport: { width: 1440, height: 900 } });

await p1.goto('http://localhost:8765/design-demo.html', { waitUntil: 'networkidle' });
await p1.waitForTimeout(1000);
await p1.evaluate(() => { document.querySelectorAll('.btn--ghost')[1].click(); });
await p1.waitForTimeout(500);
await p1.screenshot({ path: '/Users/lixinyuan/code/CCTEST/tmp-demo.png' });

await p2.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
await p2.waitForTimeout(1000);
await p2.fill('input[type="text"]', 'admin');
await p2.fill('input[type="password"]', 'admin123');
await p2.click('.login__submit');
await p2.waitForTimeout(2000);
await p2.goto('http://localhost:5173/config/new?guide=测试', { waitUntil: 'networkidle' });
await p2.waitForTimeout(2000);
await p2.screenshot({ path: '/Users/lixinyuan/code/CCTEST/tmp-actual.png' });

const actual = await p2.evaluate(() => {
  const p = document.querySelector('.guide-panel');
  return p ? { bg: window.getComputedStyle(p).background?.slice(0,60), blur: window.getComputedStyle(p).backdropFilter !== 'none', width: window.getComputedStyle(p).width } : 'NO PANEL';
});
console.log('Actual panel:', JSON.stringify(actual));
await b.close();
