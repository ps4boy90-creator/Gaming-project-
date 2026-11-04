import * as THREE from 'three';
import { Builder, Collide, Place, rotXZ } from './builder';
import { Materials, DECK_COLORS } from './materials';
import { CollisionWorld } from '../collision';
import { Door } from './doors';
import { LightPool } from './lights';
import { atlasQuad, drawDoorSign, drawScreen, drawStencil, drawPoster, ScreenKind } from './atlas';

export type Ambience = 'hab' | 'vault' | 'hangar' | 'spine' | 'lift' | 'machine' | 'garden';

export interface Room {
  id: string;
  name: string;
  deck: string; // command | crew | science | spine | aft
  x0: number;
  x1: number;
  z0: number;
  z1: number;
  y0: number;
  y1: number;
  ambience: Ambience;
}

export interface Seat {
  id: string;
  kind: 'sit' | 'lie';
  x: number;
  y: number; // seat surface height
  z: number;
  yaw: number;
  exitX: number;
  exitZ: number;
  label: string;
  sleep?: boolean;
}

export interface Item {
  id: string;
  min: [number, number, number];
  max: [number, number, number];
  prompt: string;
  action: string;
  data?: unknown;
  range?: number;
}

export interface Opening {
  at: number;
  w: number;
  y0: number;
  y1: number;
  kind: 'door' | 'window' | 'gap' | 'inner';
  locked?: boolean;
  heavy?: boolean;
  label?: string;
  /** Plate above the door: [code, name, deckKey, sub?] on the given side (+1/-1 along wall normal). */
  sign?: { code: string; name: string; deck: string; sub?: string; side: 1 | -1; both?: boolean };
  /** Door id for lookups (lift doors). */
  id?: string;
}

export interface WallOpts {
  h?: number;
  t?: number;
  mat?: string;
  openings?: Opening[];
  accent?: string; // deck key for the painted stripe
  skirting?: boolean;
  offset?: number;
  collide?: Collide;
}

export const yawFacing = (dx: number, dz: number) => Math.atan2(-dx, -dz);

/** Construction kit: walls with doors and windows, rooms with lights, signs, seats, items. */
export class Kit {
  b: Builder;
  doors: Door[] = [];
  doorById = new Map<string, Door>();
  rooms: Room[] = [];
  seats: Seat[] = [];
  items: Item[] = [];
  private n = 0;
  private screenCache = new Map<string, ReturnType<typeof drawScreen>>();

  constructor(
    public mats: Materials,
    public world: CollisionWorld,
    public interior: THREE.Object3D,
    public lights: LightPool,
  ) {
    this.b = new Builder(mats, world);
  }

  uid(prefix: string): string {
    return `${prefix}-${++this.n}`;
  }

  // ------------------------------------------------------------------ walls

  /** Wall at constant z running along x from x0 to x1. */
  wallZ(z: number, x0: number, x1: number, y: number, o: WallOpts = {}): void {
    this.wall('z', z, x0, x1, y, o);
  }

  /** Wall at constant x running along z from z0 to z1. */
  wallX(x: number, z0: number, z1: number, y: number, o: WallOpts = {}): void {
    this.wall('x', x, z0, z1, y, o);
  }

  private wall(axis: 'x' | 'z', c: number, a0: number, a1: number, y: number, o: WallOpts): void {
    const h = o.h ?? 3;
    const t = o.t ?? 0.2;
    const mat = o.mat ?? 'wall';
    const off = o.offset ?? 0;
    const collide = o.collide ?? 'wall';
    const b = this.b;
    const emit = (u0: number, u1: number, v0: number, v1: number, key: string, tt = t, col: Collide = collide, round = 0) => {
      if (u1 - u0 < 1e-3 || v1 - v0 < 1e-3) return;
      if (axis === 'z') b.box(u0, y + v0, c - tt / 2 + off, u1, y + v1, c + tt / 2 + off, key, col, round);
      else b.box(c - tt / 2 + off, y + v0, u0, c + tt / 2 + off, y + v1, u1, key, col, round);
    };
    const ops = [...(o.openings ?? [])].sort((p, q) => p.at - q.at);
    const solid: [number, number][] = [];
    let cursor = a0;
    for (const op of ops) {
      const oa = op.at - op.w / 2;
      const ob = op.at + op.w / 2;
      emit(cursor, oa, 0, h, mat);
      solid.push([cursor, oa]);
      emit(oa, ob, op.y1, h, mat);
      if (op.y0 > 0) emit(oa, ob, 0, op.y0, mat);
      cursor = ob;
      this.opening(axis, c + off, y, t, op);
    }
    emit(cursor, a1, 0, h, mat);
    solid.push([cursor, a1]);
    if (o.accent) {
      const key = `accent-${o.accent}`;
      for (const [s0, s1] of solid) emit(s0, s1, 1.02, 1.12, key, t + 0.024, false);
    }
    if (o.skirting !== false) {
      for (const [s0, s1] of solid) emit(s0, s1, 0, 0.1, 'rubber', t + 0.03, false);
    }
  }

  private opening(axis: 'x' | 'z', c: number, y: number, t: number, op: Opening): void {
    const b = this.b;
    // box helper in wall space: along a, height v (relative to floor), across n (relative to wall centre)
    const box = (a0: number, a1: number, v0: number, v1: number, n0: number, n1: number, key: string, col: Collide = false) => {
      if (axis === 'z') b.box(a0, y + v0, c + n0, a1, y + v1, c + n1, key, col);
      else b.box(c + n0, y + v0, a0, c + n1, y + v1, a1, key, col);
    };
    const oa = op.at - op.w / 2;
    const ob = op.at + op.w / 2;
    const ft = 0.07; // frame thickness
    const fd = t / 2 + 0.035; // frame depth from centre
    if (op.kind === 'door') {
      box(oa - ft, oa, 0, op.y1 + ft, -fd, fd, 'metal');
      box(ob, ob + ft, 0, op.y1 + ft, -fd, fd, 'metal');
      box(oa - ft, ob + ft, op.y1, op.y1 + ft, -fd, fd, 'metal');
      box(oa, ob, 0, 0.012, -fd - 0.12, fd + 0.12, 'hazard');
      const pos = axis === 'z' ? { x: op.at, z: c } : { x: c, z: op.at };
      const door = new Door(this.interior, this.mats, this.world, {
        axis: axis === 'z' ? 'x' : 'z',
        x: pos.x,
        y,
        z: pos.z,
        width: op.w,
        height: op.y1,
        locked: op.locked,
        label: op.label,
        heavy: op.heavy,
      });
      this.doors.push(door);
      if (op.id) this.doorById.set(op.id, door);
      if (op.sign) {
        const sides: (1 | -1)[] = op.sign.both ? [1, -1] : [op.sign.side];
        const rect = drawDoorSign(this.mats.signs, op.sign.code, op.sign.name, DECK_COLORS[op.sign.deck] ?? '#888', op.sign.sub);
        for (const s of sides) {
          const n = s * (t / 2 + 0.02);
          const p = axis === 'z' ? new THREE.Vector3(op.at, y + op.y1 + 0.3, c + n) : new THREE.Vector3(c + n, y + op.y1 + 0.3, op.at);
          this.quad(rect, 1.24, 0.31, p, axis === 'z' ? (s > 0 ? 0 : Math.PI) : s > 0 ? Math.PI / 2 : -Math.PI / 2);
        }
      }
      if (op.locked && op.label) {
        const mid = axis === 'z' ? [op.at, c] : [c, op.at];
        this.item({
          id: this.uid('locked'),
          min: [mid[0] - (axis === 'z' ? op.w / 2 : 0.4), y + 0.6, mid[1] - (axis === 'z' ? 0.4 : op.w / 2)],
          max: [mid[0] + (axis === 'z' ? op.w / 2 : 0.4), y + 2.2, mid[1] + (axis === 'z' ? 0.4 : op.w / 2)],
          prompt: op.label,
          action: 'locked',
          data: op.label,
        });
      }
    } else if (op.kind === 'window' || op.kind === 'inner') {
      box(oa - ft, oa, op.y0 - ft, op.y1 + ft, -fd, fd, 'metal');
      box(ob, ob + ft, op.y0 - ft, op.y1 + ft, -fd, fd, 'metal');
      box(oa - ft, ob + ft, op.y1, op.y1 + ft, -fd, fd, 'metal');
      if (op.y0 > 0.05) box(oa - ft, ob + ft, op.y0 - ft, op.y0, -fd - 0.06, fd + 0.06, 'metal');
      // mullions for wide panes
      const panes = Math.max(1, Math.round(op.w / 2.4));
      for (let i = 1; i < panes; i++) {
        const m = oa + (op.w * i) / panes;
        box(m - 0.04, m + 0.04, op.y0, op.y1, -fd + 0.02, fd - 0.02, 'metal');
      }
      box(oa, ob, op.y0, op.y1, -0.012, 0.012, op.kind === 'window' ? 'glass' : 'glassInner', 'wall');
    }
  }

  // ------------------------------------------------------------------ rooms

  room(
    r: Omit<Room, 'y1'> & { h?: number },
    opts: {
      floor?: string;
      ceil?: string | null;
      lights?: 'grid' | 'none' | 'strip';
      lightColor?: number;
      lightMat?: string;
      intensity?: number;
      spacing?: number;
      beams?: boolean;
    } = {},
  ): Room {
    const h = r.h ?? 3;
    const room: Room = { id: r.id, name: r.name, deck: r.deck, x0: r.x0, x1: r.x1, z0: r.z0, z1: r.z1, y0: r.y0, y1: r.y0 + h, ambience: r.ambience };
    this.rooms.push(room);
    const b = this.b;
    b.box(r.x0, r.y0 - 0.2, r.z0, r.x1, r.y0, r.z1, opts.floor ?? 'floor', 'solid');
    if (opts.ceil !== null) {
      b.box(r.x0, r.y0 + h, r.z0, r.x1, r.y0 + h + 0.25, r.z1, opts.ceil ?? 'ceil', 'solid');
      if (opts.beams !== false) {
        const along = r.x1 - r.x0 >= r.z1 - r.z0 ? 'x' : 'z';
        const len = along === 'x' ? r.x1 - r.x0 : r.z1 - r.z0;
        const n = Math.max(1, Math.floor(len / 2.4));
        for (let i = 1; i < n; i++) {
          const p = (along === 'x' ? r.x0 : r.z0) + (len * i) / n;
          if (along === 'x') b.box(p - 0.09, r.y0 + h - 0.16, r.z0, p + 0.09, r.y0 + h, r.z1, 'paintGrey', false);
          else b.box(r.x0, r.y0 + h - 0.16, p - 0.09, r.x1, r.y0 + h, p + 0.09, 'paintGrey', false);
        }
      }
    }
    const mode = opts.lights ?? 'grid';
    if (mode !== 'none') this.fixtures(room, h, opts);
    return room;
  }

  private fixtures(
    r: Room,
    h: number,
    opts: { lightColor?: number; lightMat?: string; intensity?: number; spacing?: number; lights?: string },
  ): void {
    const sx = r.x1 - r.x0;
    const sz = r.z1 - r.z0;
    const spacing = opts.spacing ?? 3.2;
    const nx = Math.max(1, Math.round(sx / spacing));
    const nz = Math.max(1, Math.round(sz / spacing));
    const color = new THREE.Color(opts.lightColor ?? 0xfff1e0);
    const intensity = opts.intensity ?? 7;
    const mat = opts.lightMat ?? 'light';
    const yTop = r.y0 + h;
    const strip = opts.lights === 'strip';
    for (let i = 0; i < nx; i++) {
      for (let k = 0; k < nz; k++) {
        const x = r.x0 + (sx * (i + 0.5)) / nx;
        const z = r.z0 + (sz * (k + 0.5)) / nz;
        const alongX = sx >= sz;
        const lx = strip ? (alongX ? sx / nx - 0.4 : 0.22) : alongX ? 1.3 : 0.3;
        const lz = strip ? (alongX ? 0.22 : sz / nz - 0.4) : alongX ? 0.3 : 1.3;
        this.b.box(x - lx / 2 - 0.05, yTop - 0.05, z - lz / 2 - 0.05, x + lx / 2 + 0.05, yTop, z + lz / 2 + 0.05, 'metal', false);
        this.b.box(x - lx / 2, yTop - 0.07, z - lz / 2, x + lx / 2, yTop - 0.04, z + lz / 2, mat, false);
      }
    }
    // pool anchors: one per ~4.5 m, slightly below the ceiling
    const ax = Math.max(1, Math.round(sx / 4.5));
    const az = Math.max(1, Math.round(sz / 4.5));
    for (let i = 0; i < ax; i++) {
      for (let k = 0; k < az; k++) {
        this.lights.add({
          x: r.x0 + (sx * (i + 0.5)) / ax,
          y: yTop - 0.35,
          z: r.z0 + (sz * (k + 0.5)) / az,
          color,
          intensity: intensity * Math.min(2.2, Math.max(1, (sx * sz) / (ax * az * 14))),
          distance: Math.max(7, Math.min(16, Math.hypot(sx / ax, sz / az) * 1.6 + h)),
        });
      }
    }
  }

  // ------------------------------------------------------------------ decals, screens

  quad(rect: ReturnType<typeof drawDoorSign>, w: number, h: number, pos: THREE.Vector3, yaw: number, key = 'sign'): void {
    this.b.geo(atlasQuad(w, h, rect), key, pos, new THREE.Euler(0, yaw, 0));
  }

  /** Painted stencil on a wall face. `yaw` is the facing direction. */
  stencil(text: string, deck: string, pos: THREE.Vector3, yaw: number, height = 0.6, seed = 1): void {
    const rect = drawStencil(this.mats.signs, text, DECK_COLORS[deck] ?? '#ddd', 640, 96, seed);
    this.quad(rect, height * (640 / 96), height, pos, yaw);
  }

  poster(title: string, lines: string[], deck: string, pos: THREE.Vector3, yaw: number): void {
    const rect = drawPoster(this.mats.signs, title, lines, DECK_COLORS[deck] ?? '#ddd');
    this.quad(rect, 0.6, 0.8, pos, yaw);
  }

  /** Wall-mounted or console screen with a bezel. */
  screen(kind: ScreenKind, pos: THREE.Vector3, yaw: number, w = 0.8, seed = 1, label = '', tilt = 0): void {
    const h = w * (320 / 512);
    const key = `${kind}:${seed}:${label}`;
    let rect = this.screenCache.get(key);
    if (!rect) {
      rect = drawScreen(this.mats.screens, kind, seed, label);
      this.screenCache.set(key, rect);
    }
    const rot = new THREE.Euler(-tilt, yaw, 0, 'YXZ');
    const fwd = new THREE.Vector3(0, 0, 1).applyEuler(rot);
    const bezel = new THREE.BoxGeometry(w + 0.06, h + 0.06, 0.04);
    this.b.geo(bezel, 'paintDark', pos.clone().addScaledVector(fwd, -0.025), rot);
    this.b.geo(atlasQuad(w, h, rect), 'screen', pos, rot);
  }

  // ------------------------------------------------------------------ seats & items

  /** Seat in local placement coordinates; occupant faces local +z. */
  seat(p: Place, lx: number, ly: number, lz: number, label: string, kind: 'sit' | 'lie' = 'sit', sleep = false, exit = 0.75): Seat {
    const [x, z] = rotXZ(lx, lz, p.rot);
    const [fx, fz] = rotXZ(0, 1, p.rot);
    const s: Seat = {
      id: this.uid('seat'),
      kind,
      x: p.x + x,
      y: p.y + ly,
      z: p.z + z,
      yaw: yawFacing(fx, fz),
      exitX: p.x + x + fx * exit,
      exitZ: p.z + z + fz * exit,
      label,
      sleep,
    };
    if (kind === 'lie') {
      // exit to the side of the bed
      const [sx, sz] = rotXZ(1, 0, p.rot);
      s.exitX = p.x + x + sx * exit;
      s.exitZ = p.z + z + sz * exit;
    }
    this.seats.push(s);
    const r = kind === 'lie' ? 0.45 : 0.3;
    this.items.push({
      id: s.id,
      min: [s.x - r, s.y - 0.25, s.z - r],
      max: [s.x + r, s.y + 0.35, s.z + r],
      prompt: kind === 'lie' ? `Lie down · ${label}` : `Sit · ${label}`,
      action: 'seat',
      data: s,
    });
    return s;
  }

  item(i: Item): Item {
    this.items.push(i);
    return i;
  }

  /** Item box in local placement coordinates. */
  pitem(p: Place, x0: number, y0: number, z0: number, x1: number, y1: number, z1: number, prompt: string, action: string, data?: unknown, range?: number): Item {
    const [ax, az] = rotXZ(x0, z0, p.rot);
    const [bx, bz] = rotXZ(x1, z1, p.rot);
    return this.item({
      id: this.uid(action),
      min: [p.x + Math.min(ax, bx), p.y + y0, p.z + Math.min(az, bz)],
      max: [p.x + Math.max(ax, bx), p.y + y1, p.z + Math.max(az, bz)],
      prompt,
      action,
      data,
      range,
    });
  }

  roomAt(x: number, y: number, z: number): Room | null {
    let best: Room | null = null;
    for (const r of this.rooms) {
      if (x >= r.x0 && x <= r.x1 && z >= r.z0 && z <= r.z1 && y >= r.y0 - 0.5 && y <= r.y1) {
        // prefer the smallest containing room (lift car inside lobby, etc.)
        if (!best || (r.x1 - r.x0) * (r.z1 - r.z0) < (best.x1 - best.x0) * (best.z1 - best.z0)) best = r;
      }
    }
    return best;
  }
}
