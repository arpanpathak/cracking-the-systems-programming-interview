// Measures every label of every figure in a real browser.
// Reports text that leaves its box or the canvas, and labels that overlap.
// Usage: node tools/check_figures.mjs [output-dir-for-png]
// Needs playwright-core (npm install playwright-core) and Google Chrome.
import { chromium } from 'playwright-core';
import { readdirSync, readFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'src', 'figures');
const shots = process.argv[2];
const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 800, height: 600 }, deviceScaleFactor: 1.5 });
let problems = 0;

for (const variant of ['', 'dark']) {
  const dir = join(root, variant);
  for (const file of readdirSync(dir).filter((name) => name.endsWith('.svg')).sort()) {
    await page.setContent(`<body style="margin:0;background:${variant ? '#161923' : '#fff'}">${readFileSync(join(dir, file), 'utf8')}</body>`);
    if (!variant) {
      const found = await page.evaluate(() => {
        const out = [];
        const texts = [...document.querySelectorAll('svg text')];
        const boxes = texts.map((node) => node.getBoundingClientRect());
        texts.forEach((node, index) => {
          const box = boxes[index];
          if (node.hasAttribute('transform')) return;
          const [low, high] = (node.dataset.fit || '6,794').split(',').map(Number);
          if (box.left < low - 1 || box.right > high + 1) {
            out.push(`overflow "${node.textContent}" ${box.left.toFixed(0)}..${box.right.toFixed(0)} room ${low}..${high}`);
          }
          for (let other = index + 1; other < texts.length; other++) {
            const b = boxes[other];
            const dx = Math.min(box.right, b.right) - Math.max(box.left, b.left);
            const dy = Math.min(box.bottom, b.bottom) - Math.max(box.top, b.top);
            if (dx > 2 && dy > 5) out.push(`overlap "${node.textContent}" / "${texts[other].textContent}"`);
          }
        });
        return out;
      });
      for (const line of found) { problems++; console.log(`${file}: ${line}`); }
    }
    if (shots) {
      mkdirSync(join(shots, variant), { recursive: true });
      const svg = await page.$('svg');
      await svg.screenshot({ path: join(shots, variant, file.replace('.svg', '.png')) });
    }
  }
}
await browser.close();
console.log(`${problems} problems`);
