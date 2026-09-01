const { chromium } = require('playwright-core');
/**
 * Verifies the monochrome conversion by measuring the rendered frame.
 *
 * The failure this guards against is not "it isn't grey" -- that is trivially
 * true or false. It is *flattening*: a conversion can be perfectly monochrome
 * and still have destroyed the picture, by mapping two lights that differ in
 * hue onto the same grey. An average-contrast check will not catch that, so
 * the important test here samples the bedroom's warm lamp against its cold
 * window and insists a real brightness gap survives.
 *
 *   python3 -m http.server 8000 &
 *   node tools/verify/mono.cjs
 */
const path = require('path');
const CHROME = process.env.CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const BASE = process.env.BASE || 'http://127.0.0.1:8000';
const SHOTS = path.join(__dirname, 'shots');

const fail = [];
const check = (n, c, x = '') => {
  console.log(`${c ? 'PASS' : 'FAIL'}  ${n}${x ? '  ' + x : ''}`);
  if (!c) fail.push(n);
};

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1152, height: 648 } });
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));
  const G = (fn, a) => page.evaluate(fn, a);
  const settle = (ms = 300) => page.waitForTimeout(ms);

  await page.goto(`${BASE}/index.html`);
  await G(() => localStorage.clear());
  await page.reload();
  await page.waitForFunction(() => window.game && ['playing', 'cutscene', 'error'].includes(window.game.state),
    null, { timeout: 15000 });

  // ---- the prologue opens a new game
  check('a new game opens on the narration', await G(() => window.game.state) === 'cutscene');
  check('the prologue hands off to the cabin',
    await G(() => window.game.cutscene.def && window.game.cutscene.def.then.scene) === 'cabin_bedroom');
  await page.screenshot({ path: path.join(SHOTS, '50-prologue.png') });
  for (let i = 0; i < 12 && await G(() => window.game.state) === 'cutscene'; i++) {
    await page.keyboard.press('Escape');
    await settle(280);
  }
  check('gameplay begins in the cabin', await G(() => window.game.scene && window.game.scene.id) === 'cabin_bedroom');

  /** Read the presented canvas, i.e. after the monochrome filter. */
  const sample = async () => G(() => {
    const c = document.getElementById('game');
    const g = c.getContext('2d');
    const d = g.getImageData(0, 0, c.width, c.height).data;
    let colouredPixels = 0;
    let n = 0;
    let sum = 0;
    let sumSq = 0;
    for (let i = 0; i < d.length; i += 4 * 29) {
      if (d[i + 3] === 0) continue;
      const r = d[i]; const gg = d[i + 1]; const b = d[i + 2];
      if (Math.abs(r - gg) > 2 || Math.abs(gg - b) > 2) colouredPixels++;
      const lum = 0.299 * r + 0.587 * gg + 0.114 * b;
      sum += lum; sumSq += lum * lum; n++;
    }
    const mean = sum / n;
    return { colouredFraction: colouredPixels / n, mean, std: Math.sqrt(sumSq / n - mean * mean) };
  });

  await settle(700);
  const mono = await sample();
  check('the presented frame is monochrome', mono.colouredFraction < 0.005,
    `${(mono.colouredFraction * 100).toFixed(2)}% coloured pixels`);
  check('it has not gone flat', mono.std > 18, `std ${mono.std.toFixed(1)}`);
  check('it is not crushed to black', mono.mean > 10, `mean ${mono.mean.toFixed(1)}`);

  // ---- the specific failure: warm and cold light collapsing to one grey
  const pools = async () => G(() => {
    const c = document.getElementById('game');
    const g = c.getContext('2d');
    const at = (nx, ny) => {
      const s = window.game.screen;
      const x = Math.round(s.offsetX + nx * s.scale);
      const y = Math.round(s.offsetY + ny * s.scale);
      const d = g.getImageData(x - 6, y - 6, 12, 12).data;
      let sum = 0; let n = 0;
      for (let i = 0; i < d.length; i += 4) {
        sum += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
        n++;
      }
      return sum / n;
    };
    // Native coordinates of the bedroom's two light sources.
    return { lamp: at(38, 112), window: at(250, 74) };
  });
  const p = await pools();
  check('warm and cold light stay distinguishable', Math.abs(p.lamp - p.window) > 12,
    `lamp ${p.lamp.toFixed(1)} vs window ${p.window.toFixed(1)}`);
  await page.screenshot({ path: path.join(SHOTS, '51-bedroom-mono.png') });

  // ---- turning it off must genuinely restore colour
  await G(() => { window.game.options.values.mono = 0; window.game.options.apply(); });
  await settle(500);
  const colour = await sample();
  check('switching it off restores colour', colour.colouredFraction > 0.05,
    `${(colour.colouredFraction * 100).toFixed(1)}% coloured`);
  await page.screenshot({ path: path.join(SHOTS, '52-bedroom-colour.png') });
  await G(() => { window.game.options.values.mono = 1; window.game.options.apply(); });
  await settle(400);

  // ---- broadcast effects answer to the same tension as the radio
  const calm = await G(() => window.game.postfx.tension);
  await G(() => {
    for (const d2 of window.game.deductions.all) {
      window.game.journal.addDeduction({ id: d2.id, title: d2.title, pages: d2.note });
      if (d2.setsFlag) window.game.flags.set(d2.setsFlag);
    }
    window.game.pushTension();
  });
  await settle(300);
  const tense = await G(() => ({ fx: window.game.postfx.tension, radio: window.game.audio.radio ? window.game.audio.radio.tension : null }));
  check('the picture degrades with the story', tense.fx === 1, `${calm} -> ${tense.fx}`);
  check('picture and sound share one tension value', tense.radio === null || tense.radio === tense.fx,
    `postfx ${tense.fx} radio ${tense.radio}`);

  const tearsAt = await G(() => {
    const count = (tension) => {
      const fx = window.game.postfx;
      fx.setTension(tension);
      fx._tear = null;
      fx._tearIn = 6;
      let seen = 0;
      for (let i = 0; i < 1800; i++) {          // 30 seconds
        fx.update(1 / 60);
        if (fx._tear) seen++;
      }
      return seen;
    };
    const tense = count(1);
    const calm = count(0);
    window.game.pushTension();
    return { tense, calm };
  });
  check('signal tearing occurs at full tension', tearsAt.tense > 0,
    `${tearsAt.tense} torn frames in 30s`);
  check('and is rarer when the story is calm', tearsAt.calm < tearsAt.tense,
    `calm ${tearsAt.calm} vs tense ${tearsAt.tense}`);
  await G(() => { window.game.options.values.broadcast = 0; window.game.options.apply(); });
  check('broadcast effects can be switched off',
    await G(() => window.game.postfx.settings.broadcast) === 0);
  await G(() => { window.game.options.values.broadcast = 1; window.game.options.apply(); });

  // ---- the epilogue is reachable and fires once
  await G(() => window.game.travel('sublevel_3', 'from_stairs', { instant: true }));
  await page.waitForFunction(() => window.game.scene.id === 'sublevel_3', null, { timeout: 8000 });
  await G(() => window.game.player.setPosition(640, 186));
  await settle(600);
  check('the epilogue plays once the answer is assembled',
    await G(() => window.game.state) === 'cutscene');
  await settle(2500);
  await page.screenshot({ path: path.join(SHOTS, '53-epilogue.png') });
  await G(() => { window.game.cutscene.stop(); });
  await settle(300);
  const again = await G(() => {
    window.game.player.setPosition(400, 186);
    window.game.player.setPosition(640, 186);
    return window.game.state;
  });
  check('and cannot be replayed', again !== 'cutscene', `state ${again}`);

  check('no console errors', errors.length === 0, errors.slice(0, 3).join(' | '));
  await settle(1200);
  check('frame rate healthy', await G(() => window.game.loop.fps) >= 50,
    `${await G(() => window.game.loop.fps)} fps`);

  await browser.close();
  console.log(fail.length ? `\n${fail.length} FAILED: ${fail.join(', ')}` : '\nMonochrome holds up.');
  process.exit(fail.length ? 1 : 0);
})();
