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
  check('lights fit the shader', world.lights > 3 && world.lights <= 16, `${world.lights} lights`);

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

  /**
   * Walk a path of waypoints given in a site's own coordinates, with the real
   * simulation and no teleporting after the start -- the only honest way to
   * show that a route through the furniture exists.
   */
  const route = (site, pts, up = false) => G(([s, pts, up]) => {
    const c = Math.cos(s.yaw), sn = Math.sin(s.yaw);
    const W = ([lx, lz]) => [s.x + lx * c + lz * sn, s.z - lx * sn + lz * c];
    const [x0, z0] = W(pts[0]);
    farm.setPose(x0, z0, 0, 0, up);
    let stuck = 0;
    for (let k = 1; k < pts.length && !stuck; k++) {
      const [tx, tz] = W(pts[k]);
      for (let n = 0; Math.hypot(tx - farm.player.x, tz - farm.player.z) > 0.18; n++) {
        farm.player.yaw = Math.atan2(-(tx - farm.player.x), -(tz - farm.player.z));
        farm.step(1 / 60, { fwd: 1, strafe: 0 }, false);
        if (n > 60 * 12) { stuck = k; break; }
      }
    }
    const q = farm.player, dx = q.x - s.x, dz = q.z - s.z;
    return { stuck, x: dx * c - dz * sn, z: dx * sn + dz * c, floor: q.floor, home: farm.query.insideHouse(q.x, q.z) };
  }, [site, pts, up]);

  /**
   * Operate a door the way a player does: find somewhere within reach to
   * stand that is not inside anything, look at the handle, and use it.
   * Returns what the screen offered and whether the door then moved.
   */
  await G(() => {
    window.tryDoor = (d) => {
      const was = d.isOpen, h = d.handle, up = h[1] > 3;
      for (let k = 0; k < 16; k++) {
        const a = (k * Math.PI) / 8, x = h[0] + Math.sin(a) * 1.1, z = h[2] + Math.cos(a) * 1.1;
        farm.setPose(x, z, 0, 0, up);
        farm.step(1 / 60, { fwd: 0, strafe: 0 }, false);
        if (Math.hypot(farm.player.x - x, farm.player.z - z) > 0.02) continue;
        const e = farm.player.eye, dx = h[0] - e[0], dy = h[1] - e[1], dz = h[2] - e[2];
        farm.player.yaw = Math.atan2(-dx, -dz); farm.player.pitch = Math.atan2(dy, Math.hypot(dx, dz));
        const t = farm.looking();
        if (!t || t.door !== d) continue;
        const label = t.label();
        farm.use();
        for (let n = 0; n < 110; n++) farm.step(1 / 60, { fwd: 0, strafe: 0 }, false);
        return { label, moved: d.isOpen !== was && d.t === d.goal };
      }
      return { label: null, moved: false };
    };
  });
  /** The door whose handle is nearest a point in a site's coordinates, operated. */
  const operate = (site, lx, lz, up = false) => G(([s, lx, lz, up]) => {
    const c = Math.cos(s.yaw), sn = Math.sin(s.yaw), wx = s.x + lx * c + lz * sn, wz = s.z - lx * sn + lz * c;
    let door = null, best = 1.5;
    for (const d of farm.interact.doors) {
      if ((d.handle[1] > 3) !== up) continue;
      const r = Math.hypot(d.handle[0] - wx, d.handle[2] - wz);
      if (r < best) { best = r; door = d; }
    }
    return door ? window.tryDoor(door) : { label: 'no door there', moved: false };
  }, [site, lx, lz, up]);

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
  // Using things. `look` stands somewhere in house space facing a direction
  // and reports what the game says can be done; `use` does it; `settle` lets
  // a door finish swinging.
  const look = async (site, fx, fz, dx, dz, pitch = 0) => {
    const [wx, wz] = toWorld(site, fx, fz);
    return G(([x, z, yaw, pitch]) => { farm.setPose(x, z, yaw, pitch); const t = farm.looking(); return t ? t.label() : null; }, [wx, wz, heading(site, dx, dz), pitch]);
  };
  const use = () => G(() => farm.use());
  const settle = (s) => G((s) => { for (let i = 0; i < s * 60; i++) farm.step(1 / 60, { fwd: 0, strafe: 0 }, false); }, s);

  h = await inHouse(0, 9.5, 0, -1, 6);                  // and on, at the front door
  check('the front door is shut', !h.home && h.z > 3.6, `stopped ${h.z.toFixed(2)} m out`);
  check('looking at it offers to open it', await look(house, 0, 5.0, 0, -1, -0.1) === 'Open door');
  await use(); await settle(1.2);
  check('and then to close it', await look(house, 0, 5.0, 0, -1, -0.1) === 'Close door');
  h = await inHouse(0, 9.5, 0, -1, 6);
  check('an open door lets you in', h.home && h.z < 2.2, `ended ${h.z.toFixed(1)} m from the middle of the house`);
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
  check('the passage ends at the clock', h.z > -3.1 && h.x < 0.15 && h.floor < 0.6, `(${h.x.toFixed(2)}, ${h.z.toFixed(2)})`);

  // --- upstairs. The door at the foot of the stairs opens like any other,
  // and everything past it is walked, not teleported to.
  const CLIMB = [[0.6, 0.9], [0.6, -2.9], [-0.4, -2.95], [-0.4, 0.6]];
  h = await route(house, CLIMB.slice(0, 2));
  check('the stair door is shut', h.stuck === 1 && h.z > -0.2 && h.floor < 0.6, `stopped at z ${h.z.toFixed(2)}`);
  let d = await operate(house, 0.56, -0.2);
  check('the stair door opens', d.label === 'Open door' && d.moved, JSON.stringify(d));
  h = await route(house, CLIMB);
  check('the stairs climb to the landing', !h.stuck && Math.abs(h.floor - 3.3) < 0.03 && h.home, `stuck at ${h.stuck}, floor ${h.floor.toFixed(2)}`);
  h = await route(house, [[-0.4, -1.6], [0.9, -1.6]], true);
  check('the balustrade keeps you out of the stairwell', h.stuck === 1 && h.x < 0.15 && Math.abs(h.floor - 3.3) < 0.03, `x ${h.x.toFixed(2)}, floor ${h.floor.toFixed(2)}`);
  for (const [name, hx, hz, path, there] of [
    ['east bedroom', 1.1, -0.27, [[-0.4, 0.6], [0.5, -0.25], [2.0, -0.25]], (q) => q.x > 1.7],
    ['west bedroom', -1.1, -0.27, [[-0.4, 0.6], [-0.5, -0.25], [-2.0, -0.25]], (q) => q.x < -1.7],
    ['bathroom', -0.04, 1.59, [[-0.4, 0.6], [0, 1.2], [0.1, 2.05]], (q) => q.z > 1.8],
  ]) {
    h = await route(house, path, true);
    const shut = h.stuck > 0;
    d = await operate(house, hx, hz, true);
    h = await route(house, path, true);
    check(`upstairs: the ${name} door is shut, opens, and lets you in`, shut && d.label === 'Open door' && d.moved && !h.stuck && there(h) && Math.abs(h.floor - 3.3) < 0.03,
      `shut ${shut}, ${JSON.stringify(d)}, ended (${h.x.toFixed(2)}, ${h.z.toFixed(2)})`);
  }
  h = await route(house, [[2.0, -0.25], [2.6, -2.1], [5.5, -2.1]], true);      // across the bedroom at its outside wall
  check('upstairs: the walls are solid and a long way up', h.stuck === 2 && h.x > 3.5 && h.x < 4.1 && h.home && Math.abs(h.floor - 3.3) < 0.03, `x ${h.x.toFixed(2)}, floor ${h.floor.toFixed(2)}`);
  h = await route(house, [...CLIMB].reverse(), true);
  check('and the stairs go back down', !h.stuck && Math.abs(h.floor - 0.5) < 0.03, `stuck at ${h.stuck}, floor ${h.floor.toFixed(2)}`);

  h = await inHouse(2.3, -2.0, 0, -1, 4);               // at the back door
  check('the back door is shut', h.home && h.z > -3.3, `stopped at z ${h.z.toFixed(2)}`);
  check('it opens too', await look(house, 2.3, -2.0, 0, -1, -0.15) === 'Open door');
  await use(); await settle(1.2);
  h = await inHouse(2.3, -2.0, 0, -1, 4);
  check('and leads out onto the back step', !h.home && h.z < -3.7, `ended at z ${h.z.toFixed(2)}, floor ${h.floor.toFixed(2)}`);
  // The whole trip, walked: in from the hall, round the sofa, past the coffee
  // table and out. Furniture once stood across this.
  h = await route(house, [[0, 1.12], [1.6, 1.12], [2.5, 0.2], [2.5, -2.6], [2.3, -3.2], [2.3, -5.2]]);
  check('nothing stands between the hall and the back door', !h.stuck && !h.home && h.z < -4.8, `stuck at ${h.stuck}, ended (${h.x.toFixed(2)}, ${h.z.toFixed(2)})`);

  // --- indoors is lit the way the reference interiors are: warm, and about
  // a fifth as bright as the screen will go, never the full glare of a lamp.
  const face = (fx, fz, dx, dz) => { const [wx, wz] = toWorld(house, fx, fz); return [wx, wz, heading(house, dx, dz)]; };
  const dining = await shot('dining', ...face(-1.6, 2.6, -0.68, -0.73), -0.1);
  check('dining room: warm and lamp-lit', dining.hue > 15 && dining.hue < 50 && dining.mean > 0.12 && dining.mean < 0.3, fmt(dining));
  const tvRoom = await shot('living', ...face(1.5, 1.0, 0.81, 0.59), -0.1);
  check('living room: lit by the television', tvRoom.hue > 180 && tvRoom.hue < 250 && tvRoom.mean < 0.25, fmt(tvRoom));
  // Switches. The dining light takes the room down with it, and the glow in
  // its windows; the television takes the blue out of the living room.
  check('the dining light has a switch', await look(house, -1.7, 0.3, -1, 0, 0.1) === 'Switch off the light');
  await use();
  const unlit = await shot('dining-dark', ...face(-1.6, 2.6, -0.68, -0.73), -0.1);
  check('off, the dining room is dark', unlit.mean < dining.mean * 0.45, fmt(unlit));
  await look(house, -1.7, 0.3, -1, 0, 0.1); await use();
  check('the television has one', await look(house, 2.7, 1.8, 0.7, 0.7, -0.3) === 'Switch off the television');
  await use();
  const tvOff = await G(([x, z, yaw]) => { farm.setPose(x, z, yaw, -0.1); return farm.measure(); }, face(1.5, 1.0, 0.81, 0.59));
  check('off, the living room loses its glow', tvOff.mean < tvRoom.mean * 0.8 && !(await G(() => farm.world.groups.tv.on)), fmt(tvOff));
  await look(house, 2.7, 1.8, 0.7, 0.7, -0.3); await use();
  await shot('hall', ...face(0, 3.0, 0, -1), -0.05);
  await shot('kitchen', ...face(-2.6, -4.4, 0.98, 0.18), -0.25);
  await shot('sofa', ...face(3.6, 0.6, -0.81, -0.58), -0.22);
  const upShot = async (name, fx, fz, dx, dz, pitch) => {
    const [x, z, yaw] = face(fx, fz, dx, dz);
    const m = await G(([x, z, yaw, pitch]) => { farm.torch = false; farm.setPose(x, z, yaw, pitch, true); return farm.measure(); }, [x, z, yaw, pitch]);
    await G(() => new Promise((r) => requestAnimationFrame(() => { farm.render(); requestAnimationFrame(r); })));
    await page.screenshot({ path: path.join(SHOTS, `farm-${name}.png`) });
    return m;
  };
  await shot('stairs', ...face(0.6, 0.9, 0, -1), 0.3);
  const bedE = await upShot('bedroom', 1.5, -0.3, 1, 0.5, -0.15);
  check('upstairs: the bedroom is lit by its own lamp, and warm', bedE.hue > 15 && bedE.hue < 55 && bedE.mean > 0.06 && bedE.mean < 0.3, fmt(bedE));
  const bathDark = await upShot('bathroom-dark', 0.05, 1.8, -0.1, 1, -0.3);
  await G(() => farm.interact.setGroup('bath', true));
  const bath = await upShot('bathroom', 0.05, 1.8, -0.1, 1, -0.3);
  check('upstairs: the bathroom starts dark and its light works', bath.mean > bathDark.mean * 1.6, `${fmt(bathDark)}  ->  ${fmt(bath)}`);
  await G(() => farm.interact.setGroup('bedW', true));
  await upShot('childs-room', -1.5, -0.3, -1, 0.35, -0.12);
  await upShot('landing', -0.55, 1.2, 0.3, -1, -0.3);
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
  check('the open leaf can be slid shut', await look(barnSite, 1.6, 8.6, 0.25, -1, 0) === 'Close barn door');
  await use(); await settle(1.6);
  [sx, sz] = toWorld(barnSite, 0.65, 11);
  p = await walk(sx, sz, barnSite.yaw, 5);
  check('and then the barn is shut', !p.inside, `(${p.x.toFixed(1)}, ${p.z.toFixed(1)})`);
  await look(barnSite, 1.0, 8.6, 0, -1, 0); await use(); await settle(1.6);
  const leaves = await G(() => farm.interact.doors.filter((d) => d.noun === 'barn door').map((d) => window.tryDoor(d)));
  [sx, sz] = toWorld(barnSite, -1, 11);
  p = await walk(sx, sz, barnSite.yaw, 5);         // where the shut leaf was
  check('both barn leaves slide, and the other one lets you in too', leaves.length === 2 && leaves.every((l) => l.moved) && p.inside, JSON.stringify(leaves));
  await G(() => farm.interact.doors.filter((d) => d.noun === 'barn door').forEach((d) => window.tryDoor(d)));

  const truck = await G(() => ({ ...farm.site.truck }));
  [sx, sz] = toWorld(truck, 0, 7);
  p = await walk(sx, sz, truck.yaw, 6);            // straight at the pickup's tailgate
  const [tx, tz] = toWorld(truck, 0, 0);
  const fromTruck = Math.hypot(p.x - tx, p.z - tz);
  check('the pickup is solid', fromTruck > 2.9 && fromTruck < 3.4, `stopped ${fromTruck.toFixed(2)} m from its centre`);
  const shadows = await G(() => farm.world.occluders.length);
  check('house, barn and pickup cast moon shadows', shadows >= 6 && shadows <= 8, `${shadows} shadow boxes`);
  await shot('truck', 3.2, 9.2, 0.62, -0.16, true);
  const cab = await G(() => farm.interact.doors.filter((d) => d.noun === 'truck door').map((d) => window.tryDoor(d)));
  check('both truck doors open', cab.length === 2 && cab.every((c) => c.label === 'Open truck door' && c.moved), JSON.stringify(cab));
  {
    const [x, z] = toWorld(truck, -2.6, 1.9);
    await shot('truck-open', x, z, heading(truck, 1.5, -1.6), -0.14, true);
  }
  // Every door in the place, one after another: none is scenery.
  const all = await G(() => farm.interact.doors.map((d) => ({ noun: d.noun, ...window.tryDoor(d) })));
  check('every door opens', all.length === 10 && all.every((a) => a.moved), all.filter((a) => !a.moved).map((a) => a.noun + ': ' + a.label).join(', ') || `${all.length} doors`);

  p = await walk(4.6, 20.5, Math.PI, 60, true);    // run south into the trees for a minute
  check('the forest closes in before the map runs out', p.ok && p.z < 60, `stopped at z ${p.z.toFixed(1)}`);

  // --- the page as a player meets it: a title card, then click and walk.
  // These steps need real frames to go by, and this suite usually runs on a
  // software renderer that takes seconds over a full one. So the live page is
  // asked for a small picture; it is the controls being tested here, not it.
  page.setDefaultTimeout(90000);
  await page.setViewportSize({ width: 480, height: 270 });
  await page.goto(`${BASE}/farm/index.html?lines=120`);
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
  // E uses whatever is in front of you. Stand at the front door and press it.
  await G(() => { const s = farm.site.house, c = Math.cos(s.yaw), n = Math.sin(s.yaw); farm.setPose(s.x + 5.0 * n, s.z + 5.0 * c, s.yaw, -0.1); });
  await page.waitForFunction(() => farm.prompt === 'Open door', null, { timeout: 60000 }).catch(() => {});
  const hud = await G(() => ({ prompt: farm.prompt, shown: !document.getElementById('prompt').hidden && document.getElementById('what').textContent }));
  await page.keyboard.press('KeyE');
  const opened = await page.waitForFunction(() => farm.interact.doors[0].isOpen, null, { timeout: 30000 }).then(() => true, () => false);
  check('the screen says what E will do, and E does it', hud.prompt === 'Open door' && opened, JSON.stringify(hud));

  // --- a phone: no keyboard, no mouse. The left thumb walks, the right looks.
  const phone = await browser.newContext({ viewport: { width: 422, height: 195 }, hasTouch: true, isMobile: true });
  const tp = await phone.newPage();
  tp.on('pageerror', (e) => errors.push('PAGEERROR (touch): ' + e.message));
  tp.setDefaultTimeout(90000);
  await tp.goto(`${BASE}/farm/index.html?lines=120`);
  await tp.waitForFunction(() => window.farm && window.farm.state !== 'loading', null, { timeout: 60000 });
  const cdp = await phone.newCDPSession(tp);
  const touch = (type, pts) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map(([x, y, id]) => ({ x, y, id })) });
  const before = await tp.evaluate(() => ({ z: farm.player.z, yaw: farm.player.yaw }));
  await touch('touchStart', [[80, 130, 1]]);
  await touch('touchMove', [[80, 60, 1]]);                         // left thumb pushed up
  await tp.waitForFunction((z) => farm.player.z < z - 0.2, before.z, { timeout: 60000 }).catch(() => {});
  await touch('touchStart', [[80, 60, 1], [330, 100, 2]]);
  await touch('touchMove', [[80, 60, 1], [240, 100, 2]]);          // right thumb dragged left
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
  await tp.setViewportSize({ width: 844, height: 390 });
  await touch('touchStart', [[150, 250, 1]]);
  await touch('touchEnd', []);
  await tp.tap('#torch');
  await tp.tap('#run');
  const btn = await tp.evaluate(() => ({ torch: farm.torch, run: farm.running }));
  check('touch: the TORCH and RUN buttons work', btn.torch === true && btn.run === true);
  await tp.evaluate(() => { const s = farm.site.house, c = Math.cos(s.yaw), n = Math.sin(s.yaw); farm.setPose(s.x + 5.0 * n, s.z + 5.0 * c, s.yaw, -0.1); farm.step(1 / 60, { fwd: 0, strafe: 0 }, false); });
  await tp.waitForFunction(() => !document.getElementById('use').disabled, null, { timeout: 10000 }).catch(() => {});
  await tp.tap('#use');
  check('touch: the USE button opens the door in front of you', await tp.evaluate(() => farm.interact.doors[0].isOpen));
  await tp.evaluate(() => { farm.torch = false; farm.render(); });
  await tp.screenshot({ path: path.join(SHOTS, 'farm-phone.png') });
  await phone.close();

  check('no console errors', errors.length === 0, errors.slice(0, 3).join(' | '));
  await browser.close();
  console.log(fail.length ? `\n${fail.length} FAILED: ${fail.join(', ')}` : '\nall passed');
  process.exit(fail.length ? 1 : 0);
})();
