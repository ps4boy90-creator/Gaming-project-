/**
 * End-to-end verification for the 3D farm scene (farm/index.html).
 *
 * Like the other suites here it drives a real browser and checks what a
 * player would actually see and bump into, rather than the modules alone:
 * that the scene boots and draws, that the picture sits inside the brightness
 * and colour targets the look was tuned against, and that walls, fences, the
 * porch and the barn door behave like walls, fences, a porch and a door.
 *
 *   python3 -m http.server 8000 &
 *   node tools/verify/farm.cjs
 *
 * Screenshots land in tools/verify/shots/farm-*.png. Set CHROME to a Chromium
 * binary and BASE to a different server if the defaults are wrong.
 */
let chromium;
try { ({ chromium } = require('playwright-core')); } catch { ({ chromium } = require('playwright')); }
const fs = require('fs');
const path = require('path');
const BASE = process.env.BASE || 'http://127.0.0.1:8000';
const SHOTS = path.join(__dirname, 'shots');
const fail = [];
const check = (name, cond, extra = '') => {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  ' + extra : ''}`);
  if (!cond) fail.push(name);
};
const fmt = (m) => `mean ${m.mean.toFixed(3)}  under-10% ${(m.dark * 100).toFixed(0)}%  p95 ${m.p95.toFixed(2)}  hue ${m.hue.toFixed(0)}`;

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch({
    args: ['--no-sandbox'],
    ...(process.env.CHROME ? { executablePath: process.env.CHROME } : {}),
  });
  const page = await browser.newPage({ viewport: { width: 1152, height: 648 } });
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));
  const G = (fn, arg) => page.evaluate(fn, arg);

  // ?manual stops the page's own loop so every frame here is one we asked for;
  // ?time pins the clock so grain, sway and flicker are the same every run.
  await page.goto(`${BASE}/farm/index.html?manual=1&time=9`);
  await page.waitForFunction(() => window.farm && window.farm.state !== 'loading', null, { timeout: 60000 });
  check('boots', await G(() => farm.state) === 'playing', await G(() => farm.error || ''));

  const world = await G(() => ({
    verts: farm.world.vertexCount, trees: farm.world.treeCount, lights: farm.world.lights.length,
    boxes: farm.world.boxes.length, trunks: farm.world.trunks.length,
  }));
  check('the forest is a forest', world.trees > 1200, `${world.trees} trees, ${world.verts} vertices`);
  check('lights fit the shader', world.lights > 3 && world.lights <= 12, `${world.lights} lights`);

  /** Stand somewhere, look somewhere, measure the frame and keep a picture of it. */
  const shot = async (name, x, z, yaw, pitch = 0, torch = false) => {
    const m = await G(([x, z, yaw, pitch, torch]) => {
      farm.torch = torch; farm.setPose(x, z, yaw, pitch); return farm.measure();
    }, [x, z, yaw, pitch, torch]);
    await G(() => new Promise((r) => requestAnimationFrame(() => { farm.render(); requestAnimationFrame(r); })));
    await page.screenshot({ path: path.join(SHOTS, `farm-${name}.png`) });
    return m;
  };

  // --- the look. Targets come from measuring night exteriors in the
  // reference games: a frame averaging 4-8% brightness with four fifths of it
  // under 10%, blue overall, and orange wherever a lamp is doing the work.
  const arrive = await shot('arrive', 4.6, 20.5, 0.12, 0.03);
  check('arrival: dark', arrive.mean > 0.04 && arrive.mean < 0.08, fmt(arrive));
  check('arrival: mostly near-black', arrive.dark > 0.8, fmt(arrive));
  check('arrival: night is blue', arrive.hue > 185 && arrive.hue < 235, fmt(arrive));
  check('arrival: something is lit', arrive.p95 > 0.1, fmt(arrive));

  const porch = await shot('porch', -7.5, 4.5, 0.25, 0.12);
  check('porch: lamplight is warm', porch.hue > 10 && porch.hue < 50, fmt(porch));
  check('porch: brighter than the yard', porch.mean > arrive.mean * 1.4, fmt(porch));

  const barn = await shot('barn', 8, -6, -1.0, 0.2);
  check('barn: lit, but still a night shot', barn.mean < 0.16 && barn.p95 > 0.15, fmt(barn));

  const woods = await shot('woods', -20, -27, 2.6, 0.12);
  check('tree line: darker than the yard, still blue', woods.dark > 0.75 && woods.hue > 185 && woods.hue < 235, fmt(woods));
  await shot('road', -20, 22, -1.57, 0.05);
  await shot('house-back', -14, -17, -2.2, 0.12);

  // --- the torch and the tape filter both have to change the picture.
  const loftDark = await shot('barn-inside-dark', 18.4, -9.2, -0.28, 0.1);
  const loftLit = await shot('barn-inside-torch', 18.4, -9.2, -0.28, 0.1, true);
  check('inside the barn is black without a torch', loftDark.mean < 0.05, fmt(loftDark));
  check('the torch lights it', loftLit.p95 > loftDark.p95 + 0.05, fmt(loftLit));
  const clean = await G(() => { farm.tape = 0; farm.torch = false; farm.setPose(4.6, 20.5, 0.12, 0.03); const m = farm.measure(); farm.tape = 1; return m; });
  check('the tape filter lifts the blacks', arrive.mean > clean.mean, `filtered ${arrive.mean.toFixed(3)} vs clean ${clean.mean.toFixed(3)}`);

  // --- walking. The simulation is stepped directly, so this is exact and fast.
  const walk = (x, z, yaw, seconds, run = false) => G(([x, z, yaw, seconds, run]) => {
    farm.setPose(x, z, yaw, 0);
    for (let i = 0; i < seconds * 60; i++) farm.step(1 / 60, { fwd: 1, strafe: 0 }, run);
    const p = farm.player;
    return { x: p.x, z: p.z, floor: p.floor, inside: farm.query.insideBarn(p.x, p.z), ok: farm.query.inBounds(p.x, p.z) };
  }, [x, z, yaw, seconds, run]);

  let p = await walk(4, 20, 0, 8);
  check('the gate is open', p.z < 10, `ended at z ${p.z.toFixed(1)}`);
  p = await walk(12, 20, 0, 8);
  check('the fence is not', p.z > 14, `ended at z ${p.z.toFixed(1)}`);

  const house = await G(() => ({ ...farm.site.house }));
  const toWorld = (s, lx, lz) => [s.x + lx * Math.cos(s.yaw) + lz * Math.sin(s.yaw), s.z - lx * Math.sin(s.yaw) + lz * Math.cos(s.yaw)];
  // Everything about the house is said in its own coordinates: front is +Z,
  // the dining room is at -X, the kitchen beyond the back wall at -Z.
  const local = (s, q) => { const c = Math.cos(s.yaw), sn = Math.sin(s.yaw), dx = q.x - s.x, dz = q.z - s.z; return { x: dx * c - dz * sn, z: dx * sn + dz * c }; };
  const heading = (s, dx, dz) => { const c = Math.cos(s.yaw), sn = Math.sin(s.yaw); return Math.atan2(-(dx * c + dz * sn), -(-dx * sn + dz * c)); };
  const inHouse = async (fx, fz, dx, dz, seconds) => {
    const [wx, wz] = toWorld(house, fx, fz);
    const q = await walk(wx, wz, heading(house, dx, dz), seconds);
    return { ...local(house, q), floor: q.floor, home: await G(([x, z]) => farm.query.insideHouse(x, z), [q.x, q.z]) };
  };
  let h = await inHouse(0, 9.5, 0, -1, 3.2);            // up the steps
  check('the steps lead onto the porch', Math.abs(h.floor - 0.5) < 0.03 && !h.home, `floor ${h.floor.toFixed(2)}`);
  h = await inHouse(0, 9.5, 0, -1, 6);                  // and on through the front door
  check('the front door stands open', h.home && h.z < 2.2, `ended ${h.z.toFixed(1)} m from the middle of the house`);
  h = await inHouse(-9, 0.4, 1, 0, 5);                  // at the west wall, from the lawn
  check('the walls do not', !h.home && h.x < -4.7, `stopped at x ${h.x.toFixed(2)}`);
  h = await inHouse(0, 1.0, -1, 0, 1.5);
  check('hall to dining room', h.x < -1.5, `x ${h.x.toFixed(2)}`);
  h = await inHouse(-1.6, 0.3, -1, 0, 4);               // at the laid table
  check('the dining table and chairs are solid', h.x > -2.2, `stopped at x ${h.x.toFixed(2)}`);
  h = await inHouse(-2.45, -2.2, 0, -1, 2.5);
  check('dining room to kitchen', h.z < -3.9 && h.home, `z ${h.z.toFixed(2)}`);
  h = await inHouse(-2.45, -4.2, 0, -1, 4);             // at the sink
  check('the kitchen counter stops you', h.z > -5.2, `stopped at z ${h.z.toFixed(2)}`);
  h = await inHouse(0, 1.0, 1, 0, 1.5);
  check('hall to living room', h.x > 1.5, `x ${h.x.toFixed(2)}`);
  h = await inHouse(2.4, 0.9, 1, 0, 5);                 // across the room to the east wall
  check('you cannot leave through a wall', h.home && h.x < 4.1, `stopped at x ${h.x.toFixed(2)}`);
  h = await inHouse(-0.4, -0.2, 0, -1, 5);              // down the passage to the clock
  check('the stair door is shut and the passage ends', h.z > -3.1 && h.x < 0.15, `(${h.x.toFixed(2)}, ${h.z.toFixed(2)})`);

  // --- indoors is lit the way the reference interiors are: warm, and about
  // a fifth as bright as the screen will go, never the full glare of a lamp.
  const face = (fx, fz, dx, dz) => { const [wx, wz] = toWorld(house, fx, fz); return [wx, wz, heading(house, dx, dz)]; };
  const dining = await shot('dining', ...face(-1.6, 2.6, -0.68, -0.73), -0.1);
  check('dining room: warm and lamp-lit', dining.hue > 15 && dining.hue < 50 && dining.mean > 0.12 && dining.mean < 0.3, fmt(dining));
  const tvRoom = await shot('living', ...face(1.5, 1.0, 0.81, 0.59), -0.1);
  check('living room: lit by the television', tvRoom.hue > 180 && tvRoom.hue < 250 && tvRoom.mean < 0.25, fmt(tvRoom));
  await shot('hall', ...face(0, 3.0, 0, -1), -0.05);
  await shot('kitchen', ...face(-2.6, -4.4, 0.98, 0.18), -0.25);
  await shot('sofa', ...face(3.6, 0.6, -0.81, -0.58), -0.22);
  let sx, sz;
  [sx, sz] = toWorld(house, -3, 9.5);
  p = await walk(sx, sz, house.yaw, 6);            // at the porch railing
  check('the porch rail keeps you off the deck', p.floor < 0.1, `floor ${p.floor.toFixed(2)}`);

  const barnSite = await G(() => ({ ...farm.site.barn }));
  [sx, sz] = toWorld(barnSite, 0.65, 11);
  p = await walk(sx, sz, barnSite.yaw, 5);         // through the gap in the doors
  check('the open barn door lets you in', p.inside, `(${p.x.toFixed(1)}, ${p.z.toFixed(1)})`);
  [sx, sz] = toWorld(barnSite, -1, 11);
  p = await walk(sx, sz, barnSite.yaw, 5);         // into the shut leaf
  check('the shut one does not', !p.inside, `(${p.x.toFixed(1)}, ${p.z.toFixed(1)})`);

  const truck = await G(() => ({ ...farm.site.truck }));
  [sx, sz] = toWorld(truck, 0, 7);
  p = await walk(sx, sz, truck.yaw, 6);            // straight at the pickup's tailgate
  const [tx, tz] = toWorld(truck, 0, 0);
  const fromTruck = Math.hypot(p.x - tx, p.z - tz);
  check('the pickup is solid', fromTruck > 2.9 && fromTruck < 3.4, `stopped ${fromTruck.toFixed(2)} m from its centre`);
  const shadows = await G(() => farm.world.occluders.length);
  check('house, barn and pickup cast moon shadows', shadows >= 6 && shadows <= 8, `${shadows} shadow boxes`);
  await shot('truck', 3.2, 9.2, 0.62, -0.16, true);

  p = await walk(4.6, 20.5, Math.PI, 60, true);    // run south into the trees for a minute
  check('the forest closes in before the map runs out', p.ok && p.z < 60, `stopped at z ${p.z.toFixed(1)}`);

  // --- the page as a player meets it: a title card, then click and walk.
  await page.goto(`${BASE}/farm/index.html`);
  await page.waitForFunction(() => window.farm && window.farm.state !== 'loading', null, { timeout: 60000 });
  check('opens on the title card', await G(() => farm.state) === 'title');
  await page.click('#view');
  const z0 = await G(() => farm.player.z);
  // Wait on distance, not time: under a software renderer a frame can take
  // a second, and the simulation deliberately refuses to take big steps.
  await page.keyboard.down('KeyW');
  await page.waitForFunction((z) => farm.player.z < z - 0.25, z0, { timeout: 60000 }).catch(() => {});
  await page.keyboard.up('KeyW');
  const live = await G(() => ({ state: farm.state, z: farm.player.z, hidden: document.getElementById('title').classList.contains('gone') }));
  check('a click starts it and W walks', live.state === 'playing' && live.z < z0 - 0.25 && live.hidden, `moved ${(z0 - live.z).toFixed(2)} m`);
  await page.keyboard.press('KeyF');
  check('F toggles the torch', await G(() => farm.torch) === true);

  // --- a phone: no keyboard, no mouse. The left thumb walks, the right looks.
  const phone = await browser.newContext({ viewport: { width: 844, height: 390 }, hasTouch: true, isMobile: true });
  const tp = await phone.newPage();
  tp.on('pageerror', (e) => errors.push('PAGEERROR (touch): ' + e.message));
  await tp.goto(`${BASE}/farm/index.html`);
  await tp.waitForFunction(() => window.farm && window.farm.state !== 'loading', null, { timeout: 60000 });
  const cdp = await phone.newCDPSession(tp);
  const touch = (type, pts) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map(([x, y, id]) => ({ x, y, id })) });
  const before = await tp.evaluate(() => ({ z: farm.player.z, yaw: farm.player.yaw }));
  await touch('touchStart', [[150, 250, 1]]);
  await touch('touchMove', [[150, 180, 1]]);                       // left thumb pushed up
  await tp.waitForFunction((z) => farm.player.z < z - 0.2, before.z, { timeout: 60000 }).catch(() => {});
  await touch('touchStart', [[150, 180, 1], [650, 200, 2]]);
  await touch('touchMove', [[150, 180, 1], [560, 200, 2]]);        // right thumb dragged left
  const after = await tp.evaluate(() => ({
    state: farm.state, z: farm.player.z, yaw: farm.player.yaw,
    pad: getComputedStyle(document.getElementById('pad')).display, stick: !document.getElementById('stick').hidden,
  }));
  await touch('touchEnd', []);
  check('touch: a tap starts it and the left thumb walks', after.state === 'playing' && after.z < before.z - 0.2, `moved ${(before.z - after.z).toFixed(2)} m`);
  check('touch: the right thumb turns the view', after.yaw > before.yaw + 0.2, `turned ${(after.yaw - before.yaw).toFixed(2)} rad`);
  check('touch: the thumbstick and buttons appear', after.pad === 'flex' && after.stick);
  const released = await tp.waitForFunction(() => farm.stick.fwd === 0 && document.getElementById('stick').hidden, null, { timeout: 30000 }).then(() => true, () => false);
  check('touch: the stick lets go', released);
  // The buttons are tapped, and the picture taken, with the page's own loop
  // stopped. Chrome delivers touch input and screenshots in step with frames,
  // and a software renderer taking seconds over each one starves both; the
  // buttons themselves do not care.
  await tp.goto(`${BASE}/farm/index.html?manual=1`);
  await tp.waitForFunction(() => window.farm && window.farm.state !== 'loading', null, { timeout: 60000 });
  await touch('touchStart', [[150, 250, 1]]);
  await touch('touchEnd', []);
  await tp.tap('#torch');
  await tp.tap('#run');
  const btn = await tp.evaluate(() => ({ torch: farm.torch, run: farm.running }));
  check('touch: the TORCH and RUN buttons work', btn.torch === true && btn.run === true);
  await tp.evaluate(() => { farm.torch = false; farm.render(); });
  await tp.screenshot({ path: path.join(SHOTS, 'farm-phone.png') });
  await phone.close();

  check('no console errors', errors.length === 0, errors.slice(0, 3).join(' | '));
  await browser.close();
  console.log(fail.length ? `\n${fail.length} FAILED: ${fail.join(', ')}` : '\nall passed');
  process.exit(fail.length ? 1 : 0);
})();
