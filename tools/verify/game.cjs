const { chromium } = require('playwright-core');
/**
 * End-to-end verification for the game.
 *
 * Drives a real browser against a running dev server and asserts the behaviour
 * a player or author actually sees -- movement, lighting, notes, doors, saves --
 * rather than unit-testing the modules in isolation. Screenshots land in
 * tools/verify/shots/ so a regression is visible, not just reported.
 *
 *   python3 -m http.server 8000 &
 *   npm install playwright-core          # once
 *   node tools/verify/game.cjs
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
const check = (name, cond, extra = '') => {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  ' + extra : ''}`);
  if (!cond) fail.push(name);
};

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1152, height: 648 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));

  const G = (fn, arg) => page.evaluate(fn, arg);
  const settle = (ms = 260) => page.waitForTimeout(ms);
  const at = async (x) => { await G(x => window.game.player.setPosition(x, window.game.player.y), x); await settle(160); };
  const press = async (k) => { await page.keyboard.press(k); await settle(); };

  await page.goto(`${BASE}/index.html`);
  await G(() => localStorage.clear());
  await page.reload();
  await page.waitForFunction(() => window.game && ['playing','error'].includes(window.game.state), null, { timeout: 15000 });
  check('boots into playing', await G(() => window.game.state) === 'playing', await G(() => window.game.error || ''));

  // --- rendering. Wait for a world frame: `state === 'playing'` is set at the
  // end of boot, before the first render has necessarily run.
  await settle(500);
  const variety = await G(() => {
    const c = window.game.screen.canvas.getContext('2d');
    const d = c.getImageData(0, 0, 384, 216).data;
    const seen = new Set();
    for (let i = 0; i < d.length; i += 4 * 37) seen.add((d[i] << 16) | (d[i+1] << 8) | d[i+2]);
    return seen.size;
  });
  check('scene renders in colour', variety > 200, `${variety} distinct colours sampled`);
  check('integer scale', await G(() => window.game.screen.scale) === 3, 'scale=' + await G(() => window.game.screen.scale));

  // --- walking
  const x0 = await G(() => window.game.player.x);
  await page.keyboard.down('ArrowLeft'); await settle(800); await page.keyboard.up('ArrowLeft'); await settle(200);
  const x1 = await G(() => window.game.player.x);
  check('walks left', x1 < x0 - 20, `${Math.round(x0)} -> ${Math.round(x1)}`);
  check('faces left', await G(() => window.game.player.facing) === -1);
  check('stays on floor', Math.abs(await G(() => window.game.player.y) - 204) < 1);
  await page.screenshot({ path: path.join(SHOTS, '10-bedroom.png') });

  // --- read the memo
  await at(152);
  check('memo in reach', await G(() => window.game.interaction.target?.id) === 'desk_memo');
  await press('KeyE');
  check('reader opens', await G(() => window.game.reader.open) && await G(() => window.game.state) === 'reading');
  await settle(700);
  await page.screenshot({ path: path.join(SHOTS, '11-reader.png') });
  for (let i = 0; i < 8 && await G(() => window.game.reader.open); i++) { await press('KeyE'); await settle(420); }
  check('reader closes', !(await G(() => window.game.reader.open)));
  check('memo filed in journal', await G(() => window.game.journal.notes.length) === 1);
  check('read_memo flag set', await G(() => window.game.flags.has('read_memo')));

  // --- journal overlay
  await press('Tab');
  check('journal opens', await G(() => window.game.state) === 'journal');
  await page.screenshot({ path: path.join(SHOTS, '12-journal.png') });
  await press('Escape');
  check('journal closes', await G(() => window.game.state) === 'playing');

  // --- locked door refuses
  await at(374);
  check('door in reach', await G(() => window.game.interaction.target?.id) === 'leave_cabin');
  await press('KeyE'); await settle(300);
  check('locked door refuses', await G(() => window.game.scene.id) === 'cabin_bedroom');
  check('refusal is spoken', !!(await G(() => window.game.dialogue.current?.text)));

  // --- take the keys, then the door opens
  await at(112);
  await press('KeyE'); await settle(300);
  check('keys taken', await G(() => window.game.flags.has('has_keys')));
  check('keys in inventory', await G(() => window.game.journal.items.length) === 1);
  await at(374);
  await press('KeyE');
  await page.waitForFunction(() => window.game.scene.id === 'cabin_landing', null, { timeout: 6000 }).catch(() => {});
  check('travelled to landing', await G(() => window.game.scene.id) === 'cabin_landing');
  check('spawned at named point', Math.abs(await G(() => window.game.player.x) - 72) < 4);
  await settle(600);
  await page.screenshot({ path: path.join(SHOTS, '13-landing.png') });

  // --- camera scrolls in the wide scene
  const cam0 = await G(() => window.game.camera.x);
  await at(600); await settle(500);
  const cam1 = await G(() => window.game.camera.x);
  check('camera scrolls in wide scene', cam1 > cam0 + 100, `${Math.round(cam0)} -> ${Math.round(cam1)}`);
  check('camera clamped to bounds', cam1 <= 768 - 384 + 0.5, 'cam=' + Math.round(cam1));

  // --- flicker actually varies
  const flick = await G(() => {
    const l = window.game.scene.lights(window.game.flags).find(x => x.flicker === 'dying');
    const s = new Set();
    for (let t = 0; t < 40; t++) { window.game.lighting.time = t * 0.11; s.add(Math.round(window.game.lighting.intensityOf(l) * 20)); }
    return s.size;
  });
  check('dying light flickers', flick > 2, `${flick} distinct levels`);

  // --- front door gated on the answering machine
  await at(716);
  await press('KeyE'); await settle(300);
  check('front door gated', await G(() => window.game.scene.id) === 'cabin_landing');
  await at(560);
  check('machine in reach', await G(() => window.game.interaction.target?.id) === 'answering_machine');
  await press('KeyE'); await settle(400);
  await page.screenshot({ path: path.join(SHOTS, '14-terminal.png') });
  for (let i = 0; i < 6; i++) { await press('KeyE'); await settle(350); }
  check('heard_message flag set', await G(() => window.game.flags.has('heard_message')));
  await at(716);
  await press('KeyE');
  await page.waitForFunction(() => window.game.scene.id === 'cabin_drive', null, { timeout: 6000 }).catch(() => {});
  check('travelled outside', await G(() => window.game.scene.id) === 'cabin_drive');
  await settle(700);
  await page.screenshot({ path: path.join(SHOTS, '15-drive.png') });

  // --- prop with an image renders
  check('car prop present', await G(() => window.game.scene.props(window.game.flags, false).length) === 1);

  // --- save / restore
  await at(430);
  await G(() => window.game.save());
  const saved = await G(() => JSON.parse(localStorage.getItem('veridian.save.v1')));
  check('save written', saved && saved.scene === 'cabin_drive' && saved.flags.has_keys === true);

  // --- cutscene
  await at(478); await settle(400);
  check('cutscene playing', await G(() => window.game.state) === 'cutscene');
  await settle(2600);
  await page.screenshot({ path: path.join(SHOTS, '16-cutscene.png') });
  const view0 = await G(() => ({ ...window.game.cutscene.view }));
  await settle(4000);
  const view1 = await G(() => ({ ...window.game.cutscene.view }));
  check('cutscene pans', Math.abs(view1.x - view0.x) > 20 || Math.abs(view1.w - view0.w) > 20,
        `${Math.round(view0.x)},${Math.round(view0.w)} -> ${Math.round(view1.x)},${Math.round(view1.w)}`);
  await page.screenshot({ path: path.join(SHOTS, '17-cutscene-pan.png') });
  await press('Escape'); await settle(400);
  check('cutscene ends back in play', await G(() => window.game.state) === 'playing');

  // --- reload restores
  await page.reload();
  await page.waitForFunction(() => window.game && window.game.state === 'playing', null, { timeout: 15000 });
  check('save restored on reload', await G(() => window.game.scene.id) === 'cabin_drive'
        && await G(() => window.game.flags.has('has_keys')));
  check('journal restored', await G(() => window.game.journal.notes.length) >= 1);

  check('no console errors', errors.length === 0, errors.join(' | '));
  await settle(1200);
  const fps = await G(() => window.game.loop.fps);
  check('frame rate healthy', fps >= 50, `${fps} fps`);

  await browser.close();
  console.log(fail.length ? `\n${fail.length} FAILED: ${fail.join(', ')}` : '\nAll checks passed.');
  process.exit(fail.length ? 1 : 0);
})();
