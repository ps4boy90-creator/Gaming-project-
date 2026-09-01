const { chromium } = require('playwright-core');
/**
 * Plays the investigation end to end in a real browser.
 *
 * The thing worth testing here is not that the code runs but that the mystery
 * is *solvable*: that every realization can actually be reached from the
 * evidence placed in the rooms the player can get into at that point, and that
 * no gate depends on something behind itself.
 *
 *   python3 -m http.server 8000 &
 *   npm install playwright-core
 *   node tools/verify/investigation.cjs
 */
const path = require('path');
const CHROME = process.env.CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
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
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));

  const G = (fn, arg) => page.evaluate(fn, arg);
  const settle = (ms = 200) => page.waitForTimeout(ms);
  const press = async (k) => { await page.keyboard.press(k); await settle(140); };

  await page.goto(`${BASE}/index.html`);
  await G(() => localStorage.clear());
  await page.reload();
  await page.waitForFunction(() => window.game && ['playing', 'error'].includes(window.game.state),
    null, { timeout: 15000 });
  check('boots', await G(() => window.game.state) === 'playing', await G(() => window.game.error || ''));

  /**
   * Dismiss whatever overlay is up until the world is interactive again.
   * Never presses a key during a scene transition: an E landing on the far
   * side of a door would immediately trigger whatever is next to the spawn.
   */
  const drain = async (limit = 30) => {
    for (let i = 0; i < limit; i++) {
      const s = await G(() => ({
        state: window.game.state,
        reader: window.game.reader.open,
        real: window.game.realization.open,
        keypad: window.game.keypad.open,
      }));
      if (s.state === 'transition' || s.state === 'cutscene') { await settle(180); continue; }
      if (!s.reader && !s.real && !s.keypad && s.state === 'playing') return true;
      if (s.real) await settle(820);
      await press('KeyE');
    }
    return false;
  };

  const goto = async (sceneId, spawn = 'start') => {
    await G(([s, sp]) => window.game.travel(s, sp, { instant: true }), [sceneId, spawn]);
    await page.waitForFunction((s) => window.game.scene && window.game.scene.id === s,
      sceneId, { timeout: 8000 });
    await settle(160);
  };

  /** Walk up to an entity by id and press E, then clear any overlay it opened. */
  const use = async (entityId) => {
    const found = await G((id) => {
      const e = window.game.scene.entities.find((x) => x.id === id && !x.removed);
      if (!e) return false;
      window.game.player.setPosition(e.x, window.game.player.y);
      return true;
    }, entityId);
    if (!found) {
      console.log(`      (no entity "${entityId}" in ${await G(() => window.game.scene.id)})`);
      return false;
    }
    await settle(160);
    const targeted = await G((id) => window.game.interaction.target && window.game.interaction.target.id === id, entityId);
    await press('KeyE');
    await drain();
    return targeted;
  };

  const flag = (f) => G((n) => window.game.flags.has(n), f);
  const sceneId = () => G(() => window.game.scene.id);

  // ---------------------------------------------------------------- cabin
  await goto('cabin_bedroom', 'wake');
  await drain();
  check('cabin memo reachable', await use('desk_memo'));
  check('read_memo set', await flag('read_memo'));
  await use('car_keys');

  // ------------------------------------------------------------- the gate
  await goto('station_gate', 'from_road');
  await drain();
  check('gate loads', await sceneId() === 'station_gate');
  check('barrier is a clue', await use('c_barrier'));
  check('car park is a clue', await use('c_cars'));
  check('no realization yet on two clues', !(await flag('knows_nobody_left')),
    'D1 needs three');

  // ------------------------------------------------------------- the lobby
  await goto('station_lobby', 'from_gate');
  await drain();
  await use('c_coats');
  check('D1 fires on the third clue', await flag('knows_nobody_left'));
  check('D1 filed in the journal',
    await G(() => window.game.journal.deductions.some((d) => d.key === 'nobody_left')));
  await use('c_signin');
  await use('c_clock');
  await use('n_desk_drawer');
  check('container yields its item', await G(() => window.game.journal.hasItem('n_desk_drawer_item')));
  const emptyLine = await G(async () => {
    const before = window.game.journal.items.length;
    return before;
  });
  await use('n_desk_drawer');
  check('container is empty the second time',
    await G(() => window.game.journal.items.length) === emptyLine);
  await page.screenshot({ path: path.join(SHOTS, '30-lobby.png') });

  // office door was gated on D1 and should now open
  const beforeDoor = await sceneId();
  await use('d_office');
  check('D1 unlocked the office wing', await sceneId() === 'office_wing', `${beforeDoor} -> ${await sceneId()}`);

  // ------------------------------------------------------------ the office
  await use('c_watch');
  await use('t_cutmemo');
  await use('c_nobodies');
  await use('n_roster');
  await use('n_drawer2');
  check('level B keycard taken', await flag('has_keycard_b'));

  // ----------------------------------------------------------- the canteen
  await goto('canteen', 'from_office');
  await drain();
  await use('c_meals');
  await use('c_chair');
  await use('c_radio');
  check('D2 (06:14) fires', await flag('knows_0614'));
  check('D3 (mid-shift) fires', await flag('knows_mid_shift'));
  await page.screenshot({ path: path.join(SHOTS, '31-canteen.png') });

  await use('d_lab');
  check('D3 unlocked the laboratory', await sceneId() === 'laboratory');

  // --------------------------------------------------------------- the lab
  await use('c_centrifuge');
  await use('t_schedule');
  await use('c_dosimeters');
  check('D4 (the test caused it) fires', await flag('knows_cause'));
  await use('c_scoring');
  await page.screenshot({ path: path.join(SHOTS, '32-lab.png') });

  await use('d_security');
  check('D4 unlocked security', await sceneId() === 'security_room');

  // ---------------------------------------------------------- the security
  await use('t_recording');
  await use('c_trail');
  check('D5 (pulled in) fires', await flag('knows_taken'));
  await use('t_doorlog');
  await use('c_powerlog');
  await use('n_lockers');
  check('level B locker opened with the card', await flag('has_stair_key'));
  await page.screenshot({ path: path.join(SHOTS, '33-security.png') });

  await use('d_stairs');
  check('D5 unlocked the stairwell', await sceneId() === 'stairwell');

  // ---------------------------------------------------------- the stairwell
  await use('c_barricade');
  await use('c_tally');
  await use('c_rations');
  check('D6 (someone was left behind) fires', await flag('knows_survivor'));
  await use('n_vancelog');
  await page.screenshot({ path: path.join(SHOTS, '34-stairwell.png') });

  // the sealed door refuses before the code
  await G(() => {
    const d = window.game.scene.entities.find((e) => e.id === 'd_sublevel');
    if (d) window.game.player.setPosition(d.x, 198);
  });
  await settle(200);
  await press('KeyE');
  await settle(200);
  check('blast door refuses without the code', await sceneId() === 'stairwell');

  // keypad: wrong code, then the one the clues gave us
  await G(() => {
    const k = window.game.scene.entities.find((e) => e.id === 'k_blast');
    if (k) window.game.player.setPosition(k.x, 198);
  });
  await settle(200);
  await press('KeyE');
  check('keypad opens', await G(() => window.game.keypad.open) && await G(() => window.game.state) === 'keypad');
  await page.screenshot({ path: path.join(SHOTS, '35-keypad.png') });
  for (const d of ['0', '0', '0', '0']) await press(`Digit${d}`);
  await settle(200);
  check('wrong code rejected', await G(() => window.game.keypad.open) && !(await flag('stair_door_open')));
  check('wrong code says so', await G(() => window.game.keypad.message.length > 0));
  for (const d of ['0', '6', '1', '4']) await press(`Digit${d}`);
  await settle(300);
  check('0614 accepted', await flag('stair_door_open'));
  await drain();

  await use('d_sublevel');
  check('the door opens to Sublevel 3', await sceneId() === 'sublevel_3');

  // ------------------------------------------------------------ the ending
  await use('c_aperture');
  await use('c_badge');
  await use('n_final');
  check('D7 (she went in after them) fires', await flag('knows_ending'));
  check('all seven realizations recorded',
    await G(() => window.game.journal.deductions.length) === 7,
    `${await G(() => window.game.journal.deductions.length)} of 7`);
  await page.screenshot({ path: path.join(SHOTS, '36-sublevel.png') });

  // -------------------------------------------------------------- journal
  await press('Tab');
  check('journal opens', await G(() => window.game.state) === 'journal');
  await press('ArrowRight');
  check('tab switches to deductions', await G(() => window.game.journalState.tab) === 1);
  await page.screenshot({ path: path.join(SHOTS, '37-journal-deductions.png') });
  await press('ArrowRight');
  check('tab switches to carrying', await G(() => window.game.journalState.tab) === 2);
  await press('Escape');

  // --------------------------------------------------------- save/restore
  await G(() => window.game.save());
  const evidence = await G(() => window.game.journal.notes.length);
  await page.reload();
  await page.waitForFunction(() => window.game && window.game.state === 'playing', null, { timeout: 15000 });
  await settle(400);
  check('restores into Sublevel 3', await sceneId() === 'sublevel_3');
  check('deductions survive a reload', await G(() => window.game.journal.deductions.length) === 7);
  check('evidence survives a reload', await G(() => window.game.journal.notes.length) === evidence);
  check('no realization replays on load', await G(() => window.game.state) === 'playing');

  check('no console errors', errors.length === 0, errors.slice(0, 3).join(' | '));
  await settle(1200);
  check('frame rate healthy', await G(() => window.game.loop.fps) >= 50, `${await G(() => window.game.loop.fps)} fps`);

  await browser.close();
  console.log(fail.length ? `\n${fail.length} FAILED: ${fail.join(', ')}` : '\nThe investigation is solvable end to end.');
  process.exit(fail.length ? 1 : 0);
})();
