import { chromium } from '/Users/lixinyuan/code/CCTEST/configforge-web/node_modules/playwright/index.mjs';
const b = await chromium.launch({ headless: true, executablePath: '/Users/lixinyuan/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing' });

const d = await b.newPage({ viewport: { width: 1440, height: 900 } });
await d.goto('http://localhost:8765/design-demo.html', { waitUntil: 'networkidle' });
await d.waitForTimeout(1000);
await d.evaluate(() => document.querySelectorAll('.btn--ghost')[1].click());
await d.waitForTimeout(500);
await d.screenshot({ path: '/Users/lixinyuan/code/CCTEST/cmp-demo.png' });

const a = await b.newPage({ viewport: { width: 1440, height: 900 } });
await a.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
await a.waitForTimeout(1000);
await a.fill('input[type="text"]', 'admin');
await a.fill('input[type="password"]', 'admin123');
await a.click('.login__submit');
await a.waitForTimeout(2000);
await a.goto('http://localhost:5173/config/new?guide=测试', { waitUntil: 'networkidle' });
await a.waitForTimeout(2000);
await a.screenshot({ path: '/Users/lixinyuan/code/CCTEST/cmp-actual.png' });

const ai = await a.evaluate(() => {
  const panel = document.querySelector('.guide-panel');
  const progress = document.querySelector('.wizard-progress');
  const card = document.querySelector('.wizard-step-card');
  return {
    panel: panel ? { hasBg: !!window.getComputedStyle(panel).background, hasBlur: window.getComputedStyle(panel).backdropFilter!=='none', hasRadius: !!window.getComputedStyle(panel).borderRadius } : 'NONE',
    progress: progress ? { hasBlur: window.getComputedStyle(progress).backdropFilter!=='none', bg: window.getComputedStyle(progress).background?.slice(0,50) } : 'NONE',
    card: card ? { hasBlur: window.getComputedStyle(card).backdropFilter!=='none' } : 'NONE',
    hasAI: !!document.querySelector('.ai-btn'),
  };
});
console.log(JSON.stringify(ai, null, 2));
console.log('\nCompare: /Users/lixinyuan/code/CCTEST/cmp-demo.png vs /Users/lixinyuan/code/CCTEST/cmp-actual.png');
await b.close();
