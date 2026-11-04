import * as THREE from 'three';
import { Builder, Collide, Place, rotXZ } from './builder';
import { Materials, DECK_COLORS } from './materials';
import { CollisionWorld } from '../collision';
import { Door } from './doors';
import { LightPool } from './lights';
import { atlasQuad, drawDoorSign, drawScreen, drawStencil, drawPoster, drawGraphic, ScreenKind } from './atlas';

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

export type Profile = 'room' | 'corridor' | 'hex' | 'hall' | 'hangar' | 'none';

/** Mesh yaw that makes a +z-facing object face into the room from a side's wall. */
function yawFor(s: { axis: 'x' | 'z'; dir: number }): number {
  return s.axis === 'z' ? (s.dir > 0 ? 0 : Math.PI) : s.dir > 0 ? Math.PI / 2 : -Math.PI / 2;
}

/** Construction kit: walls with doors and windows, rooms with lights, signs, seats, items. */
export class Kit {
  b: Builder;
  doors: Door[] = [];
  doorById = new Map<string, Door>();
  rooms: Room[] = [];
  seats: Seat[] = [];
  items: Item[] = [];
  private n = 0;
  /** Every door/window/gap cut so far, so dressing can avoid them. */
  openings: { axis: 'x' | 'z'; c: number; a0: number; a1: number; y: number; y1: number }[] = [];
  private pendingShells: { room: Room; h: number; profile: Profile; opts: { lightMat?: string; rib?: number } }[] = [];
  /** Light shafts to add as additive cones (hangar). */
  cones: { x: number; y: number; z: number; h: number }[] = [];
  private graphicCache = new Map<string, ReturnType<typeof drawGraphic>>();

  /** Painted wall graphic in the decal atlas (cached by text + style). */
  graphicRect(text: string, o: Parameters<typeof drawGraphic>[2] = {}): ReturnType<typeof drawGraphic> {
    const key = `${text}|${JSON.stringify(o)}`;
    let r = this.graphicCache.get(key);
    if (!r) {
      r = drawGraphic(this.mats.graphics, text, o);
      this.graphicCache.set(key, r);
    }
    return r;
  }

  /** Painted graphic placed on a wall face. */
  graphic(text: string, pos: THREE.Vector3, yaw: number, w: number, h: number, o: Parameters<typeof drawGraphic>[2] = {}): void {
    this.b.geo(atlasQuad(w, h, this.graphicRect(text, o)), 'decal', pos, new THREE.Euler(0, yaw, 0));
  }
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
      const pad0 = op.kind === 'door' ? 1.15 : 0.12;
      const pad1 = op.kind === 'door' ? 0.55 : 0.12;
      this.openings.push({ axis, c: c + off, a0: oa - pad0, a1: ob + pad1, y, y1: op.y1 });
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
    if (op.kind === 'door') {
      const heavy = !!op.heavy;
      const ft = heavy ? 0.22 : 0.15; // collar width
      const fd = t / 2 + (heavy ? 0.09 : 0.06); // collar depth from centre
      const leaf = heavy ? 0.07 : 0.045; // half thickness kept clear for the leaves
      const frameKey = heavy ? 'ribDark' : 'rib';
      box(oa - ft, oa, 0, op.y1 + ft, -fd, fd, frameKey);
      box(ob, ob + ft, 0, op.y1 + ft, -fd, fd, frameKey);
      box(oa - ft, ob + ft, op.y1, op.y1 + ft, -fd, fd, frameKey);
      if (heavy) {
        box(oa - ft + 0.03, oa - 0.03, 0.3, op.y1 - 0.3, -fd - 0.01, -fd, 'hazard');
        box(oa - ft + 0.03, oa - 0.03, 0.3, op.y1 - 0.3, fd, fd + 0.01, 'hazard');
        box(ob + 0.03, ob + ft - 0.03, 0.3, op.y1 - 0.3, -fd - 0.01, -fd, 'hazard');
        box(ob + 0.03, ob + ft - 0.03, 0.3, op.y1 - 0.3, fd, fd + 0.01, 'hazard');
      }
      // angled top corners on both faces (the leaves slide between them)
      const s = heavy ? 0.42 : 0.32;
      for (const [n0, n1] of [[leaf, fd], [-fd, -leaf]] as const) {
        this.corner(axis, c, y, oa, op.y1, 1, -1, s, n0, n1, frameKey);
        this.corner(axis, c, y, ob, op.y1, -1, -1, s, n0, n1, frameKey);
      }
      box(oa, ob, 0, 0.014, -fd - 0.12, fd + 0.12, 'hazard');
      if (heavy) {
        const rect = this.graphicRect('PRESSURE DOOR · KEEP CLEAR', { band: '#e2a21b', fg: '#141414', chevrons: true });
        for (const sd of [1, -1]) {
          const n = sd * (fd + 0.012);
          const p = axis === 'z' ? new THREE.Vector3(op.at, y + op.y1 + ft + 0.1, c + n) : new THREE.Vector3(c + n, y + op.y1 + ft + 0.1, op.at);
          this.b.geo(atlasQuad(Math.min(op.w + 0.6, 2.4), 0.16, rect), 'decal', p, new THREE.Euler(0, axis === 'z' ? (sd > 0 ? 0 : Math.PI) : sd > 0 ? Math.PI / 2 : -Math.PI / 2, 0));
        }
      }
      // control panels beside the door, both faces
      for (const side of [1, -1]) {
        const n0 = side > 0 ? fd - 0.02 : -fd - 0.03;
        const n1 = side > 0 ? fd + 0.03 : -fd + 0.02;
        box(ob + ft + 0.08, ob + ft + 0.26, 1.12, 1.46, n0, n1, 'paintDark');
        const f0 = side > 0 ? n1 : n0 - 0.006;
        const f1 = side > 0 ? n1 + 0.006 : n0;
        box(ob + ft + 0.12, ob + ft + 0.22, 1.36, 1.41, f0, f1, op.locked ? 'statusRed' : 'statusGreen');
        box(ob + ft + 0.12, ob + ft + 0.22, 1.18, 1.3, f0, f1, 'ledStrip');
      }
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
        for (const sd of sides) {
          const n = sd * (t / 2 + 0.012);
          const along = oa - ft - 0.56;
          const p = axis === 'z' ? new THREE.Vector3(along, y + 1.62, c + n) : new THREE.Vector3(c + n, y + 1.62, along);
          this.quad(rect, 0.84, 0.21, p, axis === 'z' ? (sd > 0 ? 0 : Math.PI) : sd > 0 ? Math.PI / 2 : -Math.PI / 2);
        }
      }
      if (op.locked && op.label) {
        const mid = axis === 'z' ? [op.at, c] : [c, op.at];
        this.item({
          id: this.uid('locked'),
          min: [mid[0] - (axis === 'z' ? op.w / 2 : 0.4), y + 0.6, mid[1] - (axis === 'z' ? 0.4 : op.w / 2)],
          max: [mid[0] + (axis === 'z' ? op.w / 2 : 0.4), y + 2.1, mid[1] + (axis === 'z' ? 0.4 : op.w / 2)],
          prompt: op.label,
          action: 'locked',
          data: op.label,
        });
      }
    } else if (op.kind === 'window' || op.kind === 'inner') {
      const ft = 0.12;
      const fd = t / 2 + 0.07;
      box(oa - ft, oa, op.y0 - ft, op.y1 + ft, -fd, fd, 'ribDark');
      box(ob, ob + ft, op.y0 - ft, op.y1 + ft, -fd, fd, 'ribDark');
      box(oa - ft, ob + ft, op.y1, op.y1 + ft, -fd, fd, 'ribDark');
      if (op.y0 > 0.05) box(oa - ft, ob + ft, op.y0 - ft, op.y0, -fd - 0.08, fd + 0.08, 'ribDark');
      // heavy mullions for wide panes
      const panes = Math.max(1, Math.round(op.w / 2.2));
      for (let i = 1; i < panes; i++) {
        const m = oa + (op.w * i) / panes;
        box(m - 0.07, m + 0.07, op.y0, op.y1, -fd + 0.02, fd - 0.02, 'ribDark');
      }
      // angled corners: an octagonal viewport
      const s = Math.min(0.3, (op.y1 - op.y0) * 0.22, op.w * 0.2);
      for (const [a, sa] of [[oa, 1], [ob, -1]] as const) {
        this.corner(axis, c, y, a, op.y1, sa, -1, s, -fd, fd, 'ribDark');
        if (op.y0 > 0.05) this.corner(axis, c, y, a, op.y0, sa, 1, s, -fd, fd, 'ribDark');
      }
      box(oa, ob, op.y0, op.y1, -0.012, 0.012, op.kind === 'window' ? 'glass' : 'glassInner', 'wall');
    }
  }

  /** Triangular corner gusset in a wall plane: right angle at (a, v), legs along sa·along and sv·up. */
  private corner(axis: 'x' | 'z', c: number, y: number, a: number, v: number, sa: number, sv: number, s: number, n0: number, n1: number, key: string): void {
    const sh = new THREE.Shape();
    sh.moveTo(0, 0);
    sh.lineTo(sa * s, 0);
    sh.lineTo(0, sv * s);
    sh.closePath();
    const g = new THREE.ExtrudeGeometry(sh, { depth: n1 - n0, bevelEnabled: false });
    if (axis === 'z') this.b.geo(g, key, new THREE.Vector3(a, y + v, c + n0));
    else this.b.geo(g, key, new THREE.Vector3(c + n1, y + v, a), new THREE.Euler(0, -Math.PI / 2, 0));
  }

  /** True if any door/window/gap on this wall line overlaps [a0, a1]. */
  blocked(axis: 'x' | 'z', c: number, y: number, a0: number, a1: number): boolean {
    return this.openings.some((o) => o.axis === axis && Math.abs(o.c - c) < 0.36 && Math.abs(o.y - y) < 0.6 && o.a1 > a0 && o.a0 < a1);
  }

  // ------------------------------------------------------------------ rooms

  room(
    r: Omit<Room, 'y1'> & { h?: number },
    opts: {
      floor?: string;
      ceil?: string | null;
      lights?: 'auto' | 'grid' | 'none' | 'strip';
      lightColor?: number;
      lightMat?: string;
      intensity?: number;
      spacing?: number;
      beams?: boolean;
      profile?: Profile;
      rib?: number;
      cones?: boolean;
    } = {},
  ): Room {
    const h = r.h ?? 2.6;
    const room: Room = { id: r.id, name: r.name, deck: r.deck, x0: r.x0, x1: r.x1, z0: r.z0, z1: r.z1, y0: r.y0, y1: r.y0 + h, ambience: r.ambience };
    this.rooms.push(room);
    const profile = opts.profile ?? 'room';
    const b = this.b;
    const floorKey = opts.floor ?? (profile === 'corridor' || profile === 'hex' || profile === 'hangar' || profile === 'hall' ? 'deckPlate' : 'floor');
    b.box(r.x0, r.y0 - 0.2, r.z0, r.x1, r.y0, r.z1, floorKey, 'solid');
    if (opts.ceil !== null) b.box(r.x0, r.y0 + h, r.z0, r.x1, r.y0 + h + 0.25, r.z1, opts.ceil ?? 'ceil', 'solid');
    this.pendingShells.push({ room, h, profile, opts });
    const mode = opts.lights ?? 'auto';
    if (mode === 'grid') this.fixtures(room, h, opts);
    if (mode !== 'none') this.anchors(room, h, opts);
    return room;
  }

  /** Build the structural shells once every wall (and so every opening) exists. */
  finishShells(): void {
    for (const s of this.pendingShells) {
      if (s.profile === 'room' || s.profile === 'corridor' || s.profile === 'hex' || s.profile === 'hall') this.shipShell(s.room, s.h, s.profile, s.opts);
      else if (s.profile === 'hangar') this.hangarShell(s.room, s.h);
    }
    this.pendingShells = [];
  }

  private sides(r: Room) {
    const sx = r.x1 - r.x0;
    const sz = r.z1 - r.z0;
    const alongX = sx >= sz;
    return [
      { axis: 'z' as const, c: r.z1, dir: -1, a0: r.x0, a1: r.x1, long: alongX },
      { axis: 'z' as const, c: r.z0, dir: 1, a0: r.x0, a1: r.x1, long: alongX },
      { axis: 'x' as const, c: r.x1, dir: -1, a0: r.z0, a1: r.z1, long: !alongX },
      { axis: 'x' as const, c: r.x0, dir: 1, a0: r.z0, a1: r.z1, long: !alongX },
    ];
  }

  /** A box lying on the ceiling chamfer of one side. */
  private slope(side: ReturnType<Kit['sides']>[number], yTop: number, ch: number, mid: number, len: number, lift: number, thick: number, width: number, key: string): void {
    const k = Math.SQRT1_2;
    const nOff = side.dir * (ch / 2 + lift * k);
    const yOff = -ch / 2 - lift * k;
    if (side.axis === 'z') {
      const g = new THREE.BoxGeometry(len, thick, width);
      this.b.geo(g, key, new THREE.Vector3(mid, yTop + yOff, side.c + nOff), new THREE.Euler((-side.dir * Math.PI) / 4, 0, 0));
    } else {
      const g = new THREE.BoxGeometry(width, thick, len);
      this.b.geo(g, key, new THREE.Vector3(side.c + nOff, yTop + yOff, mid), new THREE.Euler(0, 0, (side.dir * Math.PI) / 4));
    }
  }

  private shipShell(r: Room, h: number, profile: Profile, opts: { lightMat?: string; rib?: number }): void {
    const b = this.b;
    const yTop = r.y0 + h;
    const ch = profile === 'hex' ? 0.55 : h >= 3.5 ? 0.42 : 0.3;
    const sides = this.sides(r);
    const stripKey = opts.lightMat && opts.lightMat !== 'light' ? opts.lightMat : 'lightStrip';
    for (const s of sides) {
      const len = s.a1 - s.a0;
      const mid = (s.a0 + s.a1) / 2;
      this.slope(s, yTop, ch, mid, len, 0, 0.05, ch * Math.SQRT2 + 0.02, 'panel');
      if (s.long || profile === 'room') this.slope(s, yTop, ch, mid, Math.max(0.4, len - 0.9), 0.03, 0.03, 0.09, stripKey);
    }
    const longSides = sides.filter((s) => s.long);
    const lowCh = profile === 'hex' ? 0.36 : 0;
    if (lowCh > 0) {
      // hexagonal tube: angled skirts along the floor on both long walls
      for (const s of longSides) {
        const len = s.a1 - s.a0;
        const mid = (s.a0 + s.a1) / 2;
        const k = Math.SQRT1_2;
        const pos = s.axis === 'z' ? new THREE.Vector3(mid, r.y0 + lowCh / 2, s.c + s.dir * (lowCh / 2)) : new THREE.Vector3(s.c + s.dir * (lowCh / 2), r.y0 + lowCh / 2, mid);
        if (s.axis === 'z') b.geo(new THREE.BoxGeometry(len, 0.05, lowCh * Math.SQRT2 + 0.02), 'panel', pos, new THREE.Euler((s.dir * Math.PI) / 4, 0, 0));
        else b.geo(new THREE.BoxGeometry(lowCh * Math.SQRT2 + 0.02, 0.05, len), 'panel', pos, new THREE.Euler(0, 0, (-s.dir * Math.PI) / 4));
        void k;
        const c0 = s.c;
        const c1 = s.c + s.dir * (lowCh + 0.04);
        if (s.axis === 'z') this.world.add(s.a0, r.y0, Math.min(c0, c1), s.a1, r.y0 + 0.5, Math.max(c0, c1));
        else this.world.add(Math.min(c0, c1), r.y0, s.a0, Math.max(c0, c1), r.y0 + 0.5, s.a1);
        // glowing strip where skirt meets floor
        const l0 = s.c + s.dir * (lowCh + 0.01);
        const l1 = s.c + s.dir * (lowCh + 0.05);
        if (s.axis === 'z') b.box(s.a0, r.y0, Math.min(l0, l1), s.a1, r.y0 + 0.02, Math.max(l0, l1), 'ledStrip', false);
        else b.box(Math.min(l0, l1), r.y0, s.a0, Math.max(l0, l1), r.y0 + 0.02, s.a1, 'ledStrip', false);
      }
    }
    const shortLen = longSides[0].axis === 'z' ? r.z1 - r.z0 : r.x1 - r.x0;
    const ls = longSides[0];
    const start = ls.a0;
    const len = ls.a1 - ls.a0;
    const spacing = opts.rib ?? (profile === 'hall' ? 2.64 : 2.4);
    const n = Math.max(1, Math.round(len / spacing));
    const ribs: number[] = [];
    for (let i = 1; i < n; i++) ribs.push(start + (len * i) / n);
    const lo = Math.min(longSides[0].c, longSides[1].c);
    const hi = Math.max(longSides[0].c, longSides[1].c);
    for (const p of ribs) {
      // ceiling beam across the short span
      if (ls.axis === 'z') b.box(p - 0.11, yTop - 0.14, lo + ch - 0.05, p + 0.11, yTop, hi - ch + 0.05, 'rib', false);
      else b.box(lo + ch - 0.05, yTop - 0.14, p - 0.11, hi - ch + 0.05, yTop, p + 0.11, 'rib', false);
      for (const s of longSides) {
        this.slope(s, yTop, ch, p, 0.22, 0.05, 0.1, ch * Math.SQRT2 + 0.06, 'rib');
        if (profile === 'room') continue;
        if (this.blocked(s.axis, s.c, r.y0, p - 0.45, p + 0.45)) continue;
        const f0 = s.c;
        const f1 = s.c + s.dir * (0.24 + lowCh);
        if (s.axis === 'z') b.box(p - 0.13, r.y0, Math.min(f0, f1), p + 0.13, yTop - ch + 0.02, Math.max(f0, f1), 'rib', 'solid', 0.02);
        else b.box(Math.min(f0, f1), r.y0, p - 0.13, Math.max(f0, f1), yTop - ch + 0.02, p + 0.13, 'rib', 'solid', 0.02);
      }
    }
    // centre ceiling light runs for wide rooms, one per bay
    if (profile !== 'corridor' && shortLen >= 4) {
      const bounds = [start, ...ribs, start + len];
      const cMid = (lo + hi) / 2;
      for (let i = 0; i < bounds.length - 1; i++) {
        const a0 = bounds[i] + 0.35;
        const a1 = bounds[i + 1] - 0.35;
        if (a1 - a0 < 0.4) continue;
        for (const off of shortLen >= 7 ? [-1.4, 1.4] : [0]) {
          if (ls.axis === 'z') {
            b.box(a0 - 0.05, yTop - 0.05, cMid + off - 0.13, a1 + 0.05, yTop, cMid + off + 0.13, 'metal', false);
            b.box(a0, yTop - 0.065, cMid + off - 0.08, a1, yTop - 0.04, cMid + off + 0.08, stripKey, false);
          } else {
            b.box(cMid + off - 0.13, yTop - 0.05, a0 - 0.05, cMid + off + 0.13, yTop, a1 + 0.05, 'metal', false);
            b.box(cMid + off - 0.08, yTop - 0.065, a0, cMid + off + 0.08, yTop - 0.04, a1, stripKey, false);
          }
        }
      }
    }
    if (profile === 'corridor' || profile === 'hex') this.corridorFit(r, h, longSides, ribs, ch, lowCh);
  }

  /** Corridor fit-out: grating, floor LEDs, handrails, ceiling pipes and cable tray, wall equipment. */
  private corridorFit(r: Room, h: number, longSides: ReturnType<Kit['sides']>, ribs: number[], ch: number, lowCh = 0): void {
    const b = this.b;
    const yTop = r.y0 + h;
    const ls = longSides[0];
    const lo = Math.min(longSides[0].c, longSides[1].c);
    const hi = Math.max(longSides[0].c, longSides[1].c);
    const cMid = (lo + hi) / 2;
    const A = (a: number, n: number, yy: number) => (ls.axis === 'z' ? new THREE.Vector3(a, yy, n) : new THREE.Vector3(n, yy, a));
    // centre grating strip
    if (ls.axis === 'z') b.box(ls.a0, r.y0, cMid - 0.45, ls.a1, r.y0 + 0.006, cMid + 0.45, 'grating', false);
    else b.box(cMid - 0.45, r.y0, ls.a0, cMid + 0.45, r.y0 + 0.006, ls.a1, 'grating', false);
    // ceiling services: pipes on one side, cable tray on the other
    const sA = longSides[0];
    const sB = longSides[1];
    const pipeN = (s: typeof sA, off: number) => s.c + s.dir * (ch + off);
    for (const [off, rad, key] of [[0.1, 0.055, 'pipeBlue'], [0.24, 0.04, 'steel'], [0.35, 0.03, 'pipeGreen']] as const) {
      b.cyl(A(ls.a0, pipeN(sA, off), yTop - 0.24), A(ls.a1, pipeN(sA, off), yTop - 0.24), rad, key, 10);
    }
    const tn = pipeN(sB, 0.2);
    if (ls.axis === 'z') b.box(ls.a0, yTop - 0.27, tn - 0.16, ls.a1, yTop - 0.21, tn + 0.16, 'ribDark', false);
    else b.box(tn - 0.16, yTop - 0.27, ls.a0, tn + 0.16, yTop - 0.21, ls.a1, 'ribDark', false);
    for (const k of [-0.08, 0, 0.08]) b.cyl(A(ls.a0, tn + k, yTop - 0.18), A(ls.a1, tn + k, yTop - 0.18), 0.025, 'rubber', 6);
    // overhead clutter between ribs: downlights, junction boxes, duct runs
    const bnds = [ls.a0, ...ribs, ls.a1];
    for (let i = 0; i < bnds.length - 1; i++) {
      const m = (bnds[i] + bnds[i + 1]) / 2;
      b.geo(new THREE.CylinderGeometry(0.11, 0.13, 0.05, 16), 'ribDark', A(m, cMid, yTop - 0.025));
      b.geo(new THREE.CylinderGeometry(0.085, 0.085, 0.01, 16), 'lightWarm', A(m, cMid, yTop - 0.05));
      if (i % 2 === 0) {
        const p0 = A(m - 0.5, cMid + 0.35, yTop - 0.16);
        const p1 = A(m + 0.5, cMid + 0.75, yTop);
        b.box(Math.min(p0.x, p1.x), p0.y, Math.min(p0.z, p1.z), Math.max(p0.x, p1.x), p1.y, Math.max(p0.z, p1.z), 'ribDark', false, 0.02);
      } else {
        const p0 = A(m - 0.35, cMid - 0.7, yTop - 0.12);
        const p1 = A(m + 0.35, cMid - 0.3, yTop);
        b.box(Math.min(p0.x, p1.x), p0.y, Math.min(p0.z, p1.z), Math.max(p0.x, p1.x), p1.y, Math.max(p0.z, p1.z), 'paintDark', false, 0.02);
      }
    }
    for (const p of ribs) {
      for (const s of [sA, sB]) {
        const n0 = pipeN(s, 0);
        const n1 = pipeN(s, 0.45);
        if (ls.axis === 'z') b.box(p - 0.04, yTop - 0.3, Math.min(n0, n1), p + 0.04, yTop - 0.14, Math.max(n0, n1), 'metal', false);
        else b.box(Math.min(n0, n1), yTop - 0.3, p - 0.04, Math.max(n0, n1), yTop - 0.14, p + 0.04, 'metal', false);
      }
    }
    // bays between ribs: handrails, floor LEDs, equipment
    const bounds = [ls.a0, ...ribs, ls.a1];
    const kinds = ['o2', 'ext', 'intercom', 'valve', 'panel'] as const;
    let ki = Math.abs(Math.round(r.x0 + r.z0 + r.y0)) % kinds.length;
    let frame = 0;
    const deckTag = r.deck === 'command' ? '1' : r.deck === 'crew' ? '2' : r.deck === 'science' ? '3' : 'S';
    longSides.forEach((s, si) => {
      const face = s.c + s.dir * (0.1 + (lowCh > 0 ? lowCh * 0.6 : 0));
      for (let i = 0; i < bounds.length - 1; i++) {
        const b0 = bounds[i] + (i === 0 ? 0.15 : 0.2);
        const b1 = bounds[i + 1] - (i === bounds.length - 2 ? 0.15 : 0.2);
        if (b1 - b0 < 0.8) continue;
        if (this.blocked(s.axis, s.c, r.y0, b0 - 0.1, b1 + 0.1)) continue;
        // LED strip at the floor
        const l0 = face + s.dir * 0.02;
        const l1 = face + s.dir * 0.05;
        if (s.axis === 'z') b.box(b0, r.y0 + 0.02, Math.min(l0, l1), b1, r.y0 + 0.04, Math.max(l0, l1), 'ledStrip', false);
        else b.box(Math.min(l0, l1), r.y0 + 0.02, b0, Math.max(l0, l1), r.y0 + 0.04, b1, 'ledStrip', false);
        // handrail on standoffs
        const rn = face + s.dir * 0.09;
        b.cyl(A(b0 + 0.1, rn, r.y0 + 1.0), A(b1 - 0.1, rn, r.y0 + 1.0), 0.024, 'steel', 10);
        for (const a of [b0 + 0.2, b1 - 0.2]) b.cyl(A(a, face, r.y0 + 1.0), A(a, rn, r.y0 + 1.0), 0.016, 'steel', 6);
        // equipment in alternating bays, bold frame numbers in the others
        if ((i + si) % 2 === 0) this.equipment(kinds[ki++ % kinds.length], s, (b0 + b1) / 2, face, r.y0);
        else {
          frame++;
          const rect = this.graphicRect(`${deckTag}·${String(i + 1).padStart(2, '0')}`, { w: 256, h: 128, sub: si ? 'PORT' : 'STBD', fg: '#e9e6dc' });
          const gp = A((b0 + b1) / 2, s.c + s.dir * 0.112, r.y0 + 1.72);
          this.b.geo(atlasQuad(0.62, 0.31, rect), 'decal', gp, new THREE.Euler(0, s.axis === 'z' ? (s.dir > 0 ? 0 : Math.PI) : s.dir > 0 ? Math.PI / 2 : -Math.PI / 2, 0));
        }
      }
    });
  }

  /** Wall-mounted ship equipment facing into the room from a wall face. */
  private equipment(kind: 'o2' | 'ext' | 'intercom' | 'valve' | 'panel', s: ReturnType<Kit['sides']>[number], a: number, face: number, y: number): void {
    const b = this.b;
    const P = (along: number, out: number, up: number) => (s.axis === 'z' ? new THREE.Vector3(a + along, y + up, face + s.dir * out) : new THREE.Vector3(face + s.dir * out, y + up, a + along));
    const B = (a0: number, a1: number, o0: number, o1: number, v0: number, v1: number, key: string) => {
      const p0 = P(a0, o0, v0);
      const p1 = P(a1, o1, v1);
      b.box(Math.min(p0.x, p1.x), p0.y, Math.min(p0.z, p1.z), Math.max(p0.x, p1.x), p1.y, Math.max(p0.z, p1.z), key, false);
    };
    const yaw = s.axis === 'z' ? (s.dir > 0 ? 0 : Math.PI) : s.dir > 0 ? Math.PI / 2 : -Math.PI / 2;
    const itemAt = (prompt: string, text: string, v0: number, v1: number, w: number) => {
      const p0 = P(-w / 2, 0, v0);
      const p1 = P(w / 2, 0.25, v1);
      this.item({ id: this.uid('equip'), min: [Math.min(p0.x, p1.x), p0.y, Math.min(p0.z, p1.z)], max: [Math.max(p0.x, p1.x), p1.y, Math.max(p0.z, p1.z)], prompt, action: 'flavor', data: text });
    };
    void yaw;
    switch (kind) {
      case 'o2':
        B(-0.28, 0.28, 0, 0.13, 1.25, 1.9, 'warning');
        B(-0.24, 0.24, 0.13, 0.135, 1.42, 1.8, 'blackGlass');
        B(-0.28, 0.28, 0.13, 0.135, 1.27, 1.36, 'hazard');
        B(0.17, 0.23, 0.135, 0.14, 1.83, 1.87, 'statusGreen');
        itemAt('Emergency oxygen', 'Emergency oxygen station. Four masks, sealed. Fifteen minutes each.', 1.25, 1.9, 0.56);
        break;
      case 'ext':
        B(-0.14, 0.14, 0, 0.04, 0.5, 1.2, 'emergency');
        b.cyl(P(0, 0.12, 0.55), P(0, 0.12, 1.05), 0.075, 'emergency', 14);
        b.cyl(P(0, 0.12, 1.05), P(0, 0.12, 1.14), 0.03, 'metal', 8);
        B(-0.1, 0.1, 0.04, 0.2, 0.75, 0.79, 'metal');
        itemAt('Fire suppressant', 'Fire suppressant. Foam, not water. Water and electronics do not get along.', 0.5, 1.2, 0.28);
        break;
      case 'intercom':
        B(-0.15, 0.15, 0, 0.05, 1.32, 1.74, 'paintDark');
        B(-0.1, 0.1, 0.05, 0.055, 1.52, 1.66, 'ledStrip');
        for (let k = 0; k < 4; k++) B(-0.1, 0.1, 0.05, 0.056, 1.36 + k * 0.03, 1.375 + k * 0.03, 'metal');
        itemAt('Intercom', 'Intercom. VESTA is listening. She is always listening.', 1.32, 1.74, 0.3);
        break;
      case 'valve':
        b.cyl(P(0, 0.12, 0), P(0, 0.12, 2.55), 0.07, 'pipeGreen', 12);
        b.geo(new THREE.TorusGeometry(0.15, 0.022, 8, 20), 'emergency', P(0, 0.26, 1.25), new THREE.Euler(0, yawFor(s), 0));
        b.cyl(P(0, 0.12, 1.25), P(0, 0.26, 1.25), 0.025, 'metal', 8);
        B(-0.1, 0.1, 0, 0.12, 2.0, 2.14, 'metal');
        B(-0.1, 0.1, 0, 0.12, 0.3, 0.44, 'metal');
        itemAt('Coolant valve', 'Coolant line, loop B. The label says DO NOT CLOSE. Someone has added: "seriously".', 0.9, 1.6, 0.4);
        break;
      case 'panel':
        B(-0.32, 0.32, 0, 0.12, 0.85, 1.75, 'wallDark');
        B(-0.3, 0.3, 0.12, 0.125, 1.55, 1.7, 'hazard');
        B(0.18, 0.26, 0.125, 0.13, 1.05, 1.1, 'statusAmber');
        B(-0.05, 0.05, 0.12, 0.17, 1.2, 1.32, 'metal');
        itemAt('Power distribution', 'Power distribution, section ' + Math.abs(Math.round(a)) + '. Hums slightly louder than its neighbours.', 0.85, 1.75, 0.64);
        break;
    }
  }

  private hangarShell(r: Room, h: number): void {
    const b = this.b;
    const yTop = r.y0 + h;
    for (const s of this.sides(r)) {
      const len = s.a1 - s.a0;
      const n = Math.max(1, Math.round(len / 6));
      for (let i = 1; i < n; i++) {
        const p = s.a0 + (len * i) / n;
        if (this.blocked(s.axis, s.c, r.y0, p - 0.6, p + 0.6)) continue;
        const f0 = s.c;
        const f1 = s.c + s.dir * 0.55;
        if (s.axis === 'z') b.box(p - 0.32, r.y0, Math.min(f0, f1), p + 0.32, yTop, Math.max(f0, f1), 'ribDark', 'solid', 0.03);
        else b.box(Math.min(f0, f1), r.y0, p - 0.32, Math.max(f0, f1), yTop, p + 0.32, 'ribDark', 'solid', 0.03);
        // knee brace up into the ceiling truss
        const k0 = s.c + s.dir * 0.55;
        const k1 = s.c + s.dir * 2.2;
        if (s.axis === 'z') b.box(p - 0.2, yTop - 1.6, Math.min(k0, k1), p + 0.2, yTop - 1.2, Math.max(k0, k1), 'ribDark', false);
        else b.box(Math.min(k0, k1), yTop - 1.6, p - 0.2, Math.max(k0, k1), yTop - 1.2, p + 0.2, 'ribDark', false);
        if (s.axis === 'z' && s.dir < 0) b.box(p - 0.3, yTop - 1.0, r.z0, p + 0.3, yTop, r.z1, 'ribDark', false);
        // amber marker light on each pillar
        const l0 = s.c + s.dir * 0.55;
        const l1 = s.c + s.dir * 0.57;
        if (s.axis === 'z') b.box(p - 0.08, r.y0 + 3.2, Math.min(l0, l1), p + 0.08, r.y0 + 3.4, Math.max(l0, l1), 'statusAmber', false);
        else b.box(Math.min(l0, l1), r.y0 + 3.2, p - 0.08, Math.max(l0, l1), r.y0 + 3.4, p + 0.08, 'statusAmber', false);
      }
    }
  }

  private anchors(r: Room, h: number, opts: { lightColor?: number; intensity?: number }): void {
    const sx = r.x1 - r.x0;
    const sz = r.z1 - r.z0;
    const yTop = r.y0 + h;
    const color = new THREE.Color(opts.lightColor ?? 0xfff1e0);
    const intensity = opts.intensity ?? 7;
    const ax = Math.max(1, Math.round(sx / 4.5));
    const az = Math.max(1, Math.round(sz / 4.5));
    for (let i = 0; i < ax; i++) {
      for (let k = 0; k < az; k++) {
        this.lights.add({
          x: r.x0 + (sx * (i + 0.5)) / ax,
          y: yTop - 0.45,
          z: r.z0 + (sz * (k + 0.5)) / az,
          color,
          intensity: intensity * Math.min(2.2, Math.max(1, (sx * sz) / (ax * az * 14))),
          distance: Math.max(7, Math.min(16, Math.hypot(sx / ax, sz / az) * 1.6 + h)),
        });
      }
    }
  }

  private fixtures(r: Room, h: number, opts: { lightMat?: string; spacing?: number; cones?: boolean }): void {
    const sx = r.x1 - r.x0;
    const sz = r.z1 - r.z0;
    const spacing = opts.spacing ?? 3.2;
    const nx = Math.max(1, Math.round(sx / spacing));
    const nz = Math.max(1, Math.round(sz / spacing));
    const mat = opts.lightMat ?? 'light';
    const yTop = r.y0 + h;
    for (let i = 0; i < nx; i++) {
      for (let k = 0; k < nz; k++) {
        const x = r.x0 + (sx * (i + 0.5)) / nx;
        const z = r.z0 + (sz * (k + 0.5)) / nz;
        this.b.box(x - 0.75, yTop - 0.3, z - 0.3, x + 0.75, yTop, z + 0.3, 'ribDark', false);
        this.b.box(x - 0.65, yTop - 0.32, z - 0.22, x + 0.65, yTop - 0.3, z + 0.22, mat, false);
        if (opts.cones) this.cones.push({ x, y: yTop - 0.33, z, h: h - 0.4 });
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
  seat(p: Place, lx: number, ly: number, lz: number, label: string, kind: 'sit' | 'lie' = 'sit', sleep = false, exit = 0.75, exitDir?: [number, number]): Seat {
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
    if (kind === 'lie' || exitDir) {
      // exit to the side of the bed, or along an explicit local direction
      const [sx, sz] = rotXZ(exitDir ? exitDir[0] : 1, exitDir ? exitDir[1] : 0, p.rot);
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
