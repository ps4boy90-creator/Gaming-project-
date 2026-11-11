import { R } from '../data/defs';
import { rng } from '../core/util';
import { PASS_STAFF, type Room, type WorldObject } from '../world/world';
import type { Agent, Step } from './agent';
import { ENTRY_X, ENTRY_Y, type Job, type Sim } from './sim';
import { useSpot, visitorSpot } from './spots';

function randomTile(sim: Sim, room: Room): number {
  const w = sim.world;
  for (let i = 0; i < 12; i++) {
    const t = rng.pick(room.tiles);
    if (w.cost[PASS_STAFF][t] === 2) return t;
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

function freeObjIn(sim: Sim, a: Agent, types: string[], roomType: number): WorldObject | null {
  const w = sim.world;
  let best: WorldObject | null = null, bd = 1e9;
  for (const t of types)
    for (const o of sim.objsOf(t)) {
      if (!sim.freeSlots(o)) continue;
      const room = w.roomAtTile(w.idx(o.x, o.y));
      if (roomType && (!room || room.type !== roomType || !room.valid)) continue;
      const d = Math.abs(o.x - a.x) + Math.abs(o.y - a.z);
      if (d < bd) {
        bd = d;
        best = o;
      }
    }
  return best;
}

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

/** stand somewhere sensible and wait */
function idle(sim: Sim, a: Agent, status: string, room?: Room) {
  const w = sim.world;
  const r = room ?? nearestRoom(a, w.validRoomsOf(R.staffroom));
  if (r) {
    sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, r) }, { t: 'do', dur: rng.range(6, 14), status }], status);
    return;
  }
  // mill about near the entrance
  const x = Math.round(ENTRY_X + rng.range(-5, 5)), y = Math.round(ENTRY_Y - rng.range(0, 3));
  const t = w.nearestWalkable(x, y, PASS_STAFF, 4);
  if (t >= 0 && a.distTo({ x: ENTRY_X, z: ENTRY_Y }) > 7) sim.setPlan(a, [{ t: 'walk', tile: t }, { t: 'do', dur: rng.range(5, 12), status }], status);
  else sim.setPlan(a, [{ t: 'do', dur: rng.range(5, 12), status }], status);
}

export function staffMinute(sim: Sim, a: Agent) {
  const s = a.s!;
  if (s.role !== 'riot') s.energy = Math.max(0, s.energy - 1 / 560);
  if (a.pose === 'down') {
    const doc = sim.nearestStaff(a, 'doctor', 1.8);
    s.health = Math.min(1, s.health + (doc ? 0.035 : 0.005));
  } else if (s.health < 1) s.health = Math.min(1, s.health + 0.0012);
}

export function thinkStaff(sim: Sim, a: Agent) {
  const s = a.s!, w = sim.world;
  if (a.pose === 'down') {
    sim.setPlan(a, [{
      t: 'do', hold: true, pose: 'down', icon: 'medical', status: 'Injured',
      until: () => s.health >= 0.4,
      done: () => { a.pose = 'stand'; s.mode = 'idle'; },
    }]);
    return;
  }
  if (s.mode === 'leave') {
    sim.setPlan(a, [
      { t: 'walk', tile: w.idx(ENTRY_X, ENTRY_Y), hold: true, status: 'Leaving' },
      { t: 'do', dur: 0.2, hold: true, done: () => { a.dead = true; } },
    ]);
    return;
  }
  s.mode = 'idle';
  s.targetId = 0;
  // tired staff take a break
  if (s.role !== 'riot' && s.energy < 0.2 && !sim.riot) {
    const room = nearestRoom(a, w.validRoomsOf(R.staffroom));
    if (room) {
      s.mode = 'break';
      const rest: Partial<Step> = { dur: 40, done: () => { s.energy = 1; s.mode = 'idle'; } };
      const seat = freeObjIn(sim, a, ['sofa', 'chair'], R.staffroom);
      if (seat && useObj(sim, a, seat, rest, 'On a break')) return;
      sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, room) }, { t: 'do', status: 'On a break', ...rest }], 'On a break');
      return;
    }
    sim.warn('nostaffroom', 'Your staff are exhausted and slow. Build a Staff Room so they can rest.', 900);
  }
  switch (s.role) {
    case 'guard': return guard(sim, a);
    case 'riot': return riotOfficer(sim, a);
    case 'workman': return workman(sim, a);
    case 'cook': return cook(sim, a);
    case 'doctor': return doctor(sim, a);
    case 'janitor': return janitor(sim, a);
    case 'teacher': return teacher(sim, a);
    case 'psych': return deskJob(sim, a, R.psych, 'Seeing patients', 'Needs an office');
    case 'chaplain': return chaplain(sim, a);
    case 'warden': return warden(sim, a);
  }
}

function guard(sim: Sim, a: Agent) {
  const s = a.s!, w = sim.world;
  // fixed posts: towers and CCTV consoles (a third of the force at most)
  if (s.station < 0 && a.id % 3 === 0) {
    const tower = freeObjIn(sim, a, ['guard_tower'], 0);
    if (tower && useObj(sim, a, tower, { dur: 120 }, 'On tower duty')) return;
    const desk = freeObjIn(sim, a, ['cctv_monitor'], R.security);
    if (desk && useObj(sim, a, desk, { dur: 90 }, 'Watching CCTV')) return;
  }
  if (s.station >= 0) {
    const room = w.roomAtTile(s.station);
    if (room) {
      sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, room) }, { t: 'do', dur: rng.range(8, 18), status: 'On post' }], 'On post');
      return;
    }
    s.station = -1;
  }
  // patrol: go where the inmates are
  let room: Room | undefined;
  if (sim.prisoners.length && rng.chance(0.75)) room = sim.roomOf(rng.pick(sim.prisoners));
  if (!room) {
    const rooms = [...w.rooms.values()].filter((r) => r.type !== R.storage && r.type !== R.staffroom);
    if (rooms.length) room = rng.pick(rooms);
  }
  if (room) {
    // stay just outside locked cells: aim for a tile next to the room when it is a cell
    sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, room) }, { t: 'do', dur: rng.range(3, 9), status: 'Patrolling' }], 'Patrolling');
    return;
  }
  idle(sim, a, 'Patrolling');
}

function riotOfficer(sim: Sim, a: Agent) {
  // dispatch assigns targets; otherwise hold position inside the gate
  const w = sim.world;
  const rioter = sim.prisoners.find((p) => p.p!.mode === 'riot' && !sim.inFight(p));
  if (rioter) {
    sim.respond(a, rioter);
    return;
  }
  const t = w.nearestWalkable(ENTRY_X + rng.int(-3, 3), ENTRY_Y - rng.int(2, 6), PASS_STAFF, 4);
  if (t >= 0) sim.setPlan(a, [{ t: 'walk', tile: t, run: true }, { t: 'do', dur: 4, status: 'Standing by' }], 'Standing by');
  else sim.setPlan(a, [{ t: 'do', dur: 4, status: 'Standing by' }]);
}

const JOB_TIME: Record<Job['kind'], number> = { wall: 1.3, door: 2.4, floor: 0.32, object: 2.0 };
const JOB_BIAS: Record<Job['kind'], number> = { wall: 0, door: 2, floor: 4, object: 7 };

function workman(sim: Sim, a: Agent) {
  const w = sim.world, s = a.s!;
  const jobs = sim.jobs();
  let best: Job | null = null, bd = 1e9;
  for (const j of jobs) {
    if (sim.claims.has(j.key)) continue;
    const jx = j.tile % w.w, jy = Math.floor(j.tile / w.w);
    const d = Math.max(Math.abs(jx - a.x), Math.abs(jy - a.z)) + JOB_BIAS[j.kind];
    if (d < bd) {
      bd = d;
      best = j;
    }
  }
  if (!best) {
    const store = nearestRoom(a, w.roomsOf(R.storage));
    idle(sim, a, 'Waiting for work', store);
    return;
  }
  const j = best;
  sim.claims.set(j.key, a.id);
  s.mode = 'job';
  const jx = j.tile % w.w, jy = Math.floor(j.tile / w.w);
  // stand beside the job (walls) or on it (floors, objects)
  let stand = -1, sd = 1e9;
  const cost = w.cost[PASS_STAFF];
  const consider = (x: number, y: number) => {
    if (!w.inb(x, y)) return;
    const i = w.idx(x, y);
    if (!cost[i] || w.planWall[i] || w.planDoor[i]) return;
    const d = Math.hypot(x + 0.5 - a.x, y + 0.5 - a.z);
    if (d < sd) {
      sd = d;
      stand = i;
    }
  };
  if (j.kind === 'floor' || j.kind === 'object') consider(jx, jy);
  if (stand < 0) for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, 1], [1, -1], [-1, -1]]) consider(jx + dx, jy + dy);
  const yaw = Math.atan2(jx + 0.5 - ((stand % w.w) + 0.5), jy + 0.5 - (Math.floor(stand / w.w) + 0.5));
  const work: Step = {
    t: 'do', pose: 'work', dur: JOB_TIME[j.kind] * (stand < 0 ? 2 : 1), icon: 'build', status: 'Building',
    yaw: stand >= 0 && stand !== j.tile ? yaw : undefined,
    done: () => { sim.completeJob(j); s.mode = 'idle'; },
  };
  if (stand < 0) sim.setPlan(a, [work], 'Building');
  else sim.setPlan(a, [{ t: 'walk', tile: stand }, work], 'Building');
}

function cook(sim: Sim, a: Agent) {
  const w = sim.world;
  const kitchen = nearestRoom(a, w.validRoomsOf(R.kitchen));
  if (!kitchen) return idle(sim, a, 'No kitchen to work in');
  if (sim.meals < sim.mealCap() - 1) {
    const o = freeObjIn(sim, a, ['cooker'], R.kitchen);
    if (o && useObj(sim, a, o, {
      dur: rng.range(14, 22), icon: 'work',
      tick: (dt) => {
        if (sim.meals < sim.mealCap()) {
          sim.meals += dt * 0.32;
          sim.spend(dt * 0.32 * 1.4, 'Food', true);
        }
      },
    }, 'Cooking')) return;
  }
  sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, kitchen) }, { t: 'do', dur: rng.range(4, 9), status: 'Kitchen duty' }], 'Kitchen duty');
}

function doctor(sim: Sim, a: Agent) {
  const w = sim.world;
  // emergencies first
  let target: Agent | null = null, bd = 1e9;
  for (const o of sim.agents) {
    if (o.pose !== 'down' || o.dead || o === a) continue;
    const d = a.distTo(o);
    if (d < bd) {
      bd = d;
      target = o;
    }
  }
  if (target) {
    const t = target;
    sim.setPlan(a, [
      { t: 'follow', target: t, range: 1.3, run: true, status: 'Responding to casualty', abort: () => t.pose !== 'down' },
      { t: 'do', pose: 'work', dur: 20, until: () => t.pose !== 'down' || t.dead, status: 'Giving first aid', icon: 'medical' },
    ], 'Responding to casualty');
    return;
  }
  const room = nearestRoom(a, w.validRoomsOf(R.infirmary));
  if (!room) return idle(sim, a, 'No infirmary to work in');
  const patients = room.objects.map((id) => w.objects.get(id)!).filter((o) => o.type === 'medical_bed' && o.users.some((u) => u));
  if (patients.length) {
    const bed = rng.pick(patients);
    const t = w.nearestWalkable(bed.x + (rng.chance(0.5) ? 1 : -1), bed.y, PASS_STAFF, 2);
    sim.setPlan(a, [{ t: 'walk', tile: t >= 0 ? t : randomTile(sim, room) }, { t: 'do', pose: 'work', dur: rng.range(6, 12), status: 'Treating a patient' }], 'Treating a patient');
    return;
  }
  const desk = freeObjIn(sim, a, ['office_desk'], R.infirmary);
  if (desk && useObj(sim, a, desk, { dur: rng.range(15, 30) }, 'On call')) return;
  sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, room) }, { t: 'do', dur: rng.range(6, 12), status: 'On call' }], 'On call');
}

function janitor(sim: Sim, a: Agent) {
  let best: Room | undefined, bd = 0.12;
  for (const r of sim.world.rooms.values()) {
    if (r.outdoor) continue;
    const score = r.dirt - Math.min(0.1, (Math.abs(r.cx - a.x) + Math.abs(r.cy - a.z)) * 0.002);
    if (score > bd) {
      bd = score;
      best = r;
    }
  }
  if (!best) return idle(sim, a, 'Nothing to clean');
  const room = best;
  sim.setPlan(a, [
    { t: 'walk', tile: randomTile(sim, room) },
    { t: 'do', pose: 'work', dur: rng.range(4, 7), status: 'Cleaning', tick: (dt) => { room.dirt = Math.max(0, room.dirt - (dt * 1.1) / Math.max(8, room.tiles.length)); } },
  ], 'Cleaning');
}

function standAt(sim: Sim, a: Agent, o: WorldObject, dur: number, status: string, pose: Step['pose'] = 'stand') {
  const s = useSpot(sim.world, o, 0);
  sim.setPlan(a, [{ t: 'walk', tile: s.tile }, { t: 'do', px: s.px, pz: s.pz, yaw: s.yaw, pose, dur, status }], status);
}

function teacher(sim: Sim, a: Agent) {
  const w = sim.world;
  const room = nearestRoom(a, w.validRoomsOf(R.classroom));
  if (!room) return idle(sim, a, 'No classroom to teach in');
  if (sim.activity === 'work') {
    const board = room.objects.map((id) => w.objects.get(id)!).find((o) => o.type === 'blackboard');
    if (board) return standAt(sim, a, board, rng.range(15, 25), 'Teaching', 'work');
  }
  sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, room) }, { t: 'do', dur: rng.range(8, 15), status: 'Preparing lessons' }], 'Preparing lessons');
}

function chaplain(sim: Sim, a: Agent) {
  const w = sim.world;
  const room = nearestRoom(a, w.validRoomsOf(R.chapel));
  if (!room) return idle(sim, a, 'No chapel');
  const altar = room.objects.map((id) => w.objects.get(id)!).find((o) => o.type === 'altar');
  const flock = sim.prisoners.some((p) => sim.roomOf(p) === room);
  if (altar) return standAt(sim, a, altar, rng.range(15, 25), flock ? 'Leading a service' : 'Tending the chapel', flock ? 'work' : 'stand');
  idle(sim, a, 'Tending the chapel', room);
}

function deskJob(sim: Sim, a: Agent, roomType: number, status: string, noRoom: string) {
  const room = nearestRoom(a, sim.world.validRoomsOf(roomType));
  if (!room) return idle(sim, a, noRoom);
  const desk = freeObjIn(sim, a, ['office_desk'], roomType);
  if (desk && useObj(sim, a, desk, { dur: rng.range(40, 70) }, status)) return;
  idle(sim, a, status, room);
}

function warden(sim: Sim, a: Agent) {
  const w = sim.world;
  const office = nearestRoom(a, w.validRoomsOf(R.warden));
  if (!office) return idle(sim, a, "Needs a Warden's Office");
  if (rng.chance(0.22) && sim.roomOf(a) === office) {
    const rooms = [...w.rooms.values()].filter((r) => r.type !== R.cell && r.type !== R.solitary);
    if (rooms.length) {
      sim.setPlan(a, [{ t: 'walk', tile: randomTile(sim, rng.pick(rooms)) }, { t: 'do', dur: rng.range(4, 8), status: 'Inspecting the prison' }], 'Inspecting the prison');
      return;
    }
  }
  deskJob(sim, a, R.warden, 'Running the prison', "Needs a Warden's Office");
}

export function thinkVisitor(sim: Sim, a: Agent) {
  const w = sim.world;
  const tableId = -(a.resv.find((id) => id < 0) ?? 0);
  const table = w.objects.get(tableId);
  const inmate = sim.byId.get(a.visitFor);
  if (a.stage === 0 && table && inmate && !inmate.dead) {
    a.stage = 1;
    const s = visitorSpot(w, table);
    sim.setPlan(a, [
      { t: 'walk', tile: s.tile, status: 'Visiting' },
      { t: 'do', px: s.px, pz: s.pz, y: s.y, yaw: s.yaw, pose: 'sit', dur: 45, status: `Visiting ${inmate.name}`, until: () => a.visitFor === 0 || inmate.dead, done: () => { a.visitFor = 0; } },
    ]);
    return;
  }
  a.visitFor = 0;
  sim.setPlan(a, [
    { t: 'walk', tile: w.idx(ENTRY_X, ENTRY_Y), status: 'Leaving' },
    { t: 'do', dur: 0.2, done: () => { a.dead = true; } },
  ]);
}
