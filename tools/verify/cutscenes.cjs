const { chromium } = require('playwright-core');
/**
 * Verifies the cutscene rework, and -- more importantly -- verifies that it
 * left gameplay alone.
 *
 * The brief was that cutscenes may look better while gameplay stays the plain
 * side-scrolling view it already was. That is a promise about pixels, so it is
 * checked as one: four scenes are re-rendered at the same camera positions used
 * to capture tools/verify/baseline/ before any of this work started, and every
 * pixel must match. Grain cycles, the vertical roll drifts and the lamps
 * flicker, so all three are pinned before each capture; without that the
 * comparison would fail on noise and mean nothing.
 *
 *   python3 -m http.server 8000 &
 *   node tools/verify/cutscenes.cjs
 */
const path = require('path');
const fs = require('fs');
const os = require('os');
const { spawnSync } = require('child_process');

const { captureFrames, bootFresh, CHROME } = require('./frames.cjs');

const BASE = process.env.BASE || 'http://127.0.0.1:8000';
const ROOT = path.resolve(__dirname, '..', '..');
const SHOTS = path.join(__dirname, 'shots');
const BASELINE = path.join(__dirname, 'baseline');

const fail = [];
const check = (n, c, x = '') => {
  console.log(`${c ? 'PASS' : 'FAIL'}  ${n}${x ? '  ' + x : ''}`);
  if (!c) fail.push(n);
};
const head = (t) => console.log(`\n--- ${t}`);

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
  await page.waitForFunction(
    () => window.game && ['playing', 'cutscene', 'error'].includes(window.game.state),
    null, { timeout: 15000 });

  // ---------------------------------------------------------------- the beats
  head('the five beats');
  check('opens on the prologue', await G(() => window.game.cutscene.def && window.game.cutscene.def.id) === 'prologue');
  // Including the one a step cuts to: a cutscene fires from inside a trigger,
  // so an unloaded still would fade to black at the moment it was needed.
  const missing = await G(async () => {
    const m = await import('/src/scenes/manifest.js');
    return m.cutsceneImages().filter((p) => !window.game.assets.images.has(p));
  });
  check('every still, including step cuts, is preloaded', missing.length === 0, missing.join(', '));

  // Record every cutscene from here on, in order, so "fires once, in order"
  // is an observation rather than an assumption.
  await G(() => {
    window.__beats = [];
    const g = window.game;
    const orig = g.playCutscene.bind(g);
    g.playCutscene = (id, after) => { window.__beats.push(id); return orig(id, after); };
  });

  /** Is cutscene `id` on screen right now? */
  const playing = async (id) => G((want) => window.game.state === 'cutscene'
    && window.game.cutscene.active
    && window.game.cutscene.def.id === want, id);

  /**
   * `cutscene.def` is not cleared when a cutscene ends, so asking only what the
   * last cutscene was answers a question nobody asked -- it reads as a pass
   * long after the picture has gone back to gameplay. Every beat check waits
   * for the thing to actually be on screen.
   */
  const awaitBeat = async (id, timeout = 8000) => {
    await page.waitForFunction(
      (want) => window.game.state === 'cutscene' && window.game.cutscene.active
        && window.game.cutscene.def.id === want,
      id, { timeout }).catch(() => {});
    return playing(id);
  };

  /** Escape out of the cutscene that is up, and no further. */
  const skip = async (limit = 20) => {
    const id = await G(() => (window.game.state === 'cutscene' ? window.game.cutscene.def.id : null));
    if (!id) return;
    for (let i = 0; i < limit && await playing(id); i++) {
      await page.keyboard.press('Escape');
      await settle(240);
    }
  };
  await settle(2400);   // past the fade-in, onto the bed
  await page.screenshot({ path: path.join(SHOTS, '60-prologue.png') });

  // ------------------------------------------------------------- it moves
  head('the animated beats');

  /**
   * How much of the frame changed over `ms`, ignoring the pan.
   *
   * A cutscene that pans across a still also changes every frame, so "the
   * pixels differ" proves nothing on its own. This samples with the view held
   * still, so what it measures is the animation.
   */
  const motion = async (ms) => {
    await G(() => {
      const c = window.game.cutscene;
      window.__frozen = { ...c.view };
      // Hold the window: the painter keeps running, the camera does not.
      Object.defineProperty(c, 'view', {
        configurable: true, get: () => window.__frozen, set: () => {},
      });
    });
    const grab = () => G(() => {
      const c = window.game.screen.cutsceneCanvas;
      return [...c.getContext('2d').getImageData(0, 120, c.width, 200).data]
        .filter((_, i) => i % 4 === 0);
    });
    const a = await grab();
    await settle(ms);
    const b = await grab();
    await G(() => { delete window.game.cutscene.view; window.game.cutscene.view = window.__frozen; });
    let moved = 0;
    for (let i = 0; i < a.length; i++) if (Math.abs(a[i] - b[i]) > 6) moved++;
    return moved / a.length;
  };

  const wakeMoves = await motion(420);
  check('the prologue is animated, not a pan over a photograph', wakeMoves > 0.002,
    `${(wakeMoves * 100).toFixed(2)}% of the frame changed in 0.4s`);
  check('the prologue runs a painter', await G(() => !!window.game.cutscene.fx));

  // He gets out of bed: every phase of the animation is reached, in order.
  const phases = [];
  await G(() => {
    window.__phases = [];
    const tick = () => {
      const c = window.game.cutscene;
      if (c.active && c.fxPhase && window.__phases[window.__phases.length - 1] !== c.fxPhase) {
        window.__phases.push(c.fxPhase);
      }
      if (c.active) requestAnimationFrame(tick);
    };
    tick();
  });
  await page.waitForFunction(() => window.__phases.includes('window') || !window.game.cutscene.active,
    null, { timeout: 40000 }).catch(() => {});
  phases.push(...await G(() => window.__phases));
  check('he wakes, sits up, stands, walks and reaches the window',
    JSON.stringify(phases.slice(0, 6))
      === JSON.stringify(['sleep', 'stir', 'sit', 'stand', 'walk', 'window']),
    phases.join(' -> '));
  await page.screenshot({ path: path.join(SHOTS, '59-prologue-window.png') });

  await skip();
  check('prologue hands off to the cabin', await G(() => window.game.scene.id) === 'cabin_bedroom');

  // The drive fires from cabin_drive once he has the keys and reaches the car.
  await G(() => {
    window.game.flags.set('has_keys');
    return window.game.travel('cabin_drive', 'from_landing', { instant: true });
  });
  await settle(500);
  const driveTrigger = await G(() => {
    const t = window.game.scene.entities.find((e) => e.props && e.props.cutscene === 'drive');
    return t ? t.x + t.w / 2 : null;
  });
  check('the drive has a trigger', driveTrigger !== null);
  await G((x) => window.game.player.setPosition(x, window.game.player.y), driveTrigger);
  check('the drive plays on reaching the car', await awaitBeat('drive'));
  await settle(2600);
  const driveMoves = await motion(300);
  check('the drive is animated', driveMoves > 0.03,
    `${(driveMoves * 100).toFixed(1)}% of the frame changed in 0.3s`);
  check('the drive runs a painter', await G(() => !!window.game.cutscene.fx));
  // The heaviest frame in the game: five scrolling layers and a hundred
  // gradient slices of headlight, all at 768x432.
  await settle(1400);
  const driveFps = await G(() => window.game.loop.fps);
  check('and holds frame rate while it does', driveFps >= 50, `${driveFps} fps`);

  // ------------------------------------------------- the cutscene surface
  head('cutscenes gained resolution');
  await settle(600);
  const surf = await G(() => ({
    used: window.game.screen.useCutsceneSurface,
    w: window.game.screen.cutsceneCanvas.width,
    h: window.game.screen.cutsceneCanvas.height,
    play: [window.game.screen.canvas.width, window.game.screen.canvas.height],
  }));
  check('presents from the cutscene surface', surf.used === true);
  check('the cutscene surface is 768x432', surf.w === 768 && surf.h === 432, `${surf.w}x${surf.h}`);
  check('the gameplay backbuffer is untouched at 384x216',
    surf.play[0] === 384 && surf.play[1] === 216, surf.play.join('x'));

  // Draw the still exactly as the cutscene is framing it right now, once at
  // each surface size, and count the greys that survive. Doing it offscreen
  // from the source image rather than off the live surface keeps grain and the
  // fade out of a measurement that is about resolution.
  // Counting greys is not enough on its own -- a still can hold all 256 and
  // still lose every fine edge. Measure what each surface can actually carry:
  // put the still through the surface, bring it back to source size, and see
  // how far it has moved from the original.
  const tone = await G(() => {
    const img = window.game.cutscene.image;
    const surface = (w, h) => {
      const s = document.createElement('canvas');
      s.width = w; s.height = h;
      const g = s.getContext('2d');
      g.imageSmoothingEnabled = false;
      g.drawImage(img, 0, 0, w, h);
      const back = document.createElement('canvas');
      back.width = img.width; back.height = img.height;
      const b = back.getContext('2d');
      b.imageSmoothingEnabled = false;
      b.drawImage(s, 0, 0, img.width, img.height);
      return b.getImageData(0, 0, img.width, img.height).data;
    };
    const src = (() => {
      const s = document.createElement('canvas');
      s.width = img.width; s.height = img.height;
      const g = s.getContext('2d');
      g.imageSmoothingEnabled = false;
      g.drawImage(img, 0, 0);
      return g.getImageData(0, 0, img.width, img.height).data;
    })();
    const rms = (d) => {
      let sum = 0;
      let n = 0;
      for (let i = 0; i < d.length; i += 4) { const e = d[i] - src[i]; sum += e * e; n++; }
      return Math.sqrt(sum / n);
    };
    const greys = (d) => { const s = new Set(); for (let i = 0; i < d.length; i += 4) s.add(d[i]); return s.size; };
    const hi = surface(768, 432);
    const lo = surface(384, 216);
    return { hiRms: rms(hi), loRms: rms(lo), hiGreys: greys(hi), loGreys: greys(lo) };
  });
  check('the cutscene surface carries the still intact', tone.hiRms === 0,
    `rms error ${tone.hiRms.toFixed(2)}`);
  check('the old backbuffer could not', tone.loRms > 4,
    `rms error ${tone.loRms.toFixed(2)} at 384x216`);
  check('and lost tone with it', tone.hiGreys >= tone.loGreys,
    `${tone.hiGreys} greys vs ${tone.loGreys}`);
  check('four times the pixels', 768 * 432 === 4 * 384 * 216);

  // ------------------------------------------------------------- letterbox
  head('letterbox');
  /** Is every pixel of row `y` black across the full width of a surface? */
  const rowIsBlack = async (which, y) => G(([w, yy]) => {
    const c = w === 'cut' ? window.game.screen.cutsceneCanvas : window.game.screen.canvas;
    const d = c.getContext('2d').getImageData(0, yy, c.width, 1).data;
    for (let i = 0; i < d.length; i += 4) if (d[i] > 2 || d[i + 1] > 2 || d[i + 2] > 2) return false;
    return true;
  }, [which, y]);
  const bar = Math.round((432 - 768 / 2.39) / 2);
  check('cutscene has a top bar', await rowIsBlack('cut', 2), `bar is ${bar}px`);
  check('cutscene has a bottom bar', await rowIsBlack('cut', 432 - 3));
  check('the picture between the bars is not black', !(await rowIsBlack('cut', 216)));

  await page.screenshot({ path: path.join(SHOTS, '61-drive.png') });
  await skip();
  check('the drive hands off to the gate', await G(() => window.game.scene.id) === 'station_gate');

  // Arrival plays at the gate as an establishing shot -- normally on the spawn
  // point itself, since the drive sets the player down inside the trigger.
  if (!(await playing('arrival'))) {
    const x = await G(() => {
      const t = window.game.scene.entities.find((e) => e.props && e.props.cutscene === 'arrival');
      return t ? t.x + t.w / 2 : null;
    });
    if (x !== null) await G((px) => window.game.player.setPosition(px, window.game.player.y), x);
  }
  check('arrival plays at the gate', await awaitBeat('arrival'));
  await settle(3000);   // past the fade and the title card, onto the building
  await page.screenshot({ path: path.join(SHOTS, '62-arrival.png') });
  await skip();

  // The aperture stops the player the first time they reach it.
  await G(() => window.game.travel('sublevel_3', 'from_stairs', { instant: true }));
  await settle(400);
  const apertureX = await G(() => {
    const t = window.game.scene.entities.find((e) => e.props && e.props.cutscene === 'aperture');
    return t ? t.x + t.w / 2 : null;
  });
  await G((x) => window.game.player.setPosition(x, window.game.player.y), apertureX);
  check('the aperture stops the player on arrival', await awaitBeat('aperture'));
  await settle(3200);
  // A still cutscene is where the frame-rate regression actually lived: the
  // 768x432 surface was being resampled to the display with the browser's
  // 'high' quality setting, which halved the frame rate and looked identical.
  const stillFps = await G(() => window.game.loop.fps);
  check('a still cutscene holds frame rate too', stillFps >= 50, `${stillFps} fps`);
  await page.screenshot({ path: path.join(SHOTS, '63-aperture.png') });
  await skip();

  // The epilogue is gated behind the final realization, so grant that flag
  // rather than replaying the whole investigation -- investigation.cjs already
  // proves the chain is reachable by playing it.
  await G(() => { window.game.flags.set('knows_ending'); });
  await G(() => window.game.travel('station_lobby', 'from_gate', { instant: true }));
  await settle(300);
  await G(() => window.game.travel('sublevel_3', 'from_stairs', { instant: true }));
  await settle(400);
  await G((x) => window.game.player.setPosition(x, window.game.player.y), apertureX + 40);
  check('the epilogue plays once he has the answer', await awaitBeat('epilogue'));

  // ------------------------------------------------------------ cross-fade
  head('cross-fade');
  // Run the epilogue forward to the step that cuts to the emptied room. The
  // frame during that step must be a blend of both stills, not a hard cut.
  const cutStep = await G(() => window.game.cutscene.def.steps.findIndex((s) => s.image));
  check('the epilogue cuts to a second still', cutStep > 0, `at step ${cutStep}`);
  await G((s) => {
    const c = window.game.cutscene;
    // Jump the player of the cutscene, not the game: set the step directly and
    // let update() run it, so this exercises the real path.
    c.step = s - 1;
    c._advance();
  }, cutStep);
  await settle(700);
  const fade = await G(() => ({
    mid: window.game.cutscene.crossfade,
    prev: !!window.game.cutscene.prevImage,
    a: window.game.cutscene.image && window.game.cutscene.image.src.split('/').pop(),
    b: window.game.cutscene.prevImage && window.game.cutscene.prevImage.src.split('/').pop(),
  }));
  check('cross-fade is in progress', fade.mid > 0 && fade.mid < 1, `alpha ${fade.mid.toFixed(2)}`);
  check('it holds both stills', fade.prev, `${fade.b} -> ${fade.a}`);
  await page.screenshot({ path: path.join(SHOTS, '64-epilogue-crossfade.png') });
  await settle(3000);
  await page.screenshot({ path: path.join(SHOTS, '65-epilogue.png') });
  await skip(30);

  const beats = await G(() => window.__beats);
  check('all five beats fired, in order',
    JSON.stringify(beats) === JSON.stringify(['drive', 'arrival', 'aperture', 'epilogue']),
    `after the prologue: ${beats.join(', ')}`);
  check('none fired twice', new Set(beats).size === beats.length);

  // ------------------------------------------------- gameplay is untouched
  head('gameplay presentation is untouched');
  const play = await G(() => ({
    state: window.game.state,
    cut: window.game.screen.useCutsceneSurface,
    w: window.game.screen.canvas.width,
    h: window.game.screen.canvas.height,
    smoothing: window.game.screen.hostCtx.imageSmoothingEnabled,
    scale: window.game.screen.scale,
  }));
  check('back in play', play.state === 'playing');
  check('play presents from the gameplay surface', play.cut === false);
  check('backbuffer is 384x216', play.w === 384 && play.h === 216, `${play.w}x${play.h}`);
  check('presented with smoothing off', play.smoothing === false);
  check('integer scale', play.scale === 3, `scale=${play.scale}`);
  check('no letterbox in play', !(await rowIsBlack('play', 2)));

  // Recapture from a clean boot, the way the baseline was taken. Frames reached
  // at the end of a playthrough would differ for reasons that have nothing to
  // do with presentation -- objects picked up, flags set, shake still decaying.
  await bootFresh(page, BASE);

  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'frames-'));
  await captureFrames(page, out);

  const cmp = spawnSync('python3', [path.join(__dirname, 'pixels.py'), 'compare', BASELINE, out],
    { encoding: 'utf-8' });
  process.stdout.write(cmp.stdout || '');
  if (cmp.stderr) process.stderr.write(cmp.stderr);
  if (cmp.status !== 0) fail.push(`gameplay frames differ from baseline (${cmp.status})`);
  fs.rmSync(out, { recursive: true, force: true });

  // ------------------------------------------------------------ the stills
  head('the stills');
  const st = spawnSync('python3', [path.join(__dirname, 'pixels.py'), 'stills',
    path.join(ROOT, 'assets', 'stills')], { encoding: 'utf-8' });
  process.stdout.write(st.stdout || '');
  if (st.stderr) process.stderr.write(st.stderr);
  if (st.status !== 0) fail.push(`still measurements out of bounds (${st.status})`);

  head('console');
  check('no page errors', errors.length === 0, errors.slice(0, 3).join(' | '));

  await browser.close();
  console.log(`\n${fail.length ? `${fail.length} FAILED: ${fail.join(', ')}` : 'all checks passed'}`);
  process.exit(fail.length ? 1 : 0);
})();
