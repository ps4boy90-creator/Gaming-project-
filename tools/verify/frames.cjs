/**
 * Captures gameplay frames under conditions deterministic enough to compare
 * pixel-for-pixel, and is the only place that knows how.
 *
 * Both sides of the "gameplay is unchanged" check go through here: the baseline
 * in tools/verify/baseline/ was taken with this script against the commit
 * before the cutscene work, and cutscenes.cjs takes the candidate frames with
 * it now. That matters more than it sounds. Almost everything on screen moves
 * on its own -- grain cycles, the vertical roll creeps, the lamps flicker off a
 * running PRNG, the idle animation breathes -- so two captures of the same
 * unchanged build differ in tens of thousands of pixels unless every one of
 * those clocks is pinned first. An unpinned comparison does not weakly prove
 * the claim; it proves nothing at all.
 *
 * Run standalone to (re)capture a baseline:
 *
 *   BASE=http://127.0.0.1:8001 node tools/verify/frames.cjs tools/verify/baseline
 */
const path = require('path');
const fs = require('fs');

const CHROME = process.env.CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

/** Scene, spawn point, and the camera's x. Fixed, so the frames are comparable. */
const FRAMES = [
  ['cabin_bedroom', 'wake', 180],
  ['station_lobby', 'from_gate', 200],
  ['laboratory', 'from_canteen', 420],
  ['sublevel_3', 'from_stairs', 640],
];

/** Freeze everything that moves by itself, then draw one frame. */
function pin(px) {
  const g = window.game;

  // Stop the loop first. Pinning the clocks and calling render() is not enough
  // on its own -- the loop goes on drawing frames of its own between that call
  // and the screenshot, and it is one of those that gets photographed.
  g.loop.stop();

  // Triggers draw nothing, so removing them cannot change a pixel -- but a
  // trigger authored after the baseline was taken would otherwise fire a
  // cutscene over the frame and report itself as a rendering regression.
  g.scene.entities = g.scene.entities.filter((e) => e.type !== 'trigger');
  g.dialogue.clear();

  // Lighting: the clock and the flicker noise. `time` alone is not enough --
  // the per-light jitter comes from a stateful PRNG, so two runs that rendered
  // a different number of frames before this point disagree on every lamp.
  g.lighting.time = 12.0;
  g.lighting.rng = () => 0.5;

  // Film and broadcast artefacts.
  g.postfx.settings.grain = 0;
  g.postfx.settings.broadcast = 0;
  g.postfx._rollY = 0;
  g.postfx._tear = null;

  // The player: position, facing and the phase of the idle animation.
  g.player.setPosition(px, g.player.y);
  g.player.facing = 1;
  g.player.anim.index = 0;
  g.player.anim.time = 0;

  g.camera.shakeAmount = 0;
  g.camera.shakeX = 0;
  g.camera.shakeY = 0;
  g.camera.snapTo(px, g.player.y - 40);

  g.render();
}

/** Skip the prologue narration a new game opens on. */
async function skipPrologue(page) {
  for (let i = 0; i < 20; i++) {
    if (await page.evaluate(() => window.game.state) !== 'cutscene') return;
    await page.keyboard.press('Escape');
    await page.waitForTimeout(240);
  }
}

async function captureFrames(page, outDir) {
  fs.mkdirSync(outDir, { recursive: true });
  for (const [id, spawn, x] of FRAMES) {
    await page.evaluate(() => window.game.loop.start());
    await page.evaluate(([s, sp]) => window.game.travel(s, sp, { instant: true }), [id, spawn]);
    await page.waitForTimeout(500);
    await page.evaluate(pin, x);
    await page.screenshot({ path: path.join(outDir, `${id}.png`) });
  }
  await page.evaluate(() => window.game.loop.start());
  return FRAMES.map(([id]) => id);
}

async function bootFresh(page, base) {
  await page.goto(`${base}/index.html`);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForFunction(
    () => window.game && ['playing', 'cutscene', 'error'].includes(window.game.state),
    null, { timeout: 15000 });
  await skipPrologue(page);
}

module.exports = { FRAMES, captureFrames, bootFresh, skipPrologue, CHROME };

if (require.main === module) {
  const { chromium } = require('playwright-core');
  const out = path.resolve(process.argv[2] || path.join(__dirname, 'baseline'));
  const base = process.env.BASE || 'http://127.0.0.1:8000';
  (async () => {
    const browser = await chromium.launch({ executablePath: CHROME, args: ['--no-sandbox'] });
    const page = await browser.newPage({ viewport: { width: 1152, height: 648 } });
    page.on('pageerror', (e) => console.log('PAGEERROR', e.message));
    await bootFresh(page, base);
    const ids = await captureFrames(page, out);
    const info = await page.evaluate(() => ({
      w: window.game.screen.canvas.width,
      h: window.game.screen.canvas.height,
      smoothing: window.game.screen.hostCtx.imageSmoothingEnabled,
      scale: window.game.screen.scale,
    }));
    console.log(`captured ${ids.join(', ')} from ${base} into ${out}`);
    console.log('backbuffer', JSON.stringify(info));
    await browser.close();
  })();
}
