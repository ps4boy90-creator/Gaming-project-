// Functional playtest of Milestone 1 in headless Chromium. Exits non-zero on failure.
// Usage: node tests/smoke.mjs [url]
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const playwright = require('playwright');
const url = process.argv[2] ?? 'http://localhost:4173/';
const browser = await playwright.chromium.launch({ args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const ctx = await browser.newContext({ viewport: { width: 640, height: 360 } });
const page = await ctx.newPage();
page.setDefaultTimeout(180000);
await page.addInitScript(() => {
  if (!localStorage.getItem('seedfall.settings.v1')) localStorage.setItem('seedfall.settings.v1', JSON.stringify({ quality: 'low' }));
});
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

let failed = 0;
const check = (name, ok, detail = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  · ' + detail : ''}`);
  if (!ok) failed++;
};
const S = (fn, arg) => page.evaluate(fn, arg);
const wait = (ms) => page.waitForTimeout(ms);
const step = (sec) => S((t) => window.__seedfall.step(t), sec);
const hold = async (key, ms) => { await page.keyboard.down(key); await step(ms / 1000); await page.keyboard.up(key); await step(0.1); };
const press = async (key, sec = 0.3) => { await page.keyboard.press(key); await step(sec); };
const tp = async (x, y, z, yaw = 0, pitch = 0) => { await S((a) => window.__seedfall.teleport(...a), [x, y, z, yaw, pitch]); await step(0.1); };
const aim = async (x, y, z) => { await S((a) => window.__seedfall.aim(...a), [x, y, z]); await step(0.05); };

await page.goto(url);
await page.waitForFunction(() => !document.getElementById('title')?.hidden, null, { timeout: 240000 });
check('title screen appears', true);
await page.click('#btn-new');
await page.waitForFunction(() => window.__seedfall.state() === 'play', null, { timeout: 60000 });
check('new game starts lying in your hypersleep pod', (await S(() => window.__seedfall.mode())) === 'lying' && (await S(() => window.__seedfall.info().room)) === 'sleepbay');
check('pod shows the stand-up prompt', /Stand up/.test((await S(() => window.__seedfall.prompt())) ?? ''), await S(() => window.__seedfall.prompt()));

await press('Space', 0.8);
check('Space gets you up', (await S(() => window.__seedfall.mode())) === 'walk');
check('getup objective completes', !!(await S(() => window.__seedfall.flags()['obj:getup'])));
const outPod = await S(() => window.__seedfall.info());
check('you climb out into the sleep bay aisle', outPod.room === 'sleepbay', `room ${outPod.room} at ${outPod.pos.map((v) => v.toFixed(1)).join(', ')}`);

// walking + collision
const p0 = await S(() => window.__seedfall.info().pos);
await tp(-11, 4, 5.5, Math.PI, 0); // cabin, facing the hull (+z)
await hold('w', 2500);
const p1 = await S(() => window.__seedfall.info().pos);
check('walking moves the player', Math.abs(p1[2] - 5.5) > 1, `z ${p1[2].toFixed(2)}`);
check('hull wall stops the player', p1[2] < 8.8, `z ${p1[2].toFixed(2)} (hull at 9.0)`);
check('player stays on the deck floor', Math.abs(p1[1] - 4) < 0.05, `y ${p1[1].toFixed(3)}`);
void p0;

// terminal
await tp(-9.6, 4, 4.4, -Math.PI / 2, 0);
await aim(-8.3, 5.1, 4.4);
const pr = await S(() => window.__seedfall.prompt());
check('cabin terminal prompt', pr === 'Read messages', String(pr));
await press('f');
check('terminal opens', (await S(() => window.__seedfall.state())) === 'reader');
for (const n of [2, 3]) await page.click(`.mail-item:nth-child(${n})`);
check('reading mail completes the objective', !!(await S(() => window.__seedfall.flags()['obj:mail'])));
await page.click('#reader-close');
await step(0.3);
check('terminal closes', ['play', 'paused'].includes(await S(() => window.__seedfall.state())));
if ((await S(() => window.__seedfall.state())) === 'paused') await page.click('#btn-resume');

// doors
await tp(-11, 4, -0.4, 0, 0);
await step(1.6);
const dcab = await S(() => window.__seedfall.doorAt(-11, 1.5));
check('cabin door opens when you approach', dcab.open > 0.9, `open ${dcab.open.toFixed(2)}`);
await tp(-8, 4, -0.2, 0, 0);
await step(1.5);
const dlock = await S(() => window.__seedfall.doorAt(-8, -1.5));
check('locked crew door stays shut', dlock.locked && dlock.open < 0.05);

// walk through an open door into the corridor and out to the lobby
await tp(-11, 4, 3.5, 0, 0); // inside cabin, facing -z (corridor)
await hold('w', 2600);
const p2 = await S(() => window.__seedfall.info());
check('walk out through the cabin door', p2.pos[2] < 1.6, `z ${p2.pos[2].toFixed(2)} room ${p2.room}`);

// long walks past the new ribs, handrails and wall equipment
await tp(-13.2, 4, 0, -Math.PI / 2, 0); // Deck 2 corridor, facing the bow
await hold('w', 9500);
const pc = await S(() => window.__seedfall.info().pos);
check('walk the full Deck 2 corridor', pc[0] > 12, `x ${pc[0].toFixed(2)}`);
await tp(-19, 0, 0, Math.PI / 2, 0); // spine, facing aft
await hold('w', 19000);
const ps = await S(() => window.__seedfall.info());
check('walk the spine to the suit room', ps.pos[0] < -69, `x ${ps.pos[0].toFixed(2)} room ${ps.room}`);

// lift
await tp(-16, 4, -4.4, -Math.PI / 2, 0);
await aim(-14.75, 5.38, -3.65);
const lp = await S(() => window.__seedfall.prompt());
check('lift button prompt', /Deck 1/.test(lp ?? ''), String(lp));
await press('f', 0.2);
for (let i = 0; i < 12; i++) { await step(0.5); await wait(400); }
const ly = await S(() => window.__seedfall.info().pos[1]);
check('lift carries you to Deck 1', Math.abs(ly - 8) < 0.05, `y ${ly}`);

// sitting
await tp(-3.2, 8, 5.2, Math.PI, 0);
await aim(-3.2, 8.47, 6.42);
const sp = await S(() => window.__seedfall.prompt());
check('bench prompt', /Sit/.test(sp ?? ''), String(sp));
await press('f', 0.9);
check('sit on the viewing bench', (await S(() => window.__seedfall.mode())) === 'seated');
await press('Space', 0.5);
check('stand up again', (await S(() => window.__seedfall.mode())) === 'walk');

// bridge: blinders open on entry; sit in the pilot seat on the raised flight deck
await tp(9.0, 8, 0, -Math.PI / 2, 0);
await step(4);
check('bridge blinders open when you walk in', !!(await S(() => window.__seedfall.flags().blinds)));
await tp(12.35, 8.22, 0.48, -Math.PI / 2, 0);
await aim(13.14, 8.74, 0.48);
const pp = await S(() => window.__seedfall.prompt());
check('pilot seat prompt on the flight deck', /Pilot seat/.test(pp ?? ''), String(pp));
await press('f', 0.9);
check('sit in the pilot seat', (await S(() => window.__seedfall.mode())) === 'seated');
await press('Space', 0.5);
// walk from the bridge door, round the captain's chair, up onto the flight deck
await tp(8.6, 8, 0.0, -Math.PI / 2, 0);
await S(() => window.__seedfall.look(-Math.PI / 2 - 0.35, 0));
await hold('w', 900);
await S(() => window.__seedfall.look(-Math.PI / 2, 0));
await hold('w', 2200);
const pd = await S(() => window.__seedfall.info().pos);
check('walk from the door up onto the flight deck', pd[0] > 11.6 && pd[1] > 8.2, `x ${pd[0].toFixed(2)} y ${pd[1].toFixed(2)}`);

// telescope
await tp(6.6, 8, 6.3, Math.PI, 0);
await aim(6.6, 9.4, 7.9);
const tpr = await S(() => window.__seedfall.prompt());
check('telescope prompt', tpr === 'Use telescope', String(tpr));
await press('f', 8);
check('telescope survey marks LZ-1', !!(await S(() => window.__seedfall.flags().lz1)));
await press('f', 0.5);
check('leave the telescope', (await S(() => window.__seedfall.state())) === 'play');

// sleep + save
await S(() => window.__seedfall.sitBunk());
await step(0.9);
const before = await S(() => window.__seedfall.clock());
check('bunk shows the sleep prompt', /Sleep/.test((await S(() => window.__seedfall.prompt())) ?? ''), await S(() => window.__seedfall.prompt()));
await press('f', 0.2);
for (let i = 0; i < 10; i++) { await step(0.3); await wait(600); }
const after = await S(() => window.__seedfall.clock());
check('sleeping advances ship time', before !== after, `${before} → ${after}`);
const saved = await S(() => !!localStorage.getItem('seedfall.save.v1'));
check('sleeping saves the game', saved);

// continue from save
await page.reload();
await page.waitForFunction(() => !document.getElementById('title')?.hidden, null, { timeout: 240000 });
check('Continue is offered after a save', await page.isVisible('#btn-continue'));
if (!(await page.isVisible('#btn-continue'))) { console.log('\n' + failed + ' check(s) failed'); await browser.close(); process.exit(1); }
await page.click('#btn-continue');
await step(0.5);
const cont = await S(() => window.__seedfall.info());
const fl = await S(() => window.__seedfall.flags());
check('Continue restores position near the bunk', cont.room === 'cabin', `room ${cont.room}`);
check('Continue restores progress flags', !!fl.lz1 && !!fl['obj:mail']);

check('no page errors', errors.length === 0, errors.slice(0, 5).join(' | '));
await browser.close();
console.log(failed ? `\n${failed} check(s) failed` : '\nall checks passed');
process.exit(failed ? 1 : 0);
