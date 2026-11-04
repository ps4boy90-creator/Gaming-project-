// Visual check: boots the built game in headless Chromium and screenshots key places.
// Usage: node tests/shots.mjs [url] [outDir]
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('/usr/lib/node_modules/playwright'); }
const url = process.argv[2] ?? 'http://localhost:4173/';
const out = process.argv[3] ?? new URL('./shots/', import.meta.url).pathname;
const only = process.argv[4];

const views = [
  ['cabin', -10.4, 4, 3.2, 2.62, -0.08],
  ['lounge', -3.2, 4, 3.3, Math.PI, -0.12],
  ['galley', 2.6, 4, 2.2, 2.3, -0.1],
  ['bridge2', 8.35, 8, 0.9, -Math.PI / 2 - 0.12, -0.06],
  ['bridgePilot', 12.45, 8.22, 0.25, -Math.PI / 2 + 0.06, -0.2],
  ['bridgeSide', 8.4, 8, 2.9, -2.2, -0.1],
  ['bridgeHolo', 8.4, 8, 0.7, -0.38, -0.12],
  ['corridor2', -12.8, 4, 0, -Math.PI / 2, -0.04],
  ['dome', -4.6, 8, 2.4, 2.6, -0.28],
  ['planet', 1.0, 8, 7.4, Math.PI + 0.25, -0.5],
  ['sleepbay', 10.8, 0, -3.0, 0.98, -0.12],
  ['sleepbay2', 0.9, 0, -4.2, 0.35, -0.32],
  ['garden', 8.5, 4, 5.2, Math.PI / 2 + 0.2, -0.05],
  ['hangar2', -83.2, 0, -4.6, 0.92, 0.12],
  ['aft', 6.0, 8, 7.6, Math.PI - 0.9, -0.05],
  ['bridge', 9.0, 8, -1.6, -1.2, -0.1],
  ['lab', -13.2, 0, 2.4, -2.2, -0.15],
  ['spine', -19.5, 0, 0.8, Math.PI / 2, -0.03],
  ['vault', -25.2, 0, -9.6, Math.PI / 2, -0.1],
  ['hangar', -83.5, 0, 6.5, 1.25, 0.02],
  ['arbor', 8.8, 4, -2.2, -0.6, -0.12],
  ['gym', 2.6, 4, -2.2, -0.7, -0.1],
];

const browser = await playwright.chromium.launch({ args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const quality = process.env.Q ?? 'low';
const page = await browser.newPage({ viewport: { width: Number(process.env.W ?? 960), height: Number(process.env.H ?? 540) }, deviceScaleFactor: 1 });
page.setDefaultTimeout(120000);
await page.addInitScript((q) => localStorage.setItem('seedfall.settings.v1', JSON.stringify({ quality: q })), quality);
const errors = [];
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errors.push(`[${m.type()}] ${m.text()}`); });
page.on('pageerror', (e) => errors.push(`[pageerror] ${e.message}`));
const t0 = Date.now();
await page.goto(url);
await page.waitForFunction(() => !document.getElementById('title')?.hidden, null, { timeout: 240000 });
console.log(`title after ${((Date.now() - t0) / 1000).toFixed(1)}s`);
await page.waitForTimeout(2500);
if (!only || only.split(',').includes('title')) await page.screenshot({ path: `${out}/00-title.png` });
await page.evaluate(() => window.__seedfall.startPlay());
for (const [name, x, y, z, yaw, pitch] of views) {
  if (only && !only.split(',').includes(name)) continue;
  await page.evaluate(([x, y, z, yaw, pitch]) => window.__seedfall.teleport(x, y, z, yaw, pitch), [x, y, z, yaw, pitch]);
  await page.evaluate(() => window.__seedfall.step(3.5));
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${out}/${name}.png` });
  console.log(name, JSON.stringify(await page.evaluate(() => window.__seedfall.info())));
}
console.log(errors.slice(0, 30).join('\n') || 'no console errors');
await browser.close();
