import { FLOORS, NEED_WEIGHT, NEEDS, OBJ, R, type NeedId } from '../data/defs';
import { clamp01, rng } from '../core/util';
import { PASS_PRISONER, PASS_STAFF, objLocalToWorld, type Room, type WorldObject } from '../world/world';
import type { Agent, PMode, Step } from './agent';
import { ENTRY_X, ENTRY_Y, type Sim } from './sim';
import { useSpot } from './spots';

const N: Record<NeedId, number> = Object.fromEntries(NEEDS.map((n, i) => [n, i])) as Record<NeedId, number>;
const STAFF_ROOMS = new Set<number>([R.reception, R.security, R.warden, R.staffroom, R.storage, R.psych, R.armoury, R.kitchen]);
const ESCORTED: PMode[] = ['intake', 'solitary', 'punished', 'released', 'infirm', 'cuffed'];

export function setMode(a: Agent, mode: PMode) {
  a.p!.mode = mode;
  a.pass = ESCORTED.includes(mode) ? PASS_STAFF : PASS_PRISONER;
}

function ownRoom(sim: Sim, a: Agent): Room | undefined {
  const bed = a.p!.bedId ? sim.world.objects.get(a.p!.bedId) : undefined;
  return bed ? sim.world.roomAtTile(sim.world.idx(bed.x, bed.y)) : undefined;
}

/** may this inmate use an object in this room? */
function roomOk(sim: Sim, a: Agent, room: Room | undefined, own: Room | undefined): boolean {
  if (!room) return true;
  if (STAFF_ROOMS.has(room.type) || room.type === R.solitary || room.type === R.holding) return false;
  if (room.type === R.cell || room.type === R.dorm) return room === own;
  return true;
}

/** nearest usable object of the given types */
function findObj(sim: Sim, a: Agent, types: string[], filter?: (o: WorldObject, room: Room | undefined) => boolean): WorldObject | null {
  const w = sim.world, own = ownRoom(sim, a);
  let best: WorldObject | null = null, bd = 1e9;
  for (const t of types) {
    for (const o of sim.objsOf(t)) {
      if (!sim.freeSlots(o)) continue;
      const room = w.roomAtTile(w.idx(o.x, o.y));
      if (filter ? !filter(o, room) : !roomOk(sim, a, room, own)) continue;
      const d = Math.abs(o.x - a.x) + Math.abs(o.y - a.z) + rng.next() * 3;
      if (d < bd) {
        bd = d;
        best = o;
      }
    }
  }
  return best;
}

/** reserve an object and build walk + use steps */
function useObj(sim: Sim, a: Agent, o: WorldObject, step: Partial<Step>, status: string): boolean {
  const slot = sim.reserve(a, o);
  if (slot < 0) return false;
  const s = useSpot(sim.world, o, slot);
  sim.setPlan(a, [
    { t: 'walk', tile: s.tile },
    { t: 'do', px: s.px, pz: s.pz, y: s.y, yaw: s.yaw, pose: s.pose, status, ...step },
  ], status);
  return true;
}

function randomTile(sim: Sim, room: Room, pass: number): number {
  const w = sim.world;
  for (let i = 0; i < 12; i++) {
    const t = rng.pick(room.tiles);
    if (w.cost[pass][t] === 2) return t;
  }
  return rng.pick(room.tiles);
}

function nearestRoom(a: Agent, rooms: Room[]): Room | undefined {
  let best: Room | undefined, bd = 1e9;
  for (const r of rooms) {
    const d = Math.abs(r.cx - a.x) + Math.abs(r.cy - a.z);
    if (d < bd) {
      bd = d;
      best = r;
    }
  }
  return best;
}

// ====================================================================== think
export function thinkPrisoner(sim: Sim, a: Agent) {
  const p = a.p!;
  switch (p.mode) {
    case 'intake': return intake(sim, a);
    case 'cuffed':
      sim.beginPunishment(a);
      a.pass = PASS_STAFF;
      return;
    case 'solitary':
    case 'punished': return punishment(sim, a);
    case 'down': return downed(sim, a);
    case 'infirm': return infirm(sim, a);
    case 'escaping': return escaping(sim, a);
    case 'released': return leave(sim, a);
    case 'riot': return rioting(sim, a);
    case 'fight': setMode(a, 'normal');
  }
  normal(sim, a);
}

function intake(sim: Sim, a: Agent) {
  const p = a.p!, w = sim.world;
  a.pass = PASS_STAFF;
  if (!p.processed) {
    const rec = nearestRoom(a, w.validRoomsOf(R.reception));
    if (rec) {
      const desk = rec.objects.map((id) => w.objects.get(id)!).find((o) => o.type === 'office_desk');
      let tile = randomTile(sim, rec, PASS_STAFF);
      if (desk) {
        const [px, pz] = objLocalToWorld(desk, rng.range(-0.8, 0.8), 1.6);
        const tx = Math.floor(px), tz = Math.floor(pz);
        if (w.inb(tx, tz) && w.cost[PASS_STAFF][w.idx(tx, tz)] === 2) tile = w.idx(tx, tz);
      }
      sim.setPlan(a, [
        { t: 'walk', tile, status: 'Arriving' },
        { t: 'do', dur: 10, pose: 'stand', status: 'Being processed', done: () => { p.processed = true; } },
      ]);
      return;
    }
    p.processed = true;
  }
  sim.assignBed(a);
  setMode(a, 'normal');
  if (p.bedId) {
    const bed = w.objects.get(p.bedId)!;
    a.pass = PASS_STAFF; // escorted to the cell the first time
    sim.setPlan(a, [{ t: 'walk', tile: w.idx(bed.x, bed.y), status: 'Being taken to a cell' }, { t: 'do', dur: 2, done: () => { a.pass = PASS_PRISONER; } }]);
  }
}

function leave(sim: Sim, a: Agent) {
  const p = a.p!;
  sim.setPlan(a, [
    { t: 'walk', tile: sim.world.idx(ENTRY_X, ENTRY_Y), hold: true, status: 'Released: walking free' },
    {
      t: 'do', dur: 0.2, hold: true,
      done: () => {
        a.dead = true;
        sim.stats.released++;
        const bonus = Math.round(150 + 650 * p.reform);
        sim.earn(bonus, 'Release bonus');
        sim.toast(`${a.name} served their sentence and was released${p.reform > 0.6 ? ' a reformed man' : ''}. (+$${bonus})`, 'good');
      },
    },
  ]);
}

function punishment(sim: Sim, a: Agent) {
  const p = a.p!, w = sim.world;
  let room: Room | undefined;
  if (p.mode === 'solitary') {
    for (const [tile, aid] of sim.solitaryOcc) if (aid === a.id) room = w.roomAtTile(tile);
    if (room && room.type !== R.solitary) room = undefined;
  } else room = ownRoom(sim, a);
  if (!room || sim.time >= p.modeUntil) {
    for (const [rid, aid] of sim.solitaryOcc) if (aid === a.id) sim.solitaryOcc.delete(rid);
    p.anger *= 0.65;
    setMode(a, 'normal');
    return;
  }
  const inside = sim.roomOf(a) === room;
  const steps: Step[] = [];
  if (!inside) steps.push({ t: 'walk', tile: randomTile(sim, room, PASS_STAFF), hold: true, status: p.mode === 'solitary' ? 'Being taken to solitary' : 'Being taken to their cell' });
  steps.push({
    t: 'do', hold: true, pose: rng.chance(0.5) ? 'sit' : 'stand', y: 0, icon: 'cuffs',
    status: p.mode === 'solitary' ? 'In solitary' : 'Confined to cell',
    until: () => sim.time >= p.modeUntil,
    tick: () => {
      // meals are brought to the cell
      if (p.needs[N.hunger] > 0.3) p.needs[N.hunger] = 0.3;
      if (p.needs[N.bladder] > 0.6) p.needs[N.bladder] = 0.2;
    },
  });
  sim.setPlan(a, steps);
}

function downed(sim: Sim, a: Agent) {
  const p = a.p!;
  a.pose = 'down';
  sim.setPlan(a, [{
    t: 'do', hold: true, pose: 'down', icon: 'medical', status: 'Unconscious',
    until: () => p.health >= 0.32,
    tick: (dt) => {
      const doc = sim.nearestStaff(a, 'doctor', 1.8);
      p.health = Math.min(1, p.health + dt * (doc ? 0.035 : 0.0035));
    },
    done: () => { a.pose = 'stand'; setMode(a, 'infirm'); },
  }]);
}

function infirm(sim: Sim, a: Agent) {
  const p = a.p!, w = sim.world;
  if (p.health >= 0.95 || !sim.hasRoom(R.infirmary)) {
    setMode(a, 'normal');
    return;
  }
  const bed = findObj(sim, a, ['medical_bed'], (_o, room) => !!room && room.type === R.infirmary && room.valid);
  if (bed) {
    useObj(sim, a, bed, {
      icon: 'medical', hold: true,
      until: () => p.health >= 0.97,
      tick: (dt) => {
        const doc = sim.nearestStaff(a, 'doctor', 7);
        p.health = Math.min(1, p.health + dt * (doc ? 0.0085 : 0.0018));
        p.needs[N.sleep] = Math.max(0, p.needs[N.sleep] - dt * 0.002);
        if (p.needs[N.hunger] > 0.3) p.needs[N.hunger] = 0.3;
      },
      done: () => {
        if (!p.contraband && rng.chance(0.04)) p.contraband = 'drugs';
        setMode(a, 'normal');
      },
    }, 'In the infirmary');
    return;
  }
  const room = nearestRoom(a, w.validRoomsOf(R.infirmary))!;
  sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, room, PASS_STAFF) }, { t: 'do', dur: 8, icon: 'medical', status: 'Waiting for a medical bed' }]);
}

function escaping(sim: Sim, a: Agent) {
  const w = sim.world;
  let t = sim.tileOf(a);
  if (w.escapeDist[t] === 65535) {
    setMode(a, 'normal');
    a.p!.anger = clamp01(a.p!.anger + 0.1);
    return;
  }
  if (sim.towerSees(a)) {
    sim.toast(`A tower guard forced ${a.name} to surrender.`, 'good', a.x, a.z);
    sim.arrest(a, 12);
    return;
  }
  // follow the gradient to the nearest map edge
  let guard = 0;
  while (w.escapeDist[t] > 0 && guard++ < 400) {
    const x = t % w.w, y = Math.floor(t / w.w);
    let best = t, bd = w.escapeDist[t];
    for (const j of [x > 0 ? t - 1 : -1, x < w.w - 1 ? t + 1 : -1, y > 0 ? t - w.w : -1, y < w.h - 1 ? t + w.w : -1]) {
      if (j >= 0 && w.escapeDist[j] < bd) {
        bd = w.escapeDist[j];
        best = j;
      }
    }
    if (best === t) break;
    t = best;
  }
  sim.setPlan(a, [
    { t: 'walk', tile: t, run: true, status: 'ESCAPING!' },
    { t: 'do', dur: 0.1, done: () => sim.escaped(a) },
  ]);
  a.icon = 'escape';
}

function rioting(sim: Sim, a: Agent) {
  const p = a.p!;
  if (sim.inFight(a)) return;
  if (!sim.riot || (p.anger < 0.4 && rng.chance(0.2))) {
    setMode(a, 'normal');
    return;
  }
  let target: Agent | null = null, bd = 22;
  for (const s of sim.staff) {
    if (s.pose === 'down' || s.s!.mode === 'leave' || sim.inFight(s)) continue;
    const d = a.distTo(s);
    if (d < bd) {
      bd = d;
      target = s;
    }
  }
  if (target) {
    const t = target;
    sim.setPlan(a, [{ t: 'follow', target: t, range: 1.0, run: true, status: 'Rioting', abort: () => t.pose === 'down' || !!sim.inFight(t), done: () => sim.startFight(a, t) }]);
    a.icon = 'angry';
    return;
  }
  // nobody to fight: rampage around
  const rooms = [...sim.world.rooms.values()].filter((r) => !STAFF_ROOMS.has(r.type));
  if (rooms.length) {
    sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, rng.pick(rooms), PASS_PRISONER), run: true, status: 'Rioting' }, { t: 'do', dur: 3, pose: 'fight', icon: 'angry' }]);
  } else sim.setPlan(a, [{ t: 'do', dur: 4, pose: 'fight', icon: 'angry', status: 'Rioting' }]);
}

function normal(sim: Sim, a: Agent) {
  const p = a.p!;
  a.pass = PASS_PRISONER;
  const act = sim.activity;
  if (p.served >= p.sentence && sim.hour >= 8 && sim.hour < 18 && !sim.lockdown && !sim.riot) {
    setMode(a, 'released');
    return leave(sim, a);
  }
  if (p.health < 0.55 && sim.hasRoom(R.infirmary)) {
    setMode(a, 'infirm');
    return infirm(sim, a);
  }
  if (!p.bedId) sim.assignBed(a);
  const locked = act === 'sleep' || act === 'lockup';
  if (p.needs[N.bladder] > 0.7 && useToilet(sim, a, locked)) return;
  // anyone who missed a meal goes looking for food as soon as they are allowed out
  if (!locked && act !== 'eat' && p.needs[N.hunger] > 0.78 && sim.meals >= 1 && doEat(sim, a)) return;
  switch (act) {
    case 'sleep': return goSleep(sim, a);
    case 'lockup': return goCell(sim, a);
    case 'shower':
      if (!p.showered && p.needs[N.hygiene] > 0.15 && doShower(sim, a)) return;
      return freeTime(sim, a);
    case 'eat':
      if (!p.ate && p.needs[N.hunger] > 0.15 && doEat(sim, a)) return;
      return freeTime(sim, a);
    case 'yard':
      if (doYard(sim, a)) return;
      return freeTime(sim, a);
    case 'work':
      if (doWork(sim, a)) return;
      return freeTime(sim, a);
    default:
      return freeTime(sim, a);
  }
}

function useToilet(sim: Sim, a: Agent, locked: boolean): boolean {
  const p = a.p!, own = ownRoom(sim, a);
  const o = findObj(sim, a, ['toilet'], (_o, room) => (locked ? !!room && room === own : roomOk(sim, a, room, own) || (!!room && room.type === R.holding)));
  if (o) return useObj(sim, a, o, { dur: 4, icon: 'toilet', done: () => { p.needs[N.bladder] = 0; } }, 'Using the toilet');
  if (p.needs[N.bladder] > 0.96) {
    p.needs[N.bladder] = 0.25;
    p.needs[N.hygiene] = clamp01(p.needs[N.hygiene] + 0.4);
    p.anger = clamp01(p.anger + 0.06);
    const r = sim.roomOf(a);
    if (r) r.dirt = Math.min(1, r.dirt + 0.25);
    sim.warn('notoilet', 'Inmates cannot reach a toilet. Every cell needs one.', 300, 'warn', a.x, a.z);
  }
  return false;
}

function goSleep(sim: Sim, a: Agent) {
  const p = a.p!, w = sim.world;
  const bed = p.bedId ? w.objects.get(p.bedId) : undefined;
  const sleepStep = (rate: number): Partial<Step> => ({
    until: () => sim.activity !== 'sleep',
    tick: (dt) => {
      p.needs[N.sleep] = Math.max(0, p.needs[N.sleep] - dt * rate);
      if (p.contraband === 'tools') {
        p.dig += dt / 1150;
        if (p.dig >= 1) sim.escaped(a, 'tunnelled out of their cell during the night');
      }
    },
  });
  if (bed) {
    const s = useSpot(w, bed, p.bedSlot);
    sim.setPlan(a, [
      { t: 'walk', tile: s.tile, status: 'Going to bed' },
      { t: 'do', px: s.px, pz: s.pz, y: s.y, yaw: s.yaw, pose: 'lie', status: 'Sleeping', ...sleepStep(0.0024) },
    ]);
    return;
  }
  // no bed: holding cell floor, or wherever they are
  const hold = nearestRoom(a, w.validRoomsOf(R.holding));
  const steps: Step[] = [];
  if (hold && sim.roomOf(a) !== hold) steps.push({ t: 'walk', tile: randomTile(sim, hold, PASS_PRISONER) });
  steps.push({ t: 'do', pose: 'down', status: 'Sleeping on the floor', ...sleepStep(0.0014) });
  sim.setPlan(a, steps);
  sim.warn('nobed', 'Some inmates have no bed and are sleeping on the floor.', 600);
}

function goCell(sim: Sim, a: Agent) {
  const p = a.p!, w = sim.world;
  const room = ownRoom(sim, a) ?? nearestRoom(a, w.validRoomsOf(R.holding));
  if (!room) {
    sim.setPlan(a, [{ t: 'do', dur: 10, status: 'Nowhere to be locked up' }]);
    return;
  }
  const steps: Step[] = [];
  const inside = sim.roomOf(a) === room;
  const bed = p.bedId ? w.objects.get(p.bedId) : undefined;
  if (bed && rng.chance(0.55)) {
    const s = useSpot(w, bed, p.bedSlot);
    steps.push({ t: 'walk', tile: s.tile });
    steps.push({
      t: 'do', px: s.px, pz: s.pz, y: s.y, yaw: s.yaw, pose: 'lie', dur: rng.range(15, 30), status: 'Resting in cell',
      tick: (dt) => { p.needs[N.sleep] = Math.max(0, p.needs[N.sleep] - dt * 0.001); },
    });
  } else {
    if (!inside || rng.chance(0.6)) steps.push({ t: 'walk', tile: randomTile(sim, room, PASS_PRISONER) });
    steps.push({ t: 'do', dur: rng.range(6, 16), status: sim.time < sim.shakedownUntil ? 'Cell being searched' : 'Locked up' });
  }
  sim.setPlan(a, steps);
}

function doShower(sim: Sim, a: Agent): boolean {
  const p = a.p!;
  const o = findObj(sim, a, ['shower']);
  if (!o) {
    if (!sim.objsOf('shower').length) sim.warn('noshower', 'There are no showers. Inmates are getting filthy.', 700);
    return false;
  }
  return useObj(sim, a, o, { dur: 9, icon: 'shower', done: () => { p.needs[N.hygiene] = 0; p.showered = true; } }, 'Showering');
}

function doEat(sim: Sim, a: Agent): boolean {
  const p = a.p!, w = sim.world;
  const canteen = nearestRoom(a, w.validRoomsOf(R.canteen));
  if (!canteen) {
    sim.warn('nocanteen', 'Inmates are hungry but there is no working canteen (serving counter + benches).', 400);
    return false;
  }
  const counter = findObj(sim, a, ['serving_counter'], (_o, room) => room === canteen);
  if (!counter) {
    // queue up nearby
    sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, canteen, PASS_PRISONER) }, { t: 'do', dur: 3, icon: 'hungry', status: 'Queueing for food' }]);
    return true;
  }
  let got = false;
  return useObj(sim, a, counter, {
    dur: 22, icon: 'hungry',
    until: () => {
      if (a.stepT < 1.2) return false;
      if (sim.meals >= 1) {
        sim.meals -= 1;
        got = true;
        return true;
      }
      return false;
    },
    done: () => {
      if (!got) {
        p.ate = true;
        p.anger = clamp01(p.anger + 0.1);
        sim.warn('nofood', 'The kitchen ran out of food! Hire cooks and add cookers.', 240, 'bad', a.x, a.z);
        return;
      }
      const eat: Partial<Step> = {
        dur: 13, status: 'Eating',
        done: () => {
          p.needs[N.hunger] = Math.max(0, p.needs[N.hunger] - 0.75);
          p.ate = true;
          canteen.dirt = Math.min(1, canteen.dirt + 0.004);
        },
      };
      const seat = findObj(sim, a, ['bench', 'chair'], (_o, room) => room === canteen);
      if (seat) useObj(sim, a, seat, eat, 'Eating');
      else sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, canteen, PASS_PRISONER) }, { t: 'do', pose: 'stand', ...eat }], 'Eating standing up');
    },
  }, 'Collecting a meal');
}

function wander(sim: Sim, a: Agent, room: Room, status: string, run = false) {
  sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, room, PASS_PRISONER), run }, { t: 'do', dur: rng.range(2, 7), status }], status);
}

function exercise(sim: Sim, a: Agent, yardOnly: boolean): boolean {
  const p = a.p!;
  const o = findObj(sim, a, ['weight_bench', 'punching_bag', 'basketball_hoop'], yardOnly ? (_o, room) => !!room && room.type === R.yard : undefined);
  if (!o) return false;
  return useObj(sim, a, o, {
    dur: rng.range(14, 24),
    tick: (dt) => {
      p.needs[N.exercise] = Math.max(0, p.needs[N.exercise] - dt * 0.03);
      p.needs[N.recreation] = Math.max(0, p.needs[N.recreation] - dt * 0.006);
    },
    done: () => { p.anger = Math.max(0, p.anger - 0.03); },
  }, o.type === 'basketball_hoop' ? 'Shooting hoops' : o.type === 'punching_bag' ? 'Hitting the bag' : 'Lifting weights');
}

function phoneHome(sim: Sim, a: Agent): boolean {
  const p = a.p!;
  const o = findObj(sim, a, ['phone']);
  if (!o) return false;
  return useObj(sim, a, o, { dur: 12, icon: 'family', tick: (dt) => { p.needs[N.family] = Math.max(0, p.needs[N.family] - dt * 0.045); } }, 'Calling home');
}

function doYard(sim: Sim, a: Agent): boolean {
  const p = a.p!;
  const yard = nearestRoom(a, sim.world.validRoomsOf(R.yard));
  if (!yard) {
    sim.warn('noyard', 'Yard time is scheduled but there is no Yard.', 900);
    return false;
  }
  if (p.needs[N.exercise] > 0.25 && rng.chance(0.7) && exercise(sim, a, true)) return true;
  if (p.needs[N.family] > 0.45 && rng.chance(0.5) && phoneHome(sim, a)) return true;
  if (rng.chance(0.25)) {
    const b = findObj(sim, a, ['outdoor_bench', 'bench'], (_o, room) => room === yard);
    if (b && useObj(sim, a, b, { dur: rng.range(8, 18) }, 'Sitting in the yard')) return true;
  }
  const jog = p.needs[N.exercise] > 0.4 && rng.chance(0.5);
  sim.setPlan(a, [
    { t: 'walk', tile: randomTile(sim, yard, PASS_PRISONER), run: jog },
    { t: 'do', dur: jog ? 0.3 : rng.range(1, 5), done: () => { if (jog) p.needs[N.exercise] = Math.max(0, p.needs[N.exercise] - 0.05); } },
  ], jog ? 'Jogging' : 'Walking the yard');
  return true;
}

function doWork(sim: Sim, a: Agent): boolean {
  const p = a.p!;
  const chunk = rng.range(28, 45);
  const maybeContraband = (chance: number, items: ('weapon' | 'tools')[]) => {
    if (!p.contraband && rng.chance(chance * (0.6 + p.sec * 0.4))) p.contraband = rng.pick(items);
  };
  // education first for those who have not finished
  if (p.edu < 1 && sim.counts.teachers > 0) {
    const desk = findObj(sim, a, ['school_desk'], (_o, room) => !!room && room.type === R.classroom && room.valid);
    if (desk && useObj(sim, a, desk, {
      dur: chunk, icon: 'learn',
      tick: (dt) => {
        p.edu = Math.min(1, p.edu + dt / 700);
        p.needs[N.recreation] = Math.max(0, p.needs[N.recreation] - dt * 0.004);
      },
    }, 'Studying')) return true;
  }
  const options: [string[], number, string, (dt: number) => void, () => void][] = [
    [['workshop_saw', 'workshop_press'], R.workshop, 'Working in the workshop', (dt) => sim.earn(dt * 0.85, 'Workshop'), () => maybeContraband(0.05, ['tools', 'weapon'])],
    [['kitchen_counter'], R.kitchen, 'Working in the kitchen', (dt) => { sim.meals = Math.min(sim.mealCap(), sim.meals + dt * 0.1); }, () => maybeContraband(0.03, ['weapon'])],
    [['laundry_machine'], R.laundry, 'Working in the laundry', (dt) => { sim.laundry = Math.min(1, sim.laundry + dt * 0.012); }, () => {}],
  ];
  // shuffle so jobs fill evenly
  options.sort(() => rng.next() - 0.5);
  for (const [types, roomType, status, tick, done] of options) {
    const o = findObj(sim, a, types, (_o, room) => !!room && room.type === roomType && room.valid);
    if (o && useObj(sim, a, o, {
      dur: chunk, icon: 'work',
      tick: (dt) => {
        tick(dt);
        p.needs[N.recreation] = Math.max(0, p.needs[N.recreation] - dt * 0.003);
      },
      done,
    }, status)) return true;
  }
  return false;
}

function freeTime(sim: Sim, a: Agent) {
  const p = a.p!, w = sim.world, n = p.needs;
  type Opt = [number, () => boolean];
  const opts: Opt[] = [];
  opts.push([n[N.recreation] * 1.0 + 0.05, () => {
    const o = findObj(sim, a, ['tv', 'pool_table', 'sofa', 'bookshelf']);
    if (!o) return false;
    const label = o.type === 'tv' ? 'Watching TV' : o.type === 'pool_table' ? 'Playing pool' : o.type === 'bookshelf' ? 'Reading' : 'Relaxing';
    return useObj(sim, a, o, {
      dur: rng.range(15, 30),
      tick: (dt) => {
        n[N.recreation] = Math.max(0, n[N.recreation] - dt * 0.022);
        if (o.type === 'bookshelf') p.edu = Math.min(1, p.edu + dt / 4000);
      },
    }, label);
  }]);
  opts.push([n[N.family] * 1.1, () => {
    if (sim.hour >= 9 && sim.hour < 18 && n[N.family] > 0.35) {
      const t = findObj(sim, a, ['visit_table'], (_o, room) => !!room && room.type === R.visitation && room.valid);
      if (t) {
        let visitor: Agent | null = null;
        const ok = useObj(sim, a, t, {
          dur: 75, icon: 'family',
          tick: (dt) => {
            if (!visitor) visitor = sim.spawnVisitor(a.id, t);
            if (visitor.pose === 'sit') n[N.family] = Math.max(0, n[N.family] - dt * 0.022);
          },
          until: () => !!visitor && (visitor.dead || visitor.visitFor === 0),
          done: () => {
            if (visitor) visitor.visitFor = 0;
            if (!p.contraband && rng.chance(0.07 + p.sec * 0.03)) p.contraband = rng.pick(['drugs', 'phone', 'weapon'] as const);
            p.anger = Math.max(0, p.anger - 0.08);
          },
        }, 'Having a visit');
        if (ok) return true;
      }
    }
    return phoneHome(sim, a);
  }]);
  opts.push([n[N.exercise] * 0.9, () => exercise(sim, a, false)]);
  if (n[N.hygiene] > 0.55) opts.push([n[N.hygiene] * 0.9, () => doShower(sim, a)]);
  if (n[N.sleep] > 0.7 && p.bedId) opts.push([n[N.sleep] * 0.9, () => {
    const bed = w.objects.get(p.bedId)!;
    const s = useSpot(w, bed, p.bedSlot);
    sim.setPlan(a, [{ t: 'walk', tile: s.tile }, {
      t: 'do', px: s.px, pz: s.pz, y: s.y, yaw: s.yaw, pose: 'lie', dur: 45, icon: 'sleep', status: 'Napping',
      tick: (dt) => { n[N.sleep] = Math.max(0, n[N.sleep] - dt * 0.002); },
    }]);
    return true;
  }]);
  if (sim.counts.chaplains > 0) opts.push([p.anger * 0.7 + n[N.recreation] * 0.3, () => {
    const o = findObj(sim, a, ['pew'], (_o, room) => !!room && room.type === R.chapel && room.valid);
    return !!o && useObj(sim, a, o, {
      dur: rng.range(20, 35), icon: 'calm',
      tick: (dt) => {
        p.anger = Math.max(0, p.anger - dt * 0.006);
        n[N.recreation] = Math.max(0, n[N.recreation] - dt * 0.008);
      },
    }, 'At chapel');
  }]);
  if (sim.counts.psychs > 0 && p.anger > 0.4) opts.push([p.anger * 1.2, () => {
    const o = findObj(sim, a, ['sofa', 'chair'], (_o, room) => !!room && room.type === R.psych && room.valid);
    return !!o && useObj(sim, a, o, { dur: 30, icon: 'calm', tick: (dt) => { p.anger = Math.max(0, p.anger - dt * 0.013); } }, 'In therapy');
  }]);
  const yard = nearestRoom(a, w.validRoomsOf(R.yard));
  if (yard) opts.push([n[N.freedom] * 0.8, () => { wander(sim, a, yard, 'Getting some air'); return true; }]);

  opts.sort((x, y) => y[0] - x[0]);
  for (const [score, fn] of opts) {
    if (score < 0.18) break;
    if (fn()) return;
  }
  // nothing to do: hang around a common area, the yard, or the cell
  const hang = nearestRoom(a, [...w.validRoomsOf(R.common), ...w.validRoomsOf(R.canteen)]) ?? yard ?? ownRoom(sim, a);
  if (hang) wander(sim, a, hang, 'Hanging around');
  else sim.setPlan(a, [{ t: 'do', dur: 5, status: 'Idle' }]);
}

// ====================================================================== per-minute
export function prisonerMinute(sim: Sim, a: Agent) {
  const p = a.p!, n = p.needs, w = sim.world;
  if (a.dead) return;
  const act = sim.activity;
  const sleeping = a.pose === 'lie' && act === 'sleep';
  const tile = sim.tileOf(a);
  const outdoors = FLOORS[w.floor[tile]].outdoor;
  n[N.hunger] += 0.047 / 60;
  if (!sleeping) n[N.sleep] += 0.04 / 60;
  n[N.bladder] += (sleeping ? 0.03 : 0.11) / 60;
  n[N.hygiene] += (0.04 / 60) * (sim.laundry > 0.25 ? 0.65 : 1);
  n[N.recreation] += (sleeping ? 0.008 : 0.045) / 60;
  n[N.exercise] += 0.03 / 60;
  n[N.family] += 0.018 / 60;
  if (p.mode === 'solitary') n[N.freedom] += 0.1 / 60;
  else if (outdoors) n[N.freedom] -= 0.32 / 60;
  else if (act === 'lockup') n[N.freedom] += 0.06 / 60;
  else n[N.freedom] += (sleeping ? 0.004 : 0.024) / 60;
  n[N.safety] += (sim.danger - n[N.safety]) * 0.02;
  if (p.contraband === 'phone') n[N.family] -= 0.03 / 60;
  for (let i = 0; i < n.length; i++) n[i] = clamp01(n[i]);

  // anger follows stress
  let stress = 0;
  for (let i = 0; i < NEEDS.length; i++) stress += NEED_WEIGHT[NEEDS[i]] * Math.max(0, n[i] - 0.5) * 2;
  stress /= 3.2;
  if (!p.bedId && p.mode === 'normal') stress += 0.25;
  const room = w.roomAtTile(tile);
  if (room && room.dirt > 0.7) stress += 0.08;
  if (sim.lockdown) stress += 0.12;
  if (p.mode === 'solitary') stress += 0.08;
  if (sim.counts.wardenIn) stress -= 0.04;
  stress = Math.max(0, stress) * (0.7 + 0.3 * p.temper);
  p.anger = clamp01(p.anger + (stress - p.anger) * (stress > p.anger ? 0.011 : 0.02));
  if (p.contraband === 'drugs') {
    p.anger = Math.max(0, p.anger - 0.002);
    if (rng.chance(0.0005)) {
      p.health = Math.max(0.05, p.health - 0.55);
      p.contraband = '';
      sim.toast(`${a.name} overdosed on smuggled drugs.`, 'bad', a.x, a.z);
      if (p.mode === 'normal' && !a.busy) sim.knockDown(a);
    }
  }
  // health
  if (n[N.hunger] >= 0.99) {
    p.health -= 0.0007;
    sim.warn('starving', 'Inmates are starving!', 300, 'bad', a.x, a.z);
  } else if (p.health < 1 && p.mode !== 'down') p.health = Math.min(1, p.health + 0.0003);
  if (p.health <= 0) {
    sim.kill(a, 'has died');
    return;
  }
  p.served += 1 / 1440;
  p.reform = clamp01(p.edu * 0.5 + 0.5 * (1 - Math.min(1, p.misconduct / 5)) * Math.min(1, p.served / Math.max(1, p.sentence * 0.5)));

  // status icon when idle-ish
  if (!a.icon && p.mode === 'normal') {
    a.icon = p.anger > 0.75 ? 'angry' : n[N.hunger] > 0.85 ? 'hungry' : null;
  } else if (a.icon === 'angry' && p.anger < 0.7 && p.mode === 'normal') a.icon = null;
  else if (a.icon === 'hungry' && n[N.hunger] < 0.8) a.icon = null;

  if (sim.time >= p.nextRoll) {
    p.nextRoll = sim.time + 8 + rng.next() * 6;
    misbehave(sim, a, tile, sleeping);
  }
}

function misbehave(sim: Sim, a: Agent, tile: number, sleeping: boolean) {
  const p = a.p!, w = sim.world;
  if (p.mode !== 'normal' || a.busy || sleeping) return;
  const act = sim.activity;
  const guardNear = sim.nearestStaff(a, 'guard', 6);
  // make a run for it
  if (w.escapeDist[tile] !== 65535 && act !== 'sleep' && !guardNear) {
    const want = 0.011 * (1 + p.sec) * (0.4 + p.needs[N.freedom] + p.anger);
    if (rng.chance(want)) {
      setMode(a, 'escaping');
      sim.clearPlan(a);
      sim.warn('run', `${a.name} is making a run for it!`, 15, 'bad', a.x, a.z);
      return;
    }
  }
  // short tempers flare up now and then even in a well-run prison
  const spark = 0.0006 * p.temper * p.temper * (1 + p.sec);
  if (p.anger > 0.6 || rng.chance(spark)) {
    let pf = p.anger > 0.6 ? (p.anger - 0.55) * p.temper * 0.16 : 1;
    if (guardNear) pf *= 0.35;
    if (sim.counts.cctv) pf *= 0.8;
    if (rng.chance(pf)) {
      let victim: Agent | null = null, bd = 4.5;
      for (const o of sim.prisoners) {
        if (o === a || o.p!.mode !== 'normal' || o.busy || o.pose === 'lie') continue;
        const d = a.distTo(o);
        if (d < bd) {
          bd = d;
          victim = o;
        }
      }
      if (victim) sim.startFight(a, victim);
    }
  }
}

export { N as NEED_INDEX, OBJ };
