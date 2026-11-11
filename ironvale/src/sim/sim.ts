import {
  DEFAULT_REGIME, DOORS, FLOORS, MAP_H, MAP_W, NEEDS, OBJ, R, ROOMS, SEC_GRANT, STAFF_BY_ROLE, WALLS,
  type Activity, type StaffRole,
} from '../data/defs';
import { CASUAL, CRIMES, FIRST, FIRST_F, HAIR, LAST, SKIN } from '../data/names';
import { Bus, clamp, clamp01, fmtMoney, rng } from '../core/util';
import { Pathfinder } from '../world/pathfinding';
import { PASS_PRISONER, PASS_STAFF, World, footprint, type Room, type WorldObject } from '../world/world';
import { Agent, peekAgentId, resetAgentIds, type Look, type PrisonerData, type Role, type Step } from './agent';
import { prisonerMinute, thinkPrisoner } from './prisoner';
import { staffMinute, thinkStaff, thinkVisitor } from './staff';

export const ENTRY_X = Math.floor(MAP_W / 2);
export const ENTRY_Y = MAP_H - 1;
/** real seconds per sim minute at 1x */
export const SEC_PER_MIN = 0.7;
export const INTAKE_RATE = [0, 2, 4, 8];
export const INTAKE_NAME = ['Closed', 'Trickle', 'Steady', 'Flood'];

export interface Fight {
  a: Agent;
  b: Agent;
  t: number;
  subdue: number;
}
export interface Job {
  kind: 'wall' | 'door' | 'floor' | 'object';
  tile: number;
  objId: number;
  key: number;
}
export interface Objective {
  id: string;
  title: string;
  desc: string;
  reward: number;
  check: (s: Sim) => boolean;
}
export interface LogEntry {
  t: number;
  text: string;
  kind: 'info' | 'good' | 'bad' | 'warn';
  x?: number;
  z?: number;
}

const ROLE_LOOK: Record<Role, { torso: number; legs: number; hat: number }> = {
  warden: { torso: 0x3b4252, legs: 0x2b303b, hat: 0 },
  guard: { torso: 0x2f4a80, legs: 0x1f2a44, hat: 1 },
  doctor: { torso: 0xf2f3f1, legs: 0x4d9a94, hat: 0 },
  cook: { torso: 0xf4f4f2, legs: 0x6b7480, hat: 2 },
  janitor: { torso: 0x4f8f7a, legs: 0x3d6f5f, hat: 0 },
  workman: { torso: 0xe2c435, legs: 0x3f5f8a, hat: 3 },
  teacher: { torso: 0x8a6a4a, legs: 0x4a4f5a, hat: 0 },
  psych: { torso: 0x8a6fb0, legs: 0x4a4458, hat: 0 },
  chaplain: { torso: 0x2c2c33, legs: 0x23232a, hat: 0 },
  riot: { torso: 0x23272e, legs: 0x1b1e24, hat: 4 },
};
const JUMPSUIT = [0x5f93c9, 0xe8842c, 0xc8443a];
const EMPTY: WorldObject[] = [];

export class Sim {
  world: World;
  pf: Pathfinder;
  bus = new Bus();
  agents: Agent[] = [];
  byId = new Map<number, Agent>();
  prisoners: Agent[] = [];
  staff: Agent[] = [];

  /** minutes since day 1, 00:00 */
  time = 7 * 60;
  speed = 1;
  paused = false;
  money = 80000;
  regime: Activity[] = [...DEFAULT_REGIME];
  intake = 2;
  lockdown = false;
  shakedownUntil = 0;
  riot = false;
  meals = 0;
  /** 0..1: how well the laundry keeps uniforms clean */
  laundry = 0;
  danger = 0;
  instantBuild = false;
  name = 'Ironvale Correctional';

  fights: Fight[] = [];
  /** solitary room (first tile) -> inmate id */
  solitaryOcc = new Map<number, number>();
  claims = new Map<number, number>();
  private jobCache: Job[] = [];
  private jobVersion = -1;
  planVersion = 0;
  private arrivals: { at: number; count: number }[] = [];
  private minuteAcc = 0;
  private lastHour = -1;
  private topoSeen = -1;
  private objIndex = new Map<string, WorldObject[]>();

  ledgerToday: Record<string, number> = {};
  ledgerYesterday: Record<string, number> = {};
  history: { day: number; net: number; pop: number }[] = [];
  stats = { escapes: 0, deaths: 0, released: 0, fights: 0, contraband: 0, intake: 0, lastEscapeDay: 0, reoffendSaved: 0 };
  objectivesDone = new Set<string>();
  log: LogEntry[] = [];
  warnCooldown = new Map<string, number>();
  /** cached counts refreshed each sim minute */
  counts = { guards: 0, cooks: 0, doctors: 0, janitors: 0, workmen: 0, teachers: 0, psychs: 0, chaplains: 0, warden: 0, capacity: 0, wardenIn: false, armoury: false, cctv: false };

  constructor(world?: World) {
    this.world = world ?? new World();
    this.pf = new Pathfinder(this.world);
    this.world.rebuildTopology();
  }

  // ------------------------------------------------------------------ time
  get day() {
    return Math.floor(this.time / 1440) + 1;
  }
  get hour() {
    return Math.floor((this.time % 1440) / 60);
  }
  get hourF() {
    return (this.time % 1440) / 60;
  }
  /** what the regime says prisoners should be doing right now */
  get activity(): Activity {
    if (this.lockdown || this.time < this.shakedownUntil) return 'lockup';
    return this.regime[this.hour];
  }

  update(dtReal: number) {
    if (this.paused) return;
    let dt = (Math.min(dtReal, 0.1) * this.speed) / SEC_PER_MIN;
    // sub-step so fast speeds stay stable
    const steps = Math.max(1, Math.ceil(dt / 0.2));
    dt /= steps;
    for (let i = 0; i < steps; i++) this.tick(dt);
  }

  /** bring rooms, path costs and indexes up to date with the world (safe to call every frame) */
  sync() {
    if (this.world.dirtyTopo) this.world.rebuildTopology();
    if (this.world.topoVersion !== this.topoSeen) {
      this.topoSeen = this.world.topoVersion;
      this.onTopology();
    }
  }

  private tick(dt: number) {
    this.time += dt;
    this.sync();
    const h = this.hour;
    if (h !== this.lastHour) {
      const first = this.lastHour < 0;
      this.lastHour = h;
      if (!first) this.onHour(h);
    }
    for (const a of this.agents) if (!a.dead) this.updateAgent(a, dt);
    this.minuteAcc += dt;
    while (this.minuteAcc >= 1) {
      this.minuteAcc -= 1;
      this.perMinute();
    }
    if (this.agents.some((a) => a.dead)) this.sweepDead();
  }

  private onHour(h: number) {
    // regime changes interrupt whatever prisoners were doing
    for (const a of this.prisoners) {
      const p = a.p!;
      if (h === 0 || this.regime[h] !== this.regime[(h + 23) % 24]) {
        p.ate = false;
        p.showered = false;
        if (!a.busy) this.clearPlan(a);
      }
    }
    if (h === 0) this.onDay();
    if (h === 8) this.scheduleIntake();
    this.bus.emit('hour', h);
  }

  private onDay() {
    // income
    let grant = 600;
    for (const a of this.prisoners) grant += SEC_GRANT[a.p!.sec];
    if (this.counts.wardenIn) grant = Math.round(grant * 1.1);
    this.earn(grant, 'State grant');
    let wages = 0;
    for (const a of this.staff) wages += a.s!.wage;
    this.spend(wages, 'Wages', true);
    const net = Object.values(this.ledgerToday).reduce((s, v) => s + v, 0);
    this.history.push({ day: this.day - 1, net, pop: this.prisoners.length });
    if (this.history.length > 30) this.history.shift();
    this.ledgerYesterday = this.ledgerToday;
    this.ledgerToday = {};
    this.toast(`Day ${this.day - 1} closed: ${net >= 0 ? '+' : ''}${fmtMoney(net)}`, net >= 0 ? 'good' : 'bad');
    this.bus.emit('day', this.day);
  }

  // ------------------------------------------------------------------ money
  earn(v: number, cat: string) {
    if (v <= 0) return;
    this.money += v;
    this.ledgerToday[cat] = (this.ledgerToday[cat] ?? 0) + v;
  }
  /** returns false if the player cannot afford it (unless forced) */
  spend(v: number, cat: string, force = false): boolean {
    if (v <= 0) return true;
    if (!force && this.money < v) return false;
    this.money -= v;
    this.ledgerToday[cat] = (this.ledgerToday[cat] ?? 0) - v;
    return true;
  }
  canAfford(v: number) {
    return this.money >= v;
  }

  // ------------------------------------------------------------------ messages
  toast(text: string, kind: LogEntry['kind'] = 'info', x?: number, z?: number) {
    const e: LogEntry = { t: this.time, text, kind, x, z };
    this.log.push(e);
    if (this.log.length > 80) this.log.shift();
    this.bus.emit('toast', e);
  }
  /** like toast, but rate-limited per key (sim minutes) */
  warn(key: string, text: string, cooldown = 240, kind: LogEntry['kind'] = 'warn', x?: number, z?: number) {
    const last = this.warnCooldown.get(key) ?? -1e9;
    if (this.time - last < cooldown) return;
    this.warnCooldown.set(key, this.time);
    this.toast(text, kind, x, z);
  }

  // ------------------------------------------------------------------ agents
  private addAgent(a: Agent) {
    this.agents.push(a);
    this.byId.set(a.id, a);
    if (a.kind === 'prisoner') this.prisoners.push(a);
    else if (a.kind === 'staff') this.staff.push(a);
  }
  private sweepDead() {
    for (const a of this.agents) if (a.dead) {
      this.release(a);
      this.byId.delete(a.id);
      for (const [k, v] of this.solitaryOcc) if (v === a.id) this.solitaryOcc.delete(k);
      for (const [k, v] of this.claims) if (v === a.id) this.claims.delete(k);
    }
    this.agents = this.agents.filter((a) => !a.dead);
    this.prisoners = this.prisoners.filter((a) => !a.dead);
    this.staff = this.staff.filter((a) => !a.dead);
    this.fights = this.fights.filter((f) => !f.a.dead && !f.b.dead);
  }
  private randomLook(torso: number, legs: number, hat: number): Look {
    return { torso, legs, skin: rng.pick(SKIN), hair: rng.pick(HAIR), hat, bald: rng.chance(0.18) };
  }
  private spawnPoint(a: Agent, spread = 2.5) {
    a.x = ENTRY_X + 0.5 + rng.range(-spread, spread);
    a.z = ENTRY_Y + 0.5 + rng.range(0.6, 2.2);
  }

  spawnPrisoner(sec?: number): Agent {
    const [crime, lvl] = rng.pick(CRIMES);
    const s = sec ?? lvl;
    const a = new Agent('prisoner', this.randomLook(JUMPSUIT[s], JUMPSUIT[s], 0));
    a.name = `${rng.pick(FIRST)} ${rng.pick(LAST)}`;
    a.pass = PASS_STAFF; // new arrivals are escorted in through the gate
    a.speed = rng.range(1.55, 1.9);
    const needs = new Float32Array(NEEDS.length);
    for (let i = 0; i < needs.length; i++) needs[i] = rng.range(0.05, 0.4);
    a.p = {
      sec: s, crime, age: rng.int(19, 62), sentence: [rng.int(3, 6), rng.int(5, 10), rng.int(9, 16)][s], served: 0,
      needs, anger: rng.range(0.05, 0.25) + s * 0.05, health: 1, temper: rng.range(0.5, 1.2) + s * 0.2,
      bedId: 0, bedSlot: 0, contraband: '', dig: 0, mode: 'intake', modeUntil: 0, processed: false, ate: false, showered: false,
      edu: 0, reform: 0, misconduct: 0, nextRoll: this.time + rng.range(5, 15), escortedBy: 0,
    };
    this.spawnPoint(a);
    this.addAgent(a);
    this.stats.intake++;
    return a;
  }

  staffCount(role: Role) {
    let n = 0;
    for (const a of this.staff) if (a.s!.role === role && a.s!.mode !== 'leave') n++;
    return n;
  }

  hire(role: StaffRole, free = false): Agent | null {
    const def = STAFF_BY_ROLE[role];
    if (def.max && this.staffCount(role) >= def.max) {
      this.toast(`You already have a ${def.name}.`, 'warn');
      return null;
    }
    if (!free && !this.spend(def.hire, 'Hiring')) {
      this.toast('Not enough money to hire.', 'bad');
      return null;
    }
    return this.spawnStaff(role);
  }
  spawnStaff(role: Role): Agent {
    const l = ROLE_LOOK[role];
    const a = new Agent('staff', this.randomLook(l.torso, l.legs, l.hat));
    const female = rng.chance(0.4);
    a.name = `${rng.pick(female ? FIRST_F : FIRST)} ${rng.pick(LAST)}`;
    if (role === 'warden') a.look.hair = 0x9a9a9a;
    a.pass = PASS_STAFF;
    a.speed = role === 'riot' ? 2.3 : role === 'guard' ? 2.05 : 1.8;
    a.s = {
      role, energy: rng.range(0.7, 1), station: -1, mode: 'idle', targetId: 0, health: 1, jobId: 0,
      wage: role === 'riot' ? 0 : STAFF_BY_ROLE[role as StaffRole].wage,
    };
    this.spawnPoint(a);
    this.addAgent(a);
    return a;
  }
  fire(a: Agent) {
    if (!a.s || a.s.mode === 'leave') return;
    this.clearPlan(a);
    a.s.mode = 'leave';
    if (a.s.role !== 'riot') this.toast(`${a.name} has been let go.`, 'info');
  }

  spawnVisitor(forId: number, obj: WorldObject): Agent {
    const a = new Agent('visitor', this.randomLook(rng.pick(CASUAL), rng.pick([0x3a4a66, 0x4a4a4a, 0x6b5a48]), 0));
    a.name = `${rng.pick(rng.chance(0.6) ? FIRST_F : FIRST)} ${rng.pick(LAST)}`;
    a.pass = PASS_STAFF;
    a.visitFor = forId;
    a.resv.push(-obj.id); // remember the table (negative = not a slot reservation)
    this.spawnPoint(a);
    this.addAgent(a);
    return a;
  }

  /** built objects of a type */
  objsOf(type: string): WorldObject[] {
    return this.objIndex.get(type) ?? EMPTY;
  }
  mealCap(): number {
    let counters = 0;
    for (const o of this.objsOf('serving_counter')) {
      const r = this.world.roomAtTile(this.world.idx(o.x, o.y));
      if (r && r.type === R.canteen && r.valid) counters++;
    }
    return 10 + counters * 18;
  }

  tileOf(a: { x: number; z: number }) {
    const x = clamp(Math.floor(a.x), 0, this.world.w - 1), y = clamp(Math.floor(a.z), 0, this.world.h - 1);
    return y * this.world.w + x;
  }
  roomOf(a: Agent): Room | undefined {
    return this.world.roomAtTile(this.tileOf(a));
  }

  // ------------------------------------------------------------------ reservations & plans
  /** reserve a free slot of an object; returns the slot index or -1 */
  reserve(a: Agent, o: WorldObject): number {
    const slots = OBJ[o.type].slots;
    for (let i = 0; i < slots; i++) {
      if (!o.users[i]) {
        o.users[i] = a.id;
        a.resv.push(o.id);
        return i;
      }
    }
    return -1;
  }
  freeSlots(o: WorldObject): number {
    const slots = OBJ[o.type].slots;
    let n = 0;
    for (let i = 0; i < slots; i++) if (!o.users[i]) n++;
    return n;
  }
  release(a: Agent) {
    for (const id of a.resv) {
      if (id < 0) continue;
      const o = this.world.objects.get(id);
      if (!o) continue;
      for (let i = 0; i < o.users.length; i++) if (o.users[i] === a.id) o.users[i] = 0;
    }
    a.resv = a.resv.filter((id) => id < 0 && a.kind === 'visitor');
    for (const [k, v] of this.claims) if (v === a.id) this.claims.delete(k);
  }
  clearPlan(a: Agent) {
    a.steps.length = 0;
    a.path = null;
    a.stepT = 0;
    a.stepInit = false;
    a.y = 0;
    a.icon = null;
    if (a.pose !== 'down') a.pose = 'stand';
    this.release(a);
  }
  setPlan(a: Agent, steps: Step[], status?: string) {
    a.steps = steps;
    a.stepT = 0;
    a.stepInit = false;
    a.path = null;
    if (status !== undefined) a.status = status;
  }

  private updateAgent(a: Agent, dt: number) {
    if (!a.steps.length) {
      a.thinkT -= dt;
      if (a.thinkT <= 0) {
        a.thinkT = 0.4 + Math.random() * 0.6;
        if (a.kind === 'prisoner') thinkPrisoner(this, a);
        else if (a.kind === 'staff') thinkStaff(this, a);
        else thinkVisitor(this, a);
      }
      return;
    }
    const s = a.steps[0];
    if (s.status !== undefined && !a.stepInit) a.status = s.status;
    switch (s.t) {
      case 'walk': {
        if (!a.stepInit) {
          a.stepInit = true;
          a.y = 0;
          const from = this.tileOf(a);
          let path = this.pf.find(from, s.tile!, a.pass);
          // an inmate with legitimate business is let through staff doors by a guard
          if (!path && a.p && a.pass === PASS_PRISONER && a.p.mode === 'normal' && !s.run) path = this.pf.find(from, s.tile!, PASS_STAFF);
          if (!path) {
            // staff can always get through eventually; prisoners just fail
            a.noPath++;
            if (a.kind !== 'prisoner' && a.noPath >= 3 && this.world.cost[a.pass][s.tile!]) {
              a.x = (s.tile! % this.world.w) + 0.5;
              a.z = Math.floor(s.tile! / this.world.w) + 0.5;
              a.noPath = 0;
              this.nextStep(a);
              return;
            }
            this.clearPlan(a);
            a.thinkT = 1 + Math.random() * 2;
            return;
          }
          a.noPath = 0;
          a.path = path;
          a.pathI = 0;
        }
        a.pose = s.run ? 'run' : 'walk';
        if (this.moveAlong(a, dt, s.run ? 1.55 : 1)) this.nextStep(a);
        break;
      }
      case 'do': {
        if (!a.stepInit) {
          a.stepInit = true;
          if (s.px !== undefined) {
            a.x = s.px;
            a.z = s.pz!;
          }
          if (s.yaw !== undefined) a.yaw = s.yaw;
          a.y = s.y ?? 0;
          a.pose = s.pose ?? 'stand';
          if (s.icon !== undefined) a.icon = s.icon;
        }
        s.tick?.(dt);
        a.stepT += dt;
        if ((s.dur !== undefined && a.stepT >= s.dur) || s.until?.()) {
          const done = s.done;
          this.nextStep(a);
          done?.();
        }
        break;
      }
      case 'follow': {
        const t = s.target!;
        if (t.dead || s.abort?.()) {
          this.nextStep(a);
          break;
        }
        const d = a.distTo(t);
        if (d <= (s.range ?? 1)) {
          const done = s.done;
          this.nextStep(a);
          done?.();
          break;
        }
        a.repathT -= dt;
        if (!a.path || a.repathT <= 0) {
          a.repathT = 1.2;
          const goal = this.world.nearestWalkable(Math.floor(t.x), Math.floor(t.z), a.pass, 3);
          a.path = goal >= 0 ? this.pf.find(this.tileOf(a), goal, a.pass) : null;
          a.pathI = 0;
          if (!a.path) {
            a.noPath++;
            if (a.noPath > 4) {
              // give up politely
              a.noPath = 0;
              this.nextStep(a);
              break;
            }
          }
        }
        a.pose = s.run ? 'run' : 'walk';
        if (a.path) this.moveAlong(a, dt, s.run ? 1.6 : 1);
        break;
      }
    }
  }

  private nextStep(a: Agent) {
    a.steps.shift();
    a.stepT = 0;
    a.stepInit = false;
    a.path = null;
    a.y = 0;
    if (a.pose !== 'down') a.pose = 'stand';
    a.icon = null;
    if (!a.steps.length) {
      this.release(a);
      a.thinkT = 0.05 + Math.random() * 0.3;
    }
  }

  /** advance along a.path. Returns true on arrival. */
  private moveAlong(a: Agent, dt: number, mult: number): boolean {
    const path = a.path;
    if (!path) return true;
    const w = this.world;
    let exhausted = a.s && a.s.energy <= 0.02 ? 0.75 : 1;
    let budget = a.speed * mult * exhausted * dt;
    while (budget > 0 && a.pathI < path.length) {
      const tile = path[a.pathI];
      if (!w.cost[a.pass][tile]) {
        a.path = null;
        a.stepInit = false; // re-plan this step
        return false;
      }
      const isDoor = w.door[tile] !== 0;
      const last = a.pathI === path.length - 1;
      const narrow = isDoor || last || w.cost[a.pass][tile] > 2;
      const txp = (tile % w.w) + 0.5 + (narrow ? 0 : a.offX);
      const tzp = Math.floor(tile / w.w) + 0.5 + (narrow ? 0 : a.offZ);
      const dx = txp - a.x, dz = tzp - a.z;
      const d = Math.hypot(dx, dz);
      if (d > 1e-4) {
        const want = Math.atan2(dx, dz);
        let diff = want - a.yaw;
        while (diff > Math.PI) diff -= Math.PI * 2;
        while (diff < -Math.PI) diff += Math.PI * 2;
        a.yaw += diff * Math.min(1, dt * 9);
      }
      if (d <= budget) {
        a.x = txp;
        a.z = tzp;
        budget -= d;
        a.pathI++;
        if (a.p && a.p.contraband) this.onEnterTile(a, tile);
      } else {
        a.x += (dx / d) * budget;
        a.z += (dz / d) * budget;
        budget = 0;
      }
    }
    return a.pathI >= path.length;
  }

  private onEnterTile(a: Agent, tile: number) {
    const oid = this.world.objAt[tile];
    if (!oid) return;
    const o = this.world.objects.get(oid);
    if (!o || !o.built || o.type !== 'metal_detector') return;
    const p = a.p!;
    if (p.contraband !== 'weapon' && p.contraband !== 'tools') return;
    if (!this.nearestStaff(a, 'guard', 12)) return;
    this.toast(`Metal detector: ${a.name} was carrying ${p.contraband === 'weapon' ? 'a shank' : 'digging tools'}.`, 'good', a.x, a.z);
    p.contraband = '';
    p.dig = 0;
    p.misconduct++;
    p.anger = clamp01(p.anger + 0.1);
    this.stats.contraband++;
  }

  /** nearest staff of a role within range, or null */
  nearestStaff(to: { x: number; z: number }, role: Role, range: number, onlyFree = false): Agent | null {
    let best: Agent | null = null, bd = range;
    for (const s of this.staff) {
      if (s.s!.role !== role || s.s!.mode === 'leave' || s.pose === 'down') continue;
      if (onlyFree && (s.s!.mode === 'respond' || s.s!.mode === 'escort' || s.busy)) continue;
      const d = Math.hypot(s.x - to.x, s.z - to.z);
      if (d < bd) {
        bd = d;
        best = s;
      }
    }
    return best;
  }

  // ------------------------------------------------------------------ topology changes
  private onTopology() {
    const w = this.world;
    this.objIndex.clear();
    for (const o of w.objects.values()) {
      if (!o.built) continue;
      let l = this.objIndex.get(o.type);
      if (!l) this.objIndex.set(o.type, (l = []));
      l.push(o);
    }
    // nudge anyone standing inside a new wall
    for (const a of this.agents) {
      const t = this.tileOf(a);
      if (!w.cost[PASS_STAFF][t]) {
        const n = w.nearestWalkable(t % w.w, Math.floor(t / w.w), PASS_STAFF, 8);
        if (n >= 0) {
          a.x = (n % w.w) + 0.5;
          a.z = Math.floor(n / w.w) + 0.5;
        }
      }
      if (a.path) {
        a.path = null;
        if (a.steps.length && a.steps[0].t === 'walk') a.stepInit = false;
      }
    }
    // beds that vanished or sit in invalid rooms no longer count
    let cap = 0;
    for (const type of [R.cell, R.dorm]) for (const r of w.validRoomsOf(type)) cap += r.capacity;
    this.counts.capacity = cap;
    for (const a of this.prisoners) {
      const p = a.p!;
      if (!p.bedId) continue;
      const o = w.objects.get(p.bedId);
      const room = o ? w.roomAtTile(w.idx(o.x, o.y)) : undefined;
      if (!o || !o.built || !room || !room.valid || (room.type !== R.cell && room.type !== R.dorm)) p.bedId = 0;
    }
    // solitary bookings are keyed by the room's first tile, which survives rebuilds
    for (const [tile] of this.solitaryOcc) {
      const r = w.roomAtTile(tile);
      if (!r || r.type !== R.solitary || r.tiles[0] !== tile) this.solitaryOcc.delete(tile);
    }
  }

  /** find a free bed for a prisoner. Returns true when assigned. */
  assignBed(a: Agent): boolean {
    const p = a.p!;
    if (p.bedId) return true;
    const w = this.world;
    const used = new Map<number, number[]>();
    for (const o of this.prisoners) if (o.p!.bedId) {
      let l = used.get(o.p!.bedId);
      if (!l) used.set(o.p!.bedId, (l = []));
      l.push(o.p!.bedSlot);
    }
    for (const type of [R.cell, R.dorm]) {
      for (const r of w.validRoomsOf(type)) {
        for (const oid of r.objects) {
          const o = w.objects.get(oid)!;
          if (o.type !== 'bed' && o.type !== 'bunk') continue;
          const slots = o.type === 'bunk' ? 2 : 1;
          const taken = used.get(oid) ?? [];
          if (taken.length >= slots) continue;
          p.bedId = oid;
          p.bedSlot = taken.includes(0) ? 1 : 0;
          return true;
        }
      }
    }
    return false;
  }
  freeBeds(): number {
    let used = 0;
    for (const a of this.prisoners) if (a.p!.bedId) used++;
    return Math.max(0, this.counts.capacity - used);
  }

  // ------------------------------------------------------------------ intake
  private scheduleIntake() {
    const rate = INTAKE_RATE[this.intake];
    if (!rate) return;
    let holding = 0;
    for (const r of this.world.validRoomsOf(R.holding)) holding += r.capacity;
    const waiting = this.prisoners.filter((a) => !a.p!.bedId).length;
    const room = this.freeBeds() + Math.max(0, holding - waiting) - waiting;
    const n = Math.min(rate, Math.max(0, room));
    if (n <= 0) {
      if (this.counts.capacity === 0) this.warn('nocells', 'No intake today: build cells with a bed and a toilet first.', 1400);
      else this.warn('full', 'No intake today: every bed is taken.', 1400, 'info');
      return;
    }
    this.requestBus(n);
  }
  requestBus(n: number) {
    this.arrivals.push({ at: this.time + 5, count: n });
    this.bus.emit('bus', { eta: 5, count: n });
    this.toast(`Prison bus inbound with ${n} new inmate${n > 1 ? 's' : ''}.`, 'info', ENTRY_X, ENTRY_Y);
  }

  // ------------------------------------------------------------------ per-minute systems
  /** recount staff and facilities */
  private census(tick: boolean) {
    const w = this.world;
    const c = this.counts;
    c.guards = c.cooks = c.doctors = c.janitors = c.workmen = c.teachers = c.psychs = c.chaplains = c.warden = 0;
    c.wardenIn = false;
    for (const s of this.staff) {
      const sd = s.s!;
      if (sd.mode === 'leave') continue;
      switch (sd.role) {
        case 'guard': c.guards++; break;
        case 'cook': c.cooks++; break;
        case 'doctor': c.doctors++; break;
        case 'janitor': c.janitors++; break;
        case 'workman': c.workmen++; break;
        case 'teacher': c.teachers++; break;
        case 'psych': c.psychs++; break;
        case 'chaplain': c.chaplains++; break;
        case 'warden': {
          c.warden++;
          const r = this.roomOf(s);
          if (r && r.type === R.warden && r.valid) c.wardenIn = true;
          break;
        }
      }
      if (tick) staffMinute(this, s);
    }
    c.armoury = w.validRoomsOf(R.armoury).length > 0;
    c.cctv = w.validRoomsOf(R.security).some((r) => r.objects.some((id) => {
      const o = w.objects.get(id)!;
      return o.type === 'cctv_monitor' && o.users.some((u) => u);
    }));

  }

  /** mark every grant the prison already satisfies as done, without paying out (used for the starter prison) */
  primeObjectives() {
    this.sync();
    this.census(false);
    for (const o of this.objectives) if (o.check(this)) this.objectivesDone.add(o.id);
  }

  private perMinute() {
    this.census(true);
    const c = this.counts;
    const w = this.world;
    void w;
    // (census moved to census())
    // arrivals
    for (const arr of this.arrivals) {
      if (this.time >= arr.at && arr.count > 0) {
        this.spawnPrisoner();
        arr.count--;
        arr.at = this.time + 0.6;
      }
    }
    this.arrivals = this.arrivals.filter((a) => a.count > 0);

    // danger decays; understaffing keeps a floor under it
    const pop = this.prisoners.length;
    const floor = pop > 4 ? clamp(0.45 - (c.guards / pop) * 4.5, 0, 0.45) : 0;
    this.danger = Math.max(floor, this.danger - 0.0025);
    this.laundry = Math.max(0, this.laundry - 1 / 1200);

    for (const a of this.prisoners) prisonerMinute(this, a);
    this.updateFights();
    this.dispatch();
    this.updateRiot();

    // rooms get dirty with use
    for (const a of this.prisoners) {
      const r = this.roomOf(a);
      if (r && !r.outdoor) r.dirt = Math.min(1, r.dirt + 0.012 / Math.max(6, r.tiles.length));
    }
    if (Math.floor(this.time) % 30 === 0) this.checkObjectives();
    if (Math.floor(this.time) % 20 === 0) for (const a of this.prisoners) if (!a.p!.bedId && a.p!.mode !== 'intake') this.assignBed(a);
  }

  // ------------------------------------------------------------------ fights & incidents
  inFight(a: Agent): Fight | undefined {
    return this.fights.find((f) => f.a === a || f.b === a);
  }
  startFight(a: Agent, b: Agent) {
    if (this.inFight(a) || this.inFight(b) || a.dead || b.dead) return;
    if (a.pose === 'down' || b.pose === 'down') return;
    this.clearPlan(a);
    this.clearPlan(b);
    // stand face to face
    const dx = b.x - a.x, dz = b.z - a.z, d = Math.hypot(dx, dz) || 1;
    const mx = (a.x + b.x) / 2, mz = (a.z + b.z) / 2;
    const ux = dx / d, uz = dz / d;
    const f: Fight = { a, b, t: 0, subdue: 0 };
    this.fights.push(f);
    const mk = (me: Agent, sx: number, yaw: number): Step => ({
      t: 'do', pose: 'fight', px: mx + ux * 0.32 * sx, pz: mz + uz * 0.32 * sx, yaw, hold: true, icon: 'fight', status: 'Fighting',
      until: () => !this.fights.includes(f),
    });
    const yawA = Math.atan2(ux, uz);
    this.setPlan(a, [mk(a, -1, yawA)]);
    this.setPlan(b, [mk(b, 1, yawA + Math.PI)]);
    if (a.p) a.p.mode = a.p.mode === 'riot' ? 'riot' : 'fight';
    if (b.p && b.p.mode !== 'riot') b.p.mode = 'fight';
    this.stats.fights++;
    this.danger = clamp01(this.danger + 0.12);
    if (!this.riot) this.warn('fight', `Fight! ${a.name} attacked ${b.name}.`, 20, 'bad', a.x, a.z);
  }

  private endFight(f: Fight) {
    const i = this.fights.indexOf(f);
    if (i >= 0) this.fights.splice(i, 1);
  }

  private updateFights() {
    for (const f of [...this.fights]) {
      const { a, b } = f;
      f.t += 1;
      const hpA = a.p ? a.p.health : a.s!.health, hpB = b.p ? b.p.health : b.s ? b.s.health : 1;
      // damage per minute
      const dmg = (att: Agent) => {
        if (att.s) return (att.s.role === 'riot' ? 0.11 : 0.05) * (this.counts.armoury ? 1.7 : 1);
        return (att.p!.contraband === 'weapon' ? 0.075 : 0.026) * rng.range(0.6, 1.4);
      };
      const hurt = (v: Agent, d: number) => {
        if (v.p) v.p.health = Math.max(0, v.p.health - d);
        else if (v.s) v.s.health = Math.max(0, v.s.health - d * (v.s.role === 'riot' ? 0.3 : 0.7));
      };
      hurt(b, dmg(a));
      hurt(a, dmg(b));
      // guards nearby subdue
      let g = 0;
      for (const s of this.staff) {
        if ((s.s!.role !== 'guard' && s.s!.role !== 'riot') || s.pose === 'down') continue;
        if (Math.hypot(s.x - a.x, s.z - a.z) < 1.8) g += s.s!.role === 'riot' ? 2 : 1;
      }
      f.subdue += g * (this.counts.armoury ? 0.5 : 0.34);
      const hA = a.p ? a.p.health : a.s!.health, hB = b.p ? b.p.health : b.s ? b.s.health : 1;
      const downA = hA < 0.15, downB = hB < 0.15;
      if (f.subdue >= 1 || downA || downB || f.t > 25) {
        this.endFight(f);
        for (const [x, isDown, wasAggressor] of [[a, downA, true], [b, downB, false]] as [Agent, boolean, boolean][]) {
          this.clearPlan(x);
          if (x.p) {
            if (x.p.health <= 0) { this.kill(x, 'died from injuries'); continue; }
            if (isDown) { this.knockDown(x); continue; }
            if (f.subdue >= 1 && (wasAggressor || x.p.mode === 'riot')) this.arrest(x, 8);
            else {
              x.p.mode = x.p.mode === 'riot' ? 'riot' : 'normal';
              if (wasAggressor) x.p.anger *= 0.75;
            }
          } else if (x.s) {
            if (isDown) this.knockDown(x);
            else x.s.mode = 'idle';
          }
        }
      }
      void hpA; void hpB;
    }
  }

  knockDown(a: Agent) {
    this.clearPlan(a);
    if (a.p) a.p.mode = 'down';
    a.pose = 'down';
    a.icon = 'medical';
    a.status = 'Unconscious';
    if (a.s) this.warn('staffdown', `${a.name} (${a.s.role}) has been knocked out!`, 30, 'bad', a.x, a.z);
  }

  kill(a: Agent, why: string) {
    a.dead = true;
    this.stats.deaths++;
    this.danger = clamp01(this.danger + 0.3);
    this.toast(`${a.name} ${why}.`, 'bad', a.x, a.z);
    this.spend(2000, 'Fines', true);
  }

  /** cuff a prisoner and send them to solitary (or their cell) */
  arrest(a: Agent, hours: number) {
    const p = a.p!;
    this.clearPlan(a);
    p.mode = 'cuffed';
    p.misconduct++;
    p.modeUntil = hours;
    this.setPlan(a, [{ t: 'do', dur: 1.5, pose: 'cuffed', hold: true, icon: 'cuffs', status: 'Restrained' }]);
  }

  /** pick somewhere to punish a prisoner; called from prisoner think when cuffed step ends */
  beginPunishment(a: Agent) {
    const p = a.p!;
    const hours = p.modeUntil || 6;
    let room: Room | undefined;
    for (const r of this.world.validRoomsOf(R.solitary)) {
      if (!this.solitaryOcc.has(r.tiles[0])) { room = r; break; }
    }
    if (room) {
      this.solitaryOcc.set(room.tiles[0], a.id);
      p.mode = 'solitary';
      p.modeUntil = this.time + hours * 60;
    } else {
      p.mode = 'punished';
      p.modeUntil = this.time + hours * 30;
      this.warn('nosolitary', 'No free Solitary cell: troublemakers are being locked in their own cells instead.', 600);
    }
    // an escort walks them there
    const g = this.nearestStaff(a, 'guard', 14, true);
    if (g) {
      g.s!.mode = 'escort';
      g.s!.targetId = a.id;
      this.clearPlan(g);
      this.setPlan(g, [{
        t: 'follow', target: a, range: 0.9, status: 'Escorting inmate',
        abort: () => a.dead || !a.p || (a.p.mode !== 'solitary' && a.p.mode !== 'punished') || (a.steps.length > 0 && a.steps[0].t === 'do'),
      }, { t: 'do', dur: 3, until: () => a.dead || (a.steps.length > 0 && a.steps[0].t === 'do'), done: () => { g.s!.mode = 'idle'; } }]);
    }
  }

  /** send guards (and riot police) to trouble */
  private dispatch() {
    const needs: { target: Agent; want: number }[] = [];
    for (const f of this.fights) needs.push({ target: f.a, want: 2 });
    for (const a of this.prisoners) {
      const m = a.p!.mode;
      if (m === 'escaping') needs.push({ target: a, want: 2 });
      else if (m === 'riot' && !this.inFight(a)) needs.push({ target: a, want: 1 });
    }
    if (!needs.length) return;
    const assigned = new Map<number, number>();
    for (const s of this.staff) if (s.s!.mode === 'respond') assigned.set(s.s!.targetId, (assigned.get(s.s!.targetId) ?? 0) + 1);
    for (const n of needs) {
      let have = assigned.get(n.target.id) ?? 0;
      while (have < n.want) {
        let best: Agent | null = null, bd = 90;
        for (const s of this.staff) {
          const sd = s.s!;
          if ((sd.role !== 'guard' && sd.role !== 'riot') || sd.mode === 'respond' || sd.mode === 'escort' || sd.mode === 'leave' || s.pose === 'down' || s.busy) continue;
          const d = Math.hypot(s.x - n.target.x, s.z - n.target.z);
          // escapes are only noticed if someone could plausibly see them
          if (n.target.p?.mode === 'escaping' && d > 16 && !this.counts.cctv && !this.towerSees(n.target)) continue;
          if (d < bd) { bd = d; best = s; }
        }
        if (!best) break;
        this.respond(best, n.target);
        have++;
      }
    }
  }

  towerSees(a: Agent): boolean {
    for (const o of this.world.objects.values()) {
      if (o.type !== 'guard_tower' || !o.built || !o.users.some((u) => u)) continue;
      if (Math.hypot(o.x + 1 - a.x, o.y + 1 - a.z) < 14) return true;
    }
    return false;
  }

  respond(g: Agent, target: Agent) {
    this.clearPlan(g);
    g.s!.mode = 'respond';
    g.s!.targetId = target.id;
    const stillTrouble = () => !target.dead && (!!this.inFight(target) || target.p?.mode === 'escaping' || target.p?.mode === 'riot');
    this.setPlan(g, [
      {
        t: 'follow', target, range: 1.1, run: true, status: 'Responding to incident', abort: () => !stillTrouble(),
        done: () => {
          const m = target.p?.mode;
          if (m === 'escaping') {
            this.toast(`${g.name} caught ${target.name} trying to escape.`, 'good', target.x, target.z);
            this.arrest(target, 12);
          } else if (m === 'riot' && !this.inFight(target)) {
            this.startFight(target, g);
            return;
          }
        },
      },
      { t: 'do', pose: 'fight', until: () => !this.inFight(target), dur: 30, status: 'Breaking up a fight' },
      { t: 'do', dur: 0.2, done: () => { g.s!.mode = 'idle'; g.s!.targetId = 0; } },
    ]);
  }

  private updateRiot() {
    const normal = this.prisoners.filter((a) => a.p!.mode === 'normal' || a.p!.mode === 'riot');
    if (!this.riot) {
      if (normal.length < 8) return;
      let sum = 0, hot = 0;
      for (const a of normal) {
        sum += a.p!.anger;
        if (a.p!.anger > 0.75) hot++;
      }
      if (sum / normal.length > 0.7 && hot / normal.length > 0.4 && rng.chance(0.05)) {
        this.riot = true;
        for (const a of normal) if (a.p!.anger > 0.6) {
          a.p!.mode = 'riot';
          this.clearPlan(a);
        }
        this.toast('RIOT! Inmates are attacking staff. Lock down and call for backup!', 'bad');
        this.bus.emit('riot', true);
      }
    } else {
      const rioters = this.prisoners.filter((a) => a.p!.mode === 'riot').length;
      if (!rioters) {
        this.riot = false;
        this.toast('The riot is over. Order has been restored.', 'good');
        this.bus.emit('riot', false);
        for (const s of this.staff) if (s.s!.role === 'riot') this.fire(s);
      }
    }
  }

  callRiotPolice() {
    const cost = 3000;
    if (!this.spend(cost, 'Emergency services')) {
      this.toast('Not enough money to call the riot squad.', 'bad');
      return;
    }
    for (let i = 0; i < 6; i++) this.spawnStaff('riot').name = `Riot Officer ${i + 1}`;
    this.toast('Riot squad deployed. They will leave when order is restored.', 'info', ENTRY_X, ENTRY_Y);
  }
  toggleLockdown() {
    this.lockdown = !this.lockdown;
    for (const a of this.prisoners) if (!a.busy) this.clearPlan(a);
    this.toast(this.lockdown ? 'LOCKDOWN: all inmates are returning to their cells.' : 'Lockdown lifted.', this.lockdown ? 'warn' : 'info');
    this.bus.emit('lockdown', this.lockdown);
  }
  shakedown() {
    if (this.time < this.shakedownUntil) return;
    this.shakedownUntil = this.time + 75;
    for (const a of this.prisoners) if (!a.busy) this.clearPlan(a);
    this.toast('Shakedown ordered: inmates return to cells while guards search for contraband.', 'warn');
    const until = this.shakedownUntil;
    const check = () => {
      if (this.time < until) return;
      let found = 0;
      for (const a of this.prisoners) {
        const p = a.p!;
        p.anger = clamp01(p.anger + 0.07);
        if (p.contraband && rng.chance(0.85)) {
          p.contraband = '';
          p.dig = 0;
          p.misconduct++;
          found++;
        }
      }
      this.stats.contraband += found;
      this.toast(found ? `Shakedown complete: ${found} item${found > 1 ? 's' : ''} of contraband seized.` : 'Shakedown complete: nothing found.', found ? 'good' : 'info');
      this.shakeHook = null;
      for (const a of this.prisoners) if (!a.busy) this.clearPlan(a);
    };
    this.shakeHook = check;
  }
  shakeHook: (() => void) | null = null;

  escaped(a: Agent, how = 'escaped over the perimeter') {
    a.dead = true;
    this.stats.escapes++;
    this.stats.lastEscapeDay = this.day;
    this.danger = clamp01(this.danger + 0.1);
    this.toast(`ESCAPE: ${a.name} ${how}! The state fines you $1,500.`, 'bad', a.x, a.z);
    this.spend(1500, 'Fines', true);
  }

  // ------------------------------------------------------------------ building API (used by tools)
  private bump() {
    this.planVersion++;
    this.world.dirtyPlans = true;
  }
  planWall(tile: number, type: number): boolean {
    const w = this.world;
    const x = tile % w.w, y = Math.floor(tile / w.w);
    if (x < 1 || y < 1 || x >= w.w - 1 || y >= w.h - 1) return false;
    if (w.objAt[tile]) return false;
    if ((w.wall[tile] === type && !w.planDoor[tile]) || w.planWall[tile] === type) return false;
    const cost = WALLS[type].cost;
    if (!this.spend(cost, 'Construction')) return false;
    this.refundPlan(tile);
    if (this.instantBuild) w.setWall(tile, type);
    else w.planWall[tile] = type;
    this.bump();
    return true;
  }
  planDoor(tile: number, type: number): boolean {
    const w = this.world;
    const x = tile % w.w, y = Math.floor(tile / w.w);
    if (x < 1 || y < 1 || x >= w.w - 1 || y >= w.h - 1) return false;
    if (w.objAt[tile]) return false;
    if (w.door[tile] === type || w.planDoor[tile] === type) return false;
    if (!this.spend(DOORS[type].cost, 'Construction')) return false;
    this.refundPlan(tile);
    if (this.instantBuild) w.setDoor(tile, type);
    else w.planDoor[tile] = type;
    this.bump();
    return true;
  }
  planFloor(tile: number, id: number): boolean {
    const w = this.world;
    if (w.floor[tile] === id && !w.planFloor[tile]) return false;
    if (w.planFloor[tile] === id + 1) return false;
    if (!this.spend(FLOORS[id].cost, 'Construction')) return false;
    if (w.planFloor[tile]) this.earn(FLOORS[w.planFloor[tile] - 1].cost, 'Construction');
    if (this.instantBuild || id === 0) {
      w.planFloor[tile] = 0;
      w.setFloor(tile, id);
    } else w.planFloor[tile] = id + 1;
    this.bump();
    return true;
  }
  placeObject(type: string, x: number, y: number, rot: number): WorldObject | null {
    const def = OBJ[type];
    if (!this.world.canPlace(type, x, y, rot)) return null;
    if (!this.spend(def.cost, 'Construction')) return null;
    const o = this.world.addObject(type, x, y, rot, this.instantBuild);
    this.bump();
    return o;
  }
  setZone(tile: number, type: number) {
    this.world.setZone(tile, type);
  }
  /** refund and clear any wall / door plan on a tile */
  private refundPlan(tile: number) {
    const w = this.world;
    if (w.planWall[tile]) {
      this.earn(WALLS[w.planWall[tile]].cost, 'Construction');
      w.planWall[tile] = 0;
    }
    if (w.planDoor[tile]) {
      this.earn(DOORS[w.planDoor[tile]].cost, 'Construction');
      w.planDoor[tile] = 0;
    }
  }
  /** demolish everything on a tile: plans are refunded in full, built objects at half price */
  bulldoze(tile: number) {
    const w = this.world;
    this.refundPlan(tile);
    if (w.planFloor[tile]) {
      this.earn(FLOORS[w.planFloor[tile] - 1].cost, 'Construction');
      w.planFloor[tile] = 0;
    }
    if (w.wall[tile]) w.setWall(tile, 0);
    if (w.door[tile]) w.setDoor(tile, 0);
    const oid = w.objAt[tile];
    if (oid) this.removeObject(oid);
    this.bump();
  }
  removeObject(oid: number) {
    const o = this.world.objects.get(oid);
    if (!o) return;
    const def = OBJ[o.type];
    this.earn(o.built ? Math.round(def.cost / 2) : def.cost, 'Construction');
    for (const u of o.users) {
      const a = u ? this.byId.get(u) : undefined;
      if (a && !a.busy) this.clearPlan(a);
    }
    this.world.removeObject(oid);
    this.bump();
  }

  /** open construction jobs (cached until plans change) */
  jobs(): Job[] {
    if (this.jobVersion === this.planVersion) return this.jobCache;
    this.jobVersion = this.planVersion;
    const w = this.world, out: Job[] = [];
    for (let i = 0; i < w.n; i++) {
      if (w.planWall[i]) out.push({ kind: 'wall', tile: i, objId: 0, key: i * 4 });
      else if (w.planDoor[i]) out.push({ kind: 'door', tile: i, objId: 0, key: i * 4 + 1 });
      if (w.planFloor[i]) out.push({ kind: 'floor', tile: i, objId: 0, key: i * 4 + 2 });
    }
    for (const o of w.objects.values()) if (!o.built) out.push({ kind: 'object', tile: w.idx(o.x, o.y), objId: o.id, key: -o.id });
    this.jobCache = out;
    return out;
  }
  completeJob(j: Job) {
    const w = this.world;
    switch (j.kind) {
      case 'wall':
        if (w.planWall[j.tile]) {
          const t = w.planWall[j.tile];
          w.planWall[j.tile] = 0;
          w.setWall(j.tile, t);
        }
        break;
      case 'door':
        if (w.planDoor[j.tile]) {
          const t = w.planDoor[j.tile];
          w.planDoor[j.tile] = 0;
          w.setDoor(j.tile, t);
        }
        break;
      case 'floor':
        if (w.planFloor[j.tile]) {
          const t = w.planFloor[j.tile] - 1;
          w.planFloor[j.tile] = 0;
          w.setFloor(j.tile, t);
        }
        break;
      case 'object': {
        const o = w.objects.get(j.objId);
        if (o) {
          o.built = true;
          o.progress = 1;
          w.dirtyObjects = true;
          w.dirtyTopo = true;
        }
        break;
      }
    }
    this.claims.delete(j.key);
    this.bump();
  }
  /** finish every outstanding plan immediately */
  finishAllPlans() {
    for (const j of [...this.jobs()]) this.completeJob(j);
  }

  // ------------------------------------------------------------------ objectives & rating
  objectives: Objective[] = OBJECTIVES;
  private checkObjectives() {
    for (const o of this.objectives) {
      if (this.objectivesDone.has(o.id)) continue;
      if (o.check(this)) {
        this.objectivesDone.add(o.id);
        this.earn(o.reward, 'Grants');
        this.toast(`Grant complete: ${o.title} (+${fmtMoney(o.reward)})`, 'good');
        this.bus.emit('objective', o);
      }
    }
    this.shakeHook?.();
  }
  hasRoom(type: number) {
    return this.world.validRoomsOf(type).length > 0;
  }
  countObjects(type: string) {
    let n = 0;
    for (const o of this.world.objects.values()) if (o.built && o.type === type) n++;
    return n;
  }
  /** averaged prisoner stats for the UI */
  averages() {
    const needs = new Array(NEEDS.length).fill(0);
    let anger = 0, health = 0;
    const n = this.prisoners.length;
    for (const a of this.prisoners) {
      const p = a.p!;
      for (let i = 0; i < needs.length; i++) needs[i] += p.needs[i];
      anger += p.anger;
      health += p.health;
    }
    if (n) {
      for (let i = 0; i < needs.length; i++) needs[i] /= n;
      anger /= n;
      health /= n;
    } else health = 1;
    return { needs, anger, health, n };
  }
  rating() {
    const av = this.averages();
    const wellbeing = 1 - av.needs.reduce((s, v) => s + v, 0) / av.needs.length;
    const order = 1 - av.anger;
    const safety = 1 - this.danger;
    const security = clamp01(1 - Math.max(0, 4 - (this.day - this.stats.lastEscapeDay)) * 0.2 * (this.stats.escapes ? 1 : 0));
    let reform = 0;
    for (const a of this.prisoners) reform += a.p!.reform;
    reform = av.n ? reform / av.n : 0;
    const overall = av.n ? (wellbeing * 0.28 + order * 0.24 + safety * 0.18 + security * 0.18 + av.health * 0.12) * 100 : 0;
    return { wellbeing, order, safety, security, health: av.health, reform, overall };
  }
  /** room tiles from which a prisoner could walk off the map */
  breaches(): Room[] {
    const out: Room[] = [];
    const w = this.world;
    for (const r of w.rooms.values()) {
      const def = ROOMS[r.type];
      if (['reception', 'storage', 'warden', 'security', 'staffroom', 'armoury', 'psych'].includes(def.key)) continue;
      if (r.tiles.some((t) => w.escapeDist[t] !== 65535)) out.push(r);
    }
    return out;
  }

  // ------------------------------------------------------------------ save / load
  serialize() {
    return {
      v: 1,
      name: this.name,
      world: this.world.serialize(),
      time: this.time, money: this.money, regime: this.regime, intake: this.intake, lockdown: this.lockdown, meals: this.meals, laundry: this.laundry,
      danger: this.danger, stats: this.stats, objectivesDone: [...this.objectivesDone], ledgerToday: this.ledgerToday,
      ledgerYesterday: this.ledgerYesterday, history: this.history, nextAgentId: peekAgentId(), instantBuild: this.instantBuild,
      agents: this.agents.filter((a) => a.kind !== 'visitor' && !a.dead).map((a) => ({
        id: a.id, kind: a.kind, name: a.name, x: +a.x.toFixed(2), z: +a.z.toFixed(2), look: a.look, speed: a.speed,
        p: a.p ? { ...a.p, needs: Array.from(a.p.needs) } : undefined,
        s: a.s,
      })),
    };
  }
  static load(d: any, world = new World()): Sim | null {
    if (!world.load(d.world)) return null;
    const s = new Sim(world);
    s.name = d.name ?? s.name;
    s.time = d.time;
    s.money = d.money;
    s.regime = d.regime;
    s.intake = d.intake;
    s.lockdown = d.lockdown;
    s.meals = d.meals;
    s.laundry = d.laundry ?? 0;
    s.danger = d.danger;
    Object.assign(s.stats, d.stats);
    s.objectivesDone = new Set(d.objectivesDone);
    s.ledgerToday = d.ledgerToday ?? {};
    s.ledgerYesterday = d.ledgerYesterday ?? {};
    s.history = d.history ?? [];
    s.instantBuild = !!d.instantBuild;
    for (const ad of d.agents as any[]) {
      const a = new Agent(ad.kind, ad.look);
      a.id = ad.id;
      a.name = ad.name;
      a.x = ad.x;
      a.z = ad.z;
      a.speed = ad.speed;
      if (ad.p) {
        const p = ad.p as PrisonerData;
        a.p = { ...p, needs: Float32Array.from(ad.p.needs), escortedBy: 0 };
        a.pass = PASS_PRISONER;
        if (['fight', 'cuffed', 'down'].includes(a.p.mode)) a.p.mode = 'normal';
        a.p.nextRoll = s.time + rng.range(5, 15);
      }
      if (ad.s) {
        a.s = { ...ad.s, targetId: 0, jobId: 0 };
        if (a.s!.mode !== 'leave') a.s!.mode = 'idle';
        a.pass = PASS_STAFF;
      }
      s.addAgent(a);
    }
    resetAgentIds(d.nextAgentId ?? 100000);
    s.sync();
    return s;
  }
}

function footprintOf(o: WorldObject) {
  return footprint(OBJ[o.type], o.rot);
}
export { footprintOf };

const OBJECTIVES: Objective[] = [
  { id: 'cells', title: 'First Cells', desc: 'Build 6 valid cells (bed, toilet, cell door).', reward: 4000, check: (s) => s.world.validRoomsOf(R.cell).length >= 6 },
  { id: 'food', title: 'Three Square Meals', desc: 'Build a kitchen and a canteen, and hire a cook.', reward: 3000, check: (s) => s.hasRoom(R.kitchen) && s.hasRoom(R.canteen) && s.counts.cooks > 0 },
  { id: 'showers', title: 'Stay Clean', desc: 'Build a shower room.', reward: 1500, check: (s) => s.hasRoom(R.showers) },
  { id: 'yard', title: 'Open Air', desc: 'Designate a secure yard no inmate can walk out of.', reward: 2500, check: (s) => s.world.validRoomsOf(R.yard).some((r) => r.tiles.every((t) => s.world.escapeDist[t] === 65535)) },
  { id: 'warden', title: 'Chain of Command', desc: "Build a Warden's Office and hire a Warden.", reward: 3000, check: (s) => s.hasRoom(R.warden) && s.counts.warden > 0 },
  { id: 'guards', title: 'On Patrol', desc: 'Employ 4 guards and build a Security Office.', reward: 2500, check: (s) => s.counts.guards >= 4 && s.hasRoom(R.security) },
  { id: 'pop20', title: 'Full House', desc: 'Hold 20 inmates.', reward: 6000, check: (s) => s.prisoners.length >= 20 },
  { id: 'medical', title: 'Medical Wing', desc: 'Build an infirmary and hire a doctor.', reward: 4000, check: (s) => s.hasRoom(R.infirmary) && s.counts.doctors > 0 },
  { id: 'work', title: 'Idle Hands', desc: 'Build a workshop or a laundry.', reward: 3500, check: (s) => s.hasRoom(R.workshop) || s.hasRoom(R.laundry) },
  { id: 'school', title: 'Second Chances', desc: 'Build a classroom and hire a teacher.', reward: 3500, check: (s) => s.hasRoom(R.classroom) && s.counts.teachers > 0 },
  { id: 'family', title: 'Family Ties', desc: 'Build a visitation room and install 2 phone booths.', reward: 2500, check: (s) => s.hasRoom(R.visitation) && s.countObjects('phone') >= 2 },
  { id: 'cctv', title: 'Eyes Everywhere', desc: 'Install 4 CCTV cameras and a CCTV console.', reward: 3000, check: (s) => s.countObjects('cctv') >= 4 && s.countObjects('cctv_monitor') >= 1 },
  { id: 'solitary', title: 'The Hole', desc: 'Build 2 solitary cells.', reward: 2000, check: (s) => s.world.validRoomsOf(R.solitary).length >= 2 },
  { id: 'faith', title: 'Soul Searching', desc: 'Build a chapel or a library.', reward: 2500, check: (s) => s.hasRoom(R.chapel) || s.hasRoom(R.library) },
  { id: 'pop50', title: 'Big House', desc: 'Hold 50 inmates.', reward: 15000, check: (s) => s.prisoners.length >= 50 },
  { id: 'secure', title: 'No Way Out', desc: 'Go 3 days without an escape while holding 15+ inmates.', reward: 5000, check: (s) => s.prisoners.length >= 15 && s.day - Math.max(1, s.stats.lastEscapeDay) >= 3 },
  { id: 'model', title: 'Model Prison', desc: 'Reach a rating of 85 with 30+ inmates.', reward: 20000, check: (s) => s.prisoners.length >= 30 && s.rating().overall >= 85 },
];
