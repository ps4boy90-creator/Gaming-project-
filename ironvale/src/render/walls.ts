import * as THREE from 'three';
import {
  WALLS, WALL_BRICK, WALL_CONCRETE, WALL_FENCE, WALL_PERIMETER, WALL_WINDOW,
  DOOR_CELL, DOOR_GATE, DOOR_STAFF, DOOR_STANDARD,
} from '../data/defs';
import type { World } from '../world/world';
import type { Gfx } from './gfx';
import { Batch } from './batch';
import { MB } from './modelkit';
import { makeFenceTexture } from './textures';

const C = (hex: number) => new THREE.Color().setHex(hex, THREE.SRGBColorSpace);

const COL = {
  concrete: C(0xcfd0cb),
  concreteCap: C(0x8b9299),
  brick: C(0xb9694b),
  brickCap: C(0xd9d3c4),
  perimeter: C(0xb4b6b1),
  perimeterCap: C(0x6c737b),
  steel: C(0x9aa3ad),
  darkSteel: C(0x3d444d),
  wire: C(0xc8d0d8),
  plan: C(0x58b7ff),
};

/** Standard material with a world-space brick / concrete pattern selected per instance. */
function makeWallMaterial(): THREE.MeshStandardMaterial {
  const mat = new THREE.MeshStandardMaterial({ roughness: 0.88, metalness: 0 });
  mat.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nattribute float aStyle;\nvarying float vStyle;\nvarying vec3 vWPos;\nvarying vec3 vONormal;')
      .replace(
        '#include <begin_vertex>',
        `#include <begin_vertex>
        vec4 wp4 = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
          wp4 = instanceMatrix * wp4;
        #endif
        wp4 = modelMatrix * wp4;
        vWPos = wp4.xyz;
        vStyle = aStyle;
        vONormal = normal;`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        `#include <common>
        varying float vStyle;
        varying vec3 vWPos;
        varying vec3 vONormal;
        float wHash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }`,
      )
      .replace(
        '#include <color_fragment>',
        `#include <color_fragment>
        {
          float top = step(0.5, abs(vONormal.y));
          float u = abs(vONormal.x) > 0.5 ? vWPos.z : vWPos.x;
          float y = vWPos.y;
          float px = max(fwidth(u), fwidth(y));
          float detail = clamp(1.0 - px * 7.0, 0.0, 1.0);
          float shade = 1.0;
          if (vStyle > 0.5 && vStyle < 1.5) {
            float rh = 0.108;
            float row = floor(y / rh);
            float uu = u / 0.3 + mod(row, 2.0) * 0.5;
            vec2 f = vec2(fract(uu), fract(y / rh));
            float aa = px * 4.0;
            float mortar = 1.0 - smoothstep(0.03, 0.03 + aa, f.x) * smoothstep(0.1, 0.1 + aa * 2.8, f.y);
            float h = wHash(vec2(floor(uu), row));
            float brick = 0.84 + 0.3 * h;
            shade = mix(1.0, mix(brick, 1.38, mortar), detail);
            shade = mix(shade, 1.0, top);
          } else {
            float pw = vStyle > 1.5 ? 3.0 : 2.0;
            float jv = abs(fract(u / pw) - 0.5) * pw;
            float joint = 1.0 - smoothstep(0.012, 0.012 + px * 1.5, jv);
            float jh = abs(fract(y / 0.65 + 0.5) - 0.5) * 0.65;
            float line = 1.0 - smoothstep(0.008, 0.008 + px * 1.5, jh);
            float blot = wHash(floor(vec2(u * 1.5, y * 3.0))) * 0.05;
            shade = 1.0 - (joint * 0.2 + line * 0.1 + blot) * detail * (1.0 - top);
          }
          shade *= mix(0.84, 1.0, smoothstep(0.0, 0.3, y));
          diffuseColor.rgb *= shade;
        }`,
      );
  };
  return mat;
}

function helixGeometry(len: number, radius: number, turns: number, tube: number): THREE.BufferGeometry {
  const pts: THREE.Vector3[] = [];
  const n = turns * 10;
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const a = t * turns * Math.PI * 2;
    pts.push(new THREE.Vector3(t * len - len / 2, Math.cos(a) * radius, Math.sin(a) * radius));
  }
  const curve = new THREE.CatmullRomCurve3(pts);
  return new THREE.TubeGeometry(curve, n, tube, 3, false);
}

interface DoorInst {
  idx: number;
  type: number;
  x: number;
  z: number;
  yaw: number;
  open: number;
  slot: number;
}

const DOOR_OPEN_W = 0.78;

function doorFrame(type: number) {
  const b = new MB();
  if (type === DOOR_GATE) {
    b.box(0.14, 1.7, 0.2, -0.43, 0, 0, 0x4a525c).box(0.14, 1.7, 0.2, 0.43, 0, 0, 0x4a525c);
    b.box(1.0, 0.1, 0.16, 0, 1.6, 0, 0x4a525c);
    b.box(0.1, 0.1, 0.24, -0.43, 1.7, 0, 0xe2b93b).box(0.1, 0.1, 0.24, 0.43, 1.7, 0, 0xe2b93b);
  } else {
    const col = type === DOOR_CELL ? 0x565d66 : type === DOOR_STAFF ? 0x3a5a8c : 0xa7adb3;
    b.box(0.11, 1.3, 0.32, -0.445, 0, 0, col).box(0.11, 1.3, 0.32, 0.445, 0, 0, col);
    b.box(1.0, 0.2, 0.32, 0, 1.1, 0, col);
    b.box(0.78, 0.02, 0.3, 0, 0, 0, 0x5a6068); // threshold
    if (type === DOOR_STAFF) b.box(0.8, 0.05, 0.34, 0, 1.12, 0, 0xe2b93b);
    if (type === DOOR_CELL) b.box(0.3, 0.09, 0.34, 0, 1.15, 0, 0xc9703a);
  }
  return b.build();
}

/** Leaf geometry. Swing doors are modelled with the hinge at x = 0; sliding doors are centred. */
function doorLeaf(type: number) {
  const b = new MB();
  if (type === DOOR_STANDARD) {
    b.rbox(0.76, 1.08, 0.07, 0.38, 0.02, 0, 0x8e6b4a, 0.015);
    b.box(0.6, 0.38, 0.085, 0.38, 0.14, 0, 0x7d5d40).box(0.6, 0.38, 0.085, 0.38, 0.6, 0, 0x7d5d40);
    b.box(0.05, 0.05, 0.14, 0.66, 0.52, 0, 0xd9c27a);
  } else if (type === DOOR_STAFF) {
    b.rbox(0.76, 1.08, 0.08, 0.38, 0.02, 0, 0x3f6aa8, 0.015);
    b.box(0.3, 0.26, 0.095, 0.38, 0.68, 0, 0xa9d4ea);
    b.box(0.76, 0.07, 0.095, 0.38, 0.3, 0, 0xe2b93b);
    b.box(0.05, 0.1, 0.15, 0.66, 0.5, 0, 0xcfd6dc);
  } else if (type === DOOR_CELL) {
    const col = 0x4b525b;
    b.box(0.78, 0.07, 0.07, 0, 0.03, 0, col).box(0.78, 0.07, 0.07, 0, 1.0, 0, col).box(0.78, 0.05, 0.06, 0, 0.52, 0, col);
    for (let i = 0; i < 7; i++) b.cyl(0.02, 0.02, 1.0, -0.36 + i * 0.12, 0.05, 0, 0x6a727c, 6);
    b.box(0.13, 0.17, 0.11, 0.3, 0.46, 0, 0x2f343a);
  } else {
    const col = 0x59626c;
    b.box(0.8, 0.08, 0.07, 0, 0.04, 0, col).box(0.8, 0.08, 0.07, 0, 1.46, 0, col).box(0.8, 0.05, 0.06, 0, 0.75, 0, col);
    for (let i = 0; i < 7; i++) b.cyl(0.022, 0.022, 1.46, -0.36 + i * 0.12, 0.06, 0, 0x7b858f, 6);
    b.box(0.5, 0.2, 0.09, 0, 0.95, 0, 0xe2b93b);
    b.box(0.5, 0.05, 0.095, 0, 1.02, 0, 0x2b2f35);
  }
  return b.build();
}

export class WallRenderer {
  private group = new THREE.Group();
  private body: Batch;
  private cap: Batch;
  private metal: Batch;
  private panel: Batch;
  private glass: Batch;
  private coilS: Batch;
  private coilL: Batch;
  private planBox: Batch;
  private frames = new Map<number, Batch>();
  private leaves = new Map<number, Batch>();
  private doors: DoorInst[] = [];
  /** per-tile flag set each frame by the game loop where somebody is at / approaching a door */
  doorHot: Uint8Array;
  private m4 = new THREE.Matrix4();
  private q = new THREE.Quaternion();
  private p = new THREE.Vector3();
  private s = new THREE.Vector3(1, 1, 1);
  private up = new THREE.Vector3(0, 1, 0);

  constructor(private gfx: Gfx, private world: World) {
    gfx.scene.add(this.group);
    this.doorHot = new Uint8Array(world.n);
    const box = new THREE.BoxGeometry(1, 1, 1);
    box.translate(0, 0.5, 0); // origin at the bottom centre
    this.body = new Batch(box, makeWallMaterial(), this.group, { cast: true, receive: true, cap: 512, extra: 'aStyle' });
    this.cap = new Batch(box, new THREE.MeshStandardMaterial({ roughness: 0.8 }), this.group, { cast: true, receive: true, cap: 512 });
    this.metal = new Batch(box, new THREE.MeshStandardMaterial({ roughness: 0.45, metalness: 0.55 }), this.group, { cast: true, receive: true, cap: 512 });
    const plane = new THREE.PlaneGeometry(1, 1);
    plane.translate(0, 0.5, 0);
    this.panel = new Batch(
      plane,
      new THREE.MeshStandardMaterial({
        map: makeFenceTexture(), transparent: true, side: THREE.DoubleSide, depthWrite: false, roughness: 0.5, metalness: 0.4, opacity: 0.95,
      }),
      this.group,
      { cast: false, receive: false, noAO: true, cap: 256, colors: false },
    );
    this.panel.mesh.renderOrder = 2;
    this.glass = new Batch(
      box,
      new THREE.MeshStandardMaterial({ color: 0x9fd0ea, transparent: true, opacity: 0.42, roughness: 0.1, metalness: 0.2, depthWrite: false }),
      this.group,
      { noAO: true, cap: 64, colors: false },
    );
    const wireMat = new THREE.MeshStandardMaterial({ color: 0xc9d1d9, roughness: 0.35, metalness: 0.7 });
    this.coilS = new Batch(helixGeometry(0.5, 0.055, 4, 0.007), wireMat, this.group, { cast: false, noAO: true, cap: 256, colors: false });
    this.coilL = new Batch(helixGeometry(0.5, 0.1, 3, 0.011), wireMat, this.group, { cast: true, noAO: true, cap: 256, colors: false });
    this.planBox = new Batch(
      box,
      new THREE.MeshBasicMaterial({ color: 0x58b7ff, transparent: true, opacity: 0.38, depthWrite: false }),
      this.group,
      { noAO: true, cap: 256, colors: false, renderOrder: 5 },
    );
    const doorMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.6, metalness: 0.15 });
    for (const t of [DOOR_STANDARD, DOOR_CELL, DOOR_STAFF, DOOR_GATE]) {
      this.frames.set(t, new Batch(doorFrame(t).solid, doorMat, this.group, { cast: true, receive: true, cap: 32, colors: false }));
      this.leaves.set(t, new Batch(doorLeaf(t).solid, doorMat, this.group, { cast: true, receive: true, cap: 32, colors: false }));
    }
  }

  private solidAt(x: number, y: number, plans: boolean): boolean {
    const w = this.world;
    if (!w.inb(x, y)) return false;
    const i = w.idx(x, y);
    if (w.wall[i] || w.door[i]) return true;
    return plans && (w.planWall[i] !== 0 || w.planDoor[i] !== 0);
  }

  /** emit boxes for one wall tile into a batch. Returns nothing; shared by real walls and blueprints. */
  private emitWall(x: number, y: number, type: number, plan: boolean) {
    const def = WALLS[type];
    const cx = x + 0.5, cz = y + 0.5;
    const E = this.solidAt(x + 1, y, plan), W = this.solidAt(x - 1, y, plan);
    const S = this.solidAt(x, y + 1, plan), N = this.solidAt(x, y - 1, plan);
    const th = def.thick, h = def.height;

    if (plan) {
      const t = Math.max(th, 0.2);
      if ((E || W) && !(N || S)) this.planBox.add(cx, 0, cz, 1, h, t);
      else if ((N || S) && !(E || W)) this.planBox.add(cx, 0, cz, t, h, 1);
      else {
        this.planBox.add(cx, 0, cz, t, h, t);
        if (E) this.planBox.add(cx + 0.25 + t / 4, 0, cz, 0.5 - t / 2, h, t);
        if (W) this.planBox.add(cx - 0.25 - t / 4, 0, cz, 0.5 - t / 2, h, t);
        if (S) this.planBox.add(cx, 0, cz + 0.25 + t / 4, t, h, 0.5 - t / 2);
        if (N) this.planBox.add(cx, 0, cz - 0.25 - t / 4, t, h, 0.5 - t / 2);
      }
      return;
    }

    if (type === WALL_FENCE) {
      const ph = h;
      this.metal.add(cx, 0, cz, 0.07, ph + 0.05, 0.07, 0, COL.steel);
      const arm = (dx: number, dz: number) => {
        const yaw = dx !== 0 ? 0 : Math.PI / 2;
        const ax = cx + dx * 0.25, az = cz + dz * 0.25;
        this.panel.add(ax, 0.04, az, 0.5, ph - 0.06, 1, yaw);
        this.metal.add(ax, ph - 0.03, az, dx !== 0 ? 0.5 : 0.035, 0.035, dx !== 0 ? 0.035 : 0.5, 0, COL.steel);
        this.metal.add(ax, 0.03, az, dx !== 0 ? 0.5 : 0.03, 0.03, dx !== 0 ? 0.03 : 0.5, 0, COL.steel);
        this.coilS.add(ax, ph + 0.07, az, 1, 1, 1, yaw);
      };
      if (E) arm(1, 0);
      if (W) arm(-1, 0);
      if (S) arm(0, 1);
      if (N) arm(0, -1);
      if (!E && !W && !S && !N) this.coilS.add(cx, ph + 0.07, cz, 0.4, 1, 1, 0);
      return;
    }

    if (type === WALL_WINDOW) {
      const alongX = E || W || !(N || S);
      const yaw = alongX ? 0 : Math.PI / 2;
      const sillH = 0.48, headY = 1.02;
      this.body.add(cx, 0, cz, 1, sillH, th, yaw, COL.concrete, 0);
      this.body.add(cx, headY, cz, 1, h - headY, th, yaw, COL.concrete, 0);
      const jx = alongX ? 0.44 : 0, jz = alongX ? 0 : 0.44;
      this.body.add(cx - jx, sillH, cz - jz, 0.12, headY - sillH, th, yaw, COL.concrete, 0);
      this.body.add(cx + jx, sillH, cz + jz, 0.12, headY - sillH, th, yaw, COL.concrete, 0);
      this.cap.add(cx, sillH, cz, 0.8, 0.035, th + 0.08, yaw, COL.concreteCap);
      this.cap.add(cx, h, cz, 1, 0.06, th + 0.06, yaw, COL.concreteCap);
      this.glass.add(cx, sillH + 0.03, cz, 0.76, headY - sillH - 0.03, 0.03, yaw);
      for (let i = -2; i <= 2; i++) {
        const o = i * 0.14;
        this.metal.add(cx + (alongX ? o : 0), sillH, cz + (alongX ? 0 : o), 0.028, headY - sillH, 0.028, 0, COL.darkSteel);
      }
      return;
    }

    const style = type === WALL_BRICK ? 1 : type === WALL_PERIMETER ? 2 : 0;
    const col = type === WALL_BRICK ? COL.brick : type === WALL_PERIMETER ? COL.perimeter : COL.concrete;
    const capCol = type === WALL_BRICK ? COL.brickCap : type === WALL_PERIMETER ? COL.perimeterCap : COL.concreteCap;
    const ct = th + 0.07, chh = type === WALL_PERIMETER ? 0.1 : 0.065;
    const piece = (px: number, pz: number, sx: number, sz: number) => {
      this.body.add(px, 0, pz, sx, h, sz, 0, col, style);
      this.cap.add(px, h, pz, sx + (sx > sz ? 0 : 0.07), chh, sz + (sz > sx ? 0 : 0.07), 0, capCol);
    };
    if ((E || W) && !(N || S)) {
      // straight run along X; trim the free end slightly so wall ends look finished
      const x0 = W ? x : x + 0.5 - th / 2, x1 = E ? x + 1 : x + 0.5 + th / 2;
      piece((x0 + x1) / 2, cz, x1 - x0, th);
    } else if ((N || S) && !(E || W)) {
      const z0 = N ? y : y + 0.5 - th / 2, z1 = S ? y + 1 : y + 0.5 + th / 2;
      piece(cx, (z0 + z1) / 2, th, z1 - z0);
    } else {
      this.body.add(cx, 0, cz, th, h, th, 0, col, style);
      this.cap.add(cx, h, cz, ct, chh, ct, 0, capCol);
      const a = 0.5 - th / 2;
      if (E) piece(cx + th / 2 + a / 2, cz, a, th);
      if (W) piece(cx - th / 2 - a / 2, cz, a, th);
      if (S) piece(cx, cz + th / 2 + a / 2, th, a);
      if (N) piece(cx, cz - th / 2 - a / 2, th, a);
    }
    if (type === WALL_PERIMETER) {
      const top = h + chh + 0.1;
      if (E) this.coilL.add(cx + 0.25, top, cz, 1, 1, 1, 0);
      if (W) this.coilL.add(cx - 0.25, top, cz, 1, 1, 1, 0);
      if (S) this.coilL.add(cx, top, cz + 0.25, 1, 1, 1, Math.PI / 2);
      if (N) this.coilL.add(cx, top, cz - 0.25, 1, 1, 1, Math.PI / 2);
    }
  }

  rebuild() {
    const w = this.world;
    const all = [this.body, this.cap, this.metal, this.panel, this.glass, this.coilS, this.coilL, this.planBox];
    for (const b of all) b.begin();
    for (const b of this.frames.values()) b.begin();
    for (const b of this.leaves.values()) b.begin();
    const oldOpen = new Map<number, number>();
    for (const d of this.doors) oldOpen.set(d.idx, d.open);
    this.doors.length = 0;

    for (let i = 0; i < w.n; i++) {
      const x = i % w.w, y = (i / w.w) | 0;
      const t = w.wall[i];
      if (t) this.emitWall(x, y, t, false);
      else if (w.door[i]) {
        const type = w.door[i];
        const E = this.solidAt(x + 1, y, false), W = this.solidAt(x - 1, y, false);
        const S = this.solidAt(x, y + 1, false), N = this.solidAt(x, y - 1, false);
        const alongX = E || W || !(N || S);
        const yaw = alongX ? 0 : Math.PI / 2;
        this.frames.get(type)!.add(x + 0.5, 0, y + 0.5, 1, 1, 1, yaw);
        const slot = this.leaves.get(type)!.add(x + 0.5, 0, y + 0.5, 1, 1, 1, yaw);
        this.doors.push({ idx: i, type, x: x + 0.5, z: y + 0.5, yaw, open: oldOpen.get(i) ?? 0, slot });
      }
      if (w.planWall[i]) this.emitWall(x, y, w.planWall[i], true);
      else if (w.planDoor[i]) this.planBox.add(x + 0.5, 0, y + 0.5, 0.9, 1.2, 0.9);
    }
    for (const b of all) b.end();
    for (const b of this.frames.values()) b.end();
    for (const b of this.leaves.values()) b.end();
    for (const d of this.doors) this.placeLeaf(d);
  }

  private placeLeaf(d: DoorInst) {
    const batch = this.leaves.get(d.type)!;
    const c = Math.cos(d.yaw), s = Math.sin(d.yaw);
    if (d.type === DOOR_STANDARD || d.type === DOOR_STAFF) {
      // hinge at local x = -0.38
      const hx = d.x - 0.38 * c, hz = d.z + 0.38 * s;
      this.q.setFromAxisAngle(this.up, d.yaw - d.open * 1.45);
      this.p.set(hx, 0, hz);
    } else {
      const off = d.open * DOOR_OPEN_W;
      this.q.setFromAxisAngle(this.up, d.yaw);
      this.p.set(d.x + off * c, 0, d.z - off * s);
    }
    this.m4.compose(this.p, this.q, this.s);
    batch.setMatrix(d.slot, this.m4);
  }

  update(dt: number) {
    const w = this.world;
    if (w.dirtyWalls || w.dirtyPlans) {
      w.dirtyWalls = false;
      w.dirtyPlans = false;
      this.rebuild();
    }
    const k = 1 - Math.exp(-dt * 9);
    for (const d of this.doors) {
      const target = this.doorHot[d.idx] ? 1 : 0;
      if (Math.abs(target - d.open) > 0.003) {
        d.open += (target - d.open) * k;
        this.placeLeaf(d);
      }
    }
    this.doorHot.fill(0);
  }
}

export { WALL_CONCRETE };
