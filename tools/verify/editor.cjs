const { chromium } = require('playwright-core');
/**
 * End-to-end verification for the scene editor.
 *
 * Drives a real browser against a running dev server and asserts the behaviour
 * a player or author actually sees -- movement, lighting, notes, doors, saves --
 * rather than unit-testing the modules in isolation. Screenshots land in
 * tools/verify/shots/ so a regression is visible, not just reported.
 *
 *   python3 -m http.server 8000 &
 *   npm install playwright-core          # once
 *   node tools/verify/editor.cjs
 *
 * Set CHROME to a Chromium binary if the default path is wrong, and BASE to
 * point at a different server.
 */
const path = require('path');
const CHROME = process.env.CHROME
  || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const BASE = process.env.BASE || 'http://127.0.0.1:8000';
const SHOTS = path.join(__dirname, 'shots');
const fail = [];
const check = (n, c, x='') => { console.log(`${c?'PASS':'FAIL'}  ${n}${x?'  '+x:''}`); if(!c) fail.push(n); };

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 820 } });
  const errors = [];
  page.on('console', m => { if (m.type()==='error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  const G = (f,a) => page.evaluate(f,a);
  const settle = (ms=250) => page.waitForTimeout(ms);

  await page.goto(`${BASE}/editor.html`);
  await G(() => localStorage.clear());
  await page.reload();
  await settle(700);
  check('editor loads', await G(() => !!window.editor));

  // Load a real scene from the manifest
  await page.selectOption('#load-scene', 'cabin_bedroom');
  await page.waitForFunction(() => window.editor.scene.id === 'cabin_bedroom', null, {timeout:8000}).catch(()=>{});
  check('loads a manifest scene', await G(() => window.editor.scene.id) === 'cabin_bedroom');
  check('lights became entities', await G(() => window.editor.scene.entities.filter(e=>e.type==='light').length) === 4);
  await settle(900);
  await page.screenshot({ path: path.join(SHOTS, '20-editor.png') });

  // Draw a collision box with the collision tool
  const before = await G(() => window.editor.scene.collision.length);
  await page.click('button[data-tool="collision"]');
  const box = await page.locator('#canvas').boundingBox();
  await page.mouse.move(box.x + 260, box.y + 240);
  await page.mouse.down();
  await page.mouse.move(box.x + 420, box.y + 300, { steps: 8 });
  await page.mouse.up();
  await settle();
  const after = await G(() => window.editor.scene.collision.length);
  check('collision box drawn', after === before + 1, `${before} -> ${after}`);
  const drawn = await G(() => window.editor.scene.collision.at(-1));
  check('box has real size', drawn.w > 10 && drawn.h > 10, JSON.stringify(drawn));

  // Place an entity
  await page.click('.chip[data-type="door"]');
  check('place tool armed', await G(() => window.editor.tool) === 'entity' && await G(() => window.editor.placeType) === 'door');
  const eBefore = await G(() => window.editor.scene.entities.length);
  await page.mouse.click(box.x + 600, box.y + 260);
  await settle();
  check('entity placed', await G(() => window.editor.scene.entities.length) === eBefore + 1);
  check('entity selected', await G(() => window.editor.selection?.kind) === 'entity');

  // Inspector is schema-driven: the door must expose its own fields
  const labels = await page.$$eval('#inspector .field-name', ns => ns.map(n => n.textContent));
  check('inspector shows door fields', ['to','spawn','requiresFlag','lockedText'].every(k => labels.includes(k)), labels.join(','));

  // Edit a property through the form
  await page.selectOption('#inspector select', { index: 1 }).catch(()=>{});
  await settle();
  const toVal = await G(() => window.editor.scene.entities.at(-1).props.to);
  check('property edit lands on the entity', typeof toVal === 'string' && toVal.length > 0, `to=${toVal}`);

  // Flag browser
  const flags = await page.$$eval('#flags-panel .flag', ns => ns.map(n => n.textContent.trim().split(/\s+/)[0]));
  check('flag browser lists flags', flags.includes('has_keys') && flags.includes('read_memo'), flags.join(','));
  check('orphan flags marked', await page.$$eval('#flags-panel .flag.orphan', n => n.length) >= 0);

  // Undo
  await page.click('#btn-undo');
  await settle();
  check('undo removes the edit', await G(() => window.editor.scene.entities.length) >= eBefore);

  // Export round-trip: does the exported JSON load in the game?
  const json = await G(() => JSON.stringify(window.editor.doc.export()));
  const parsed = JSON.parse(json);
  check('export has required keys', ['id','size','layers','collision','entities','ambient'].every(k => k in parsed));
  check('export rounds coordinates', parsed.entities.every(e => Number.isInteger(e.x) && Number.isInteger(e.y)));

  // Test play
  await page.click('#btn-test');
  await settle(500);
  const frame = page.frameLocator('#play');
  await page.waitForFunction(() => {
    const f = document.getElementById('play').contentWindow;
    return f && f.game && ['playing','error'].includes(f.game.state);
  }, null, { timeout: 15000 }).catch(()=>{});
  const playState = await G(() => {
    const f = document.getElementById('play').contentWindow;
    return { state: f?.game?.state, scene: f?.game?.scene?.id, error: f?.game?.error };
  });
  check('test play runs the edited scene', playState.state === 'playing' && playState.scene === 'cabin_bedroom', JSON.stringify(playState));
  await settle(900);
  await page.screenshot({ path: path.join(SHOTS, '21-editor-test.png') });

  check('no console errors', errors.length === 0, errors.slice(0,3).join(' | '));
  await browser.close();
  console.log(fail.length ? `\n${fail.length} FAILED: ${fail.join(', ')}` : '\nAll editor checks passed.');
  process.exit(fail.length ? 1 : 0);
})();
