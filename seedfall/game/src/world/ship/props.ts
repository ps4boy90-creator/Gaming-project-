import * as THREE from 'three';
import { Kit } from './kit';
import { Place, rotXZ } from './builder';
import { ScreenKind } from './atlas';

/* Furniture and equipment. Every prop is built in local coordinates where the "front"
 * faces local +z; a Place rotates it in quarter turns. */

const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

/** Local point → world. */
export function L(p: Place, x: number, y: number, z: number): THREE.Vector3 {
  const [wx, wz] = rotXZ(x, z, p.rot);
  return V(p.x + wx, p.y + y, p.z + wz);
}

/** Mesh yaw that makes a +z-facing quad face local direction (dx, dz). */
export function faceYaw(p: Place, dx = 0, dz = 1): number {
  const [fx, fz] = rotXZ(dx, dz, p.rot);
  return Math.atan2(fx, fz);
}

function col(k: Kit, p: Place, x0: number, y0: number, z0: number, x1: number, y1: number, z1: number): void {
  const [ax, az] = rotXZ(x0, z0, p.rot);
  const [bx, bz] = rotXZ(x1, z1, p.rot);
  k.world.add(p.x + Math.min(ax, bx), p.y + y0, p.z + Math.min(az, bz), p.x + Math.max(ax, bx), p.y + y1, p.z + Math.max(az, bz));
}

export function chair(k: Kit, p: Place, label = 'Chair', fabricKey = 'fabric'): void {
  const b = k.b;
  b.pbox(p, -0.24, 0.42, -0.24, 0.24, 0.5, 0.24, fabricKey, false, 0.04);
  b.pbox(p, -0.24, 0.5, -0.3, 0.24, 1.02, -0.22, fabricKey, false, 0.04);
  b.pbox(p, -0.035, 0.05, -0.035, 0.035, 0.42, 0.035, 'steel', false);
  b.pbox(p, -0.26, 0, -0.26, 0.26, 0.05, 0.26, 'metal', false, 0.02);
  col(k, p, -0.22, 0, -0.26, 0.22, 0.5, 0.22);
  k.seat(p, 0, 0.5, 0, label);
}

export function stool(k: Kit, p: Place, label = 'Stool'): void {
  const b = k.b;
  b.pbox(p, -0.19, 0.62, -0.19, 0.19, 0.68, 0.19, 'fabric', false, 0.03);
  b.pbox(p, -0.03, 0.05, -0.03, 0.03, 0.62, 0.03, 'steel', false);
  b.pbox(p, -0.2, 0, -0.2, 0.2, 0.05, 0.2, 'metal', false, 0.02);
  k.seat(p, 0, 0.68, 0, label);
}

export function bench(k: Kit, p: Place, len: number, label = 'Bench', back = false, fabricKey = 'fabric'): void {
  const b = k.b;
  b.pbox(p, -len / 2, 0.38, -0.22, len / 2, 0.47, 0.22, fabricKey, false, 0.04);
  b.pbox(p, -len / 2 + 0.05, 0, -0.18, len / 2 - 0.05, 0.38, 0.14, 'metal', false);
  if (back) b.pbox(p, -len / 2, 0.47, -0.26, len / 2, 0.95, -0.16, fabricKey, false, 0.04);
  col(k, p, -len / 2, 0, -0.22, len / 2, 0.47, 0.22);
  const n = Math.max(1, Math.floor(len / 0.7));
  for (let i = 0; i < n; i++) k.seat(p, -len / 2 + (len * (i + 0.5)) / n, 0.47, 0.02, label);
}

export function couch(k: Kit, p: Place, len: number, label = 'Couch', fabricKey = 'fabric'): void {
  const b = k.b;
  b.pbox(p, -len / 2, 0.06, -0.45, len / 2, 0.36, 0.45, 'paintDark', false, 0.03);
  b.pbox(p, -len / 2 + 0.12, 0.36, -0.28, len / 2 - 0.12, 0.5, 0.45, fabricKey, false, 0.07);
  b.pbox(p, -len / 2, 0.36, -0.45, len / 2, 0.92, -0.25, fabricKey, false, 0.08);
  b.pbox(p, -len / 2, 0.36, -0.45, -len / 2 + 0.14, 0.66, 0.45, fabricKey, false, 0.06);
  b.pbox(p, len / 2 - 0.14, 0.36, -0.45, len / 2, 0.66, 0.45, fabricKey, false, 0.06);
  col(k, p, -len / 2, 0, -0.45, len / 2, 0.5, 0.45);
  const n = Math.max(1, Math.round(len / 0.8));
  for (let i = 0; i < n; i++) k.seat(p, -len / 2 + 0.12 + ((len - 0.24) * (i + 0.5)) / n, 0.5, 0.05, label);
}

export function bed(k: Kit, p: Place, label: string, sleep = false, blanket = 'fabricAmber'): void {
  const b = k.b;
  b.pbox(p, -0.52, 0, -1.08, 0.52, 0.3, 1.08, 'paintGrey', false, 0.03);
  b.pbox(p, -0.48, 0.3, -1.04, 0.48, 0.48, 1.04, 'fabricLight', false, 0.08);
  b.pbox(p, -0.5, 0.42, -0.25, 0.5, 0.53, 1.06, blanket, false, 0.05);
  b.pbox(p, -0.36, 0.48, -0.98, 0.36, 0.6, -0.62, 'fabricLight', false, 0.06);
  b.pbox(p, -0.54, 0, -1.12, 0.54, 1.0, -1.06, 'paintGrey', false, 0.02);
  col(k, p, -0.52, 0, -1.12, 0.52, 0.55, 1.08);
  k.seat(p, 0, 0.55, -0.62, label, 'lie', sleep, 0.9);
}

export function desk(k: Kit, p: Place, kind: ScreenKind | null, seed = 1, w = 1.4): void {
  const b = k.b;
  b.pbox(p, -w / 2, 0.72, -0.36, w / 2, 0.76, 0.36, 'paint', false, 0.015);
  b.pbox(p, -w / 2 + 0.05, 0, -0.3, -w / 2 + 0.1, 0.72, 0.3, 'metal', false);
  b.pbox(p, w / 2 - 0.1, 0, -0.3, w / 2 - 0.05, 0.72, 0.3, 'metal', false);
  b.pbox(p, w / 2 - 0.5, 0.35, -0.32, w / 2 - 0.1, 0.72, 0.3, 'paintGrey', false, 0.01);
  col(k, p, -w / 2, 0, -0.36, w / 2, 0.76, 0.36);
  if (kind) {
    b.pbox(p, -0.04, 0.76, -0.26, 0.04, 0.98, -0.2, 'metal', false);
    k.screen(kind, L(p, 0, 1.12, -0.2), faceYaw(p), 0.62, seed, '', 0.12);
  }
}

export function table(k: Kit, p: Place, w: number, d: number, h = 0.74, top = 'paint'): void {
  const b = k.b;
  b.pbox(p, -w / 2, h - 0.04, -d / 2, w / 2, h, d / 2, top, false, 0.02);
  const lx = w / 2 - 0.2;
  b.pbox(p, -lx - 0.05, 0, -0.05, -lx + 0.05, h - 0.04, 0.05, 'steel', false);
  b.pbox(p, lx - 0.05, 0, -0.05, lx + 0.05, h - 0.04, 0.05, 'steel', false);
  b.pbox(p, -lx - 0.2, 0, -d / 2 + 0.1, -lx + 0.2, 0.03, d / 2 - 0.1, 'metal', false);
  b.pbox(p, lx - 0.2, 0, -d / 2 + 0.1, lx + 0.2, 0.03, d / 2 - 0.1, 'metal', false);
  col(k, p, -w / 2, 0.45, -d / 2, w / 2, h, d / 2);
  col(k, p, -lx - 0.06, 0, -0.06, -lx + 0.06, h, 0.06);
  col(k, p, lx - 0.06, 0, -0.06, lx + 0.06, h, 0.06);
}

/** Galley counter: back at local z=-0.65 against a wall, front at z=0. */
export function counter(k: Kit, p: Place, len: number, upper = true): void {
  const b = k.b;
  b.pbox(p, -len / 2, 0.1, -0.65, len / 2, 0.88, -0.02, 'paint', false, 0.01);
  b.pbox(p, -len / 2, 0, -0.62, len / 2, 0.1, -0.08, 'paintDark', false);
  b.pbox(p, -len / 2 - 0.02, 0.88, -0.66, len / 2 + 0.02, 0.92, 0.02, 'steel', false, 0.01);
  b.pbox(p, -len / 2, 0.92, -0.66, len / 2, 1.45, -0.63, 'steel', false);
  for (let x = -len / 2 + 0.6; x < len / 2 - 0.3; x += 0.6) b.pbox(p, x - 0.004, 0.12, -0.02, x + 0.004, 0.86, -0.01, 'paintGrey', false);
  if (upper) {
    b.pbox(p, -len / 2, 1.55, -0.65, len / 2, 2.2, -0.3, 'paint', false, 0.01);
    for (let x = -len / 2 + 0.6; x < len / 2 - 0.3; x += 0.6) b.pbox(p, x - 0.004, 1.56, -0.3, x + 0.004, 2.19, -0.29, 'paintGrey', false);
    b.pbox(p, -len / 2, 1.5, -0.6, len / 2, 1.55, -0.35, 'lightWarm', false);
  }
  col(k, p, -len / 2, 0, -0.65, len / 2, 0.92, 0);
}

export function locker(k: Kit, p: Place, w = 0.6, label = '', key = 'paintGrey'): void {
  const b = k.b;
  b.pbox(p, -w / 2, 0, -0.5, w / 2, 2.0, 0, key, false, 0.01);
  b.pbox(p, -w / 2 + 0.01, 0.02, -0.01, w / 2 - 0.01, 1.98, 0.005, key, false);
  for (let i = 0; i < 4; i++) b.pbox(p, -w / 2 + 0.12, 1.62 + i * 0.05, 0.005, w / 2 - 0.12, 1.635 + i * 0.05, 0.012, 'paintDark', false);
  b.pbox(p, w / 2 - 0.1, 0.9, 0.0, w / 2 - 0.07, 1.15, 0.03, 'steel', false);
  col(k, p, -w / 2, 0, -0.5, w / 2, 2.0, 0);
  if (label) k.pitem(p, -w / 2, 0.3, -0.5, w / 2, 1.9, 0.05, label, 'flavor', label);
}

/** Operator console: user stands on local +z side facing -z. */
export function consoleUnit(k: Kit, p: Place, w: number, kinds: ScreenKind[], seed = 1, opts: { pilot?: boolean } = {}): void {
  const b = k.b;
  b.pbox(p, -w / 2, 0, -0.45, w / 2, 0.82, 0.2, 'paintDark', false, 0.02);
  b.pbox(p, -w / 2, 0.82, -0.45, w / 2, 0.86, 0.32, 'metal', false, 0.01);
  b.pbox(p, -w / 2, 0.86, -0.45, w / 2, 1.0, -0.2, 'paintDark', false, 0.02);
  col(k, p, -w / 2, 0, -0.45, w / 2, 0.86, 0.32);
  const n = kinds.length;
  const sw = Math.min(0.75, (w - 0.1) / n - 0.06);
  kinds.forEach((kind, i) => {
    const x = -w / 2 + (w * (i + 0.5)) / n;
    k.screen(kind, L(p, x, 1.27, -0.3), faceYaw(p), sw, seed + i, '', 0.18);
  });
  // analogue hardware: rows of toggles, knobs and lit push-buttons
  let sd = seed * 7 + 3;
  const rnd = () => ((sd = (sd * 16807) % 2147483647) / 2147483647);
  for (const z of [-0.12, -0.02, 0.08, 0.18]) {
    for (let x = -w / 2 + 0.08; x < w / 2 - 0.06; x += 0.055) {
      const r = rnd();
      if (r < 0.12) continue;
      if (r < 0.45) {
        b.pbox(p, x - 0.012, 0.86, z - 0.012, x + 0.012, 0.866, z + 0.012, 'paintDark', false);
        b.geo(new THREE.BoxGeometry(0.008, 0.045, 0.008), 'chrome', L(p, x, 0.885, z), new THREE.Euler(rnd() > 0.5 ? 0.45 : -0.45, faceYaw(p), 0, 'YXZ'));
      } else if (r < 0.65) {
        b.geo(new THREE.CylinderGeometry(0.019, 0.022, 0.025, 10), 'paintDark', L(p, x, 0.873, z));
        b.pbox(p, x - 0.002, 0.885, z - 0.016, x + 0.002, 0.888, z, 'paint', false);
      } else {
        const key = r < 0.75 ? 'statusAmber' : r < 0.82 ? 'statusGreen' : r < 0.86 ? 'statusRed' : 'paintGrey';
        b.pbox(p, x - 0.016, 0.86, z - 0.016, x + 0.016, 0.875, z + 0.016, key, false);
      }
    }
  }
  if (opts.pilot) {
    for (const sx of [-w / 2 + 0.25, w / 2 - 0.25]) {
      b.geo(new THREE.CylinderGeometry(0.05, 0.06, 0.04, 12), 'paintDark', L(p, sx, 0.88, 0.25));
      b.cyl(L(p, sx, 0.88, 0.25), L(p, sx, 1.08, 0.3), 0.014, 'metal', 8);
      b.geo(new THREE.SphereGeometry(0.03, 10, 8), 'rubber', L(p, sx, 1.1, 0.31));
    }
    // throttle quadrant
    b.pbox(p, -0.12, 0.86, 0.12, 0.12, 0.92, 0.3, 'paintDark', false, 0.01);
    for (const tx of [-0.07, 0, 0.07]) b.cyl(L(p, tx, 0.92, 0.2), L(p, tx, 1.02, 0.17), 0.008, 'chrome', 6);
  }
}

export function plant(k: Kit, p: Place, size = 1): void {
  const b = k.b;
  b.geo(new THREE.CylinderGeometry(0.2 * size, 0.16 * size, 0.42 * size, 14), 'paintGrey', L(p, 0, 0.21 * size, 0));
  b.geo(new THREE.CylinderGeometry(0.19 * size, 0.19 * size, 0.02, 14), 'soil', L(p, 0, 0.41 * size, 0));
  let s = (p.x * 13 + p.z * 7) | 0;
  const rnd = () => ((s = (s * 16807 + 11) % 2147483647) / 2147483647);
  for (let i = 0; i < 7; i++) {
    const a = rnd() * Math.PI * 2;
    const r = rnd() * 0.18 * size;
    const leaf = new THREE.IcosahedronGeometry((0.13 + rnd() * 0.1) * size, 0);
    b.geo(leaf, i % 2 ? 'plant' : 'plantDark', V(p.x + Math.cos(a) * r, p.y + (0.5 + rnd() * 0.45) * size, p.z + Math.sin(a) * r), new THREE.Euler(rnd(), rnd(), rnd()));
  }
  col(k, p, -0.2 * size, 0, -0.2 * size, 0.2 * size, 0.5 * size, 0.2 * size);
}

export function crate(k: Kit, x: number, y: number, z: number, w: number, h: number, d: number, key = 'paintGrey'): void {
  const b = k.b;
  b.box(x - w / 2, y, z - d / 2, x + w / 2, y + h, z + d / 2, key, 'solid', 0.02);
  b.box(x - w / 2 - 0.01, y + h * 0.15, z - d / 2 - 0.01, x + w / 2 + 0.01, y + h * 0.22, z + d / 2 + 0.01, 'paintDark', false);
  b.box(x - w / 2 - 0.01, y + h * 0.78, z - d / 2 - 0.01, x + w / 2 + 0.01, y + h * 0.85, z + d / 2 + 0.01, 'paintDark', false);
}

/** Cryo pod: long axis along local z, head at -z. */
export function cryoPod(k: Kit, p: Place, num: number, failed: boolean, nameplate: string): void {
  const b = k.b;
  b.pbox(p, -0.46, 0, -1.12, 0.46, 0.52, 1.12, 'paintGrey', false, 0.04);
  b.pbox(p, -0.44, 0.08, -1.1, 0.44, 0.12, 1.1, failed ? 'podFail' : 'podGlow', false);
  b.pbox(p, -0.4, 0.52, -1.02, 0.4, 0.98, 1.02, 'frost', false, 0.16);
  b.pbox(p, -0.17, 0.56, -0.62, 0.17, 0.74, 0.86, 'sleeper', false, 0.08);
  b.geo(new THREE.SphereGeometry(0.13, 12, 10), 'sleeper', L(p, 0, 0.68, -0.8));
  b.pbox(p, -0.3, 0.52, -1.16, 0.3, 0.95, -1.08, 'metal', false, 0.02);
  b.pbox(p, -0.06, 0.82, -1.165, 0.06, 0.88, -1.155, failed ? 'statusRed' : 'statusGreen', false);
  col(k, p, -0.46, 0, -1.12, 0.46, 1.0, 1.12);
  k.pitem(p, -0.46, 0.4, -1.15, 0.46, 1.05, 1.12, `Read nameplate · Pod ${String(num).padStart(4, '0')}`, 'pod', nameplate, 2.2);
}

export function telescope(k: Kit, p: Place): void {
  const b = k.b;
  b.pbox(p, -0.3, 0, -0.3, 0.3, 0.06, 0.3, 'metal', false, 0.02);
  b.cyl(L(p, 0, 0.06, 0), L(p, 0, 1.2, 0), 0.06, 'steel');
  b.pbox(p, -0.12, 1.15, -0.12, 0.12, 1.32, 0.12, 'metal', false, 0.03);
  b.cyl(L(p, 0, 1.25, -0.55), L(p, 0, 1.55, 0.95), 0.13, 'paint', 20);
  b.cyl(L(p, 0, 1.54, 0.93), L(p, 0, 1.56, 0.97), 0.135, 'blackGlass', 20);
  b.cyl(L(p, 0, 1.25, -0.55), L(p, 0, 1.22, -0.7), 0.04, 'metal');
  col(k, p, -0.3, 0, -0.3, 0.3, 1.4, 0.3);
  k.pitem(p, -0.35, 0.9, -0.8, 0.35, 1.7, 1.0, 'Use telescope', 'telescope');
}

export function medBed(k: Kit, p: Place): void {
  const b = k.b;
  b.pbox(p, -0.25, 0, -0.6, 0.25, 0.62, 0.6, 'paintGrey', false, 0.03);
  b.pbox(p, -0.45, 0.62, -1.05, 0.45, 0.78, 1.05, 'fabricLight', false, 0.06);
  b.pbox(p, -0.75, 0, -0.1, -0.65, 2.3, 0.1, 'paint', false, 0.02);
  b.pbox(p, 0.65, 0, -0.1, 0.75, 2.3, 0.1, 'paint', false, 0.02);
  b.pbox(p, -0.75, 2.18, -0.16, 0.75, 2.3, 0.16, 'paint', false, 0.03);
  b.pbox(p, -0.6, 2.14, -0.1, 0.6, 2.18, 0.1, 'lightCold', false);
  b.cyl(L(p, 0.5, 3.0, 0.8), L(p, 0.3, 2.2, 0.6), 0.05, 'steel');
  b.cyl(L(p, 0.3, 2.2, 0.6), L(p, 0.1, 1.6, 0.4), 0.04, 'steel');
  b.geo(new THREE.SphereGeometry(0.08, 12, 8), 'metal', L(p, 0.1, 1.58, 0.4));
  col(k, p, -0.45, 0, -1.05, 0.45, 0.8, 1.05);
  col(k, p, -0.76, 0, -0.1, -0.64, 2.3, 0.1);
  col(k, p, 0.64, 0, -0.1, 0.76, 2.3, 0.1);
  k.seat({ ...p, rot: p.rot }, 0, 0.8, -0.55, 'Medical bed', 'lie', false, 0.95);
}

export function labIsland(k: Kit, p: Place, len: number): void {
  const b = k.b;
  b.pbox(p, -len / 2, 0, -0.6, len / 2, 0.88, 0.6, 'paint', false, 0.02);
  b.pbox(p, -len / 2 - 0.03, 0.88, -0.63, len / 2 + 0.03, 0.92, 0.63, 'paintDark', false, 0.01);
  b.pbox(p, -len / 2, 0, -0.5, len / 2, 0.08, 0.5, 'paintDark', false);
  col(k, p, -len / 2, 0, -0.63, len / 2, 0.92, 0.63);
  // shelf spine with lights
  b.pbox(p, -len / 2 + 0.2, 0.92, -0.04, len / 2 - 0.2, 1.6, 0.04, 'metal', false);
  b.pbox(p, -len / 2 + 0.2, 1.6, -0.18, len / 2 - 0.2, 1.64, 0.18, 'metal', false);
  b.pbox(p, -len / 2 + 0.25, 1.58, -0.15, len / 2 - 0.25, 1.6, 0.15, 'lightCold', false);
  // microscope
  const m = L(p, -len / 2 + 0.6, 0.92, 0.3);
  b.box(m.x - 0.15, m.y, m.z - 0.12, m.x + 0.15, m.y + 0.05, m.z + 0.12, 'paint', false, 0.02);
  b.cyl(V(m.x, m.y + 0.05, m.z - 0.08), V(m.x, m.y + 0.42, m.z - 0.08), 0.035, 'paint');
  b.cyl(V(m.x, m.y + 0.38, m.z - 0.08), V(m.x, m.y + 0.3, m.z + 0.08), 0.045, 'paintDark');
  b.cyl(V(m.x, m.y + 0.42, m.z - 0.08), V(m.x, m.y + 0.52, m.z - 0.14), 0.02, 'paintDark');
  k.item({ id: k.uid('micro'), min: [m.x - 0.3, m.y, m.z - 0.3], max: [m.x + 0.3, m.y + 0.6, m.z + 0.3], prompt: 'Use microscope', action: 'lab', data: 'microscope' });
  // sequencer
  const s = L(p, len / 2 - 0.8, 0.92, 0.3);
  b.box(s.x - 0.35, s.y, s.z - 0.25, s.x + 0.35, s.y + 0.45, s.z + 0.25, 'paint', false, 0.03);
  b.box(s.x - 0.25, s.y + 0.12, s.z - 0.26, s.x + 0.25, s.y + 0.32, s.z + 0.26, 'blackGlass', false);
  k.screen('dna', L(p, len / 2 - 0.8, 1.6, 0.04 + 0.06), faceYaw(p), 0.6, 3, '', 0);
  k.item({ id: k.uid('seq'), min: [s.x - 0.4, s.y, s.z - 0.3], max: [s.x + 0.4, s.y + 0.6, s.z + 0.3], prompt: 'Use gene sequencer', action: 'lab', data: 'sequencer' });
  // sample racks
  for (let i = 0; i < 8; i++) b.cyl(L(p, -0.3 + i * 0.07, 0.92, -0.35), L(p, -0.3 + i * 0.07, 1.04, -0.35), 0.014, 'glassInner', 8);
  b.pbox(p, -0.35, 0.92, -0.42, 0.25, 0.97, -0.28, 'paintGrey', false);
}

export function tank(k: Kit, p: Place, label: string): void {
  const b = k.b;
  b.geo(new THREE.CylinderGeometry(0.62, 0.66, 0.3, 24), 'metal', L(p, 0, 0.15, 0));
  b.geo(new THREE.CylinderGeometry(0.55, 0.55, 1.8, 24, 1, true), 'glassInner', L(p, 0, 1.2, 0));
  b.geo(new THREE.CylinderGeometry(0.66, 0.62, 0.35, 24), 'metal', L(p, 0, 2.27, 0));
  b.geo(new THREE.TorusGeometry(0.5, 0.025, 6, 32), 'podGlow', L(p, 0, 0.33, 0), new THREE.Euler(Math.PI / 2, 0, 0));
  b.cyl(L(p, 0, 2.45, 0), L(p, 0, 3.0, 0), 0.08, 'steel');
  col(k, p, -0.62, 0, -0.62, 0.62, 2.45, 0.62);
  k.pitem(p, -0.6, 0.5, -0.6, 0.6, 2.2, 0.6, label, 'flavor', label);
}

export function treadmill(k: Kit, p: Place): void {
  const b = k.b;
  b.pbox(p, -0.4, 0, -0.9, 0.4, 0.18, 0.9, 'paintDark', false, 0.03);
  b.pbox(p, -0.32, 0.18, -0.85, 0.32, 0.2, 0.85, 'rubber', false);
  b.pbox(p, -0.4, 0.18, 0.75, -0.35, 1.2, 0.8, 'steel', false);
  b.pbox(p, 0.35, 0.18, 0.75, 0.4, 1.2, 0.8, 'steel', false);
  b.pbox(p, -0.42, 1.15, 0.65, 0.42, 1.3, 0.85, 'paintDark', false, 0.03);
  col(k, p, -0.4, 0, -0.9, 0.4, 0.2, 0.9);
  col(k, p, -0.42, 0, 0.65, 0.42, 1.3, 0.85);
  k.pitem(p, -0.4, 0.2, -0.9, 0.4, 1.3, 0.9, 'Run on treadmill', 'flavor', 'treadmill');
}

export function weightBench(k: Kit, p: Place): void {
  const b = k.b;
  b.pbox(p, -0.18, 0.35, -0.65, 0.18, 0.45, 0.65, 'fabric', false, 0.04);
  b.pbox(p, -0.05, 0, -0.5, 0.05, 0.35, 0.5, 'metal', false);
  b.pbox(p, -0.6, 0, -0.6, -0.55, 1.2, -0.55, 'steel', false);
  b.pbox(p, 0.55, 0, -0.6, 0.6, 1.2, -0.55, 'steel', false);
  b.cyl(L(p, -0.8, 1.15, -0.58), L(p, 0.8, 1.15, -0.58), 0.02, 'chrome');
  for (const sx of [-0.7, 0.7]) b.cyl(L(p, sx - 0.04, 1.15, -0.58), L(p, sx + 0.04, 1.15, -0.58), 0.2, 'paintDark', 16);
  col(k, p, -0.2, 0, -0.65, 0.2, 0.45, 0.65);
  k.seat(p, 0, 0.45, 0.2, 'Weight bench');
}

export function showerStall(k: Kit, p: Place): void {
  const b = k.b;
  b.pbox(p, -0.5, 0, -0.5, 0.5, 0.06, 0.5, 'paintGrey', 'solid');
  b.pbox(p, -0.5, 0, -0.5, 0.5, 2.3, -0.46, 'paint', 'wall');
  b.pbox(p, -0.52, 0, -0.5, -0.48, 2.3, 0.5, 'glassInner', 'wall');
  b.pbox(p, 0.48, 0, -0.5, 0.52, 2.3, 0.5, 'glassInner', 'wall');
  b.cyl(L(p, 0, 2.1, -0.46), L(p, 0, 2.15, -0.25), 0.02, 'chrome');
  b.geo(new THREE.CylinderGeometry(0.1, 0.08, 0.04, 16), 'chrome', L(p, 0, 2.13, -0.22));
  k.pitem(p, -0.45, 0.8, -0.45, 0.45, 2.0, 0.3, 'Turn on shower', 'shower', `${p.x},${p.z}`);
}

export function planter(k: Kit, p: Place, len: number): void {
  const b = k.b;
  b.pbox(p, -len / 2, 0, -0.4, len / 2, 0.7, 0.4, 'paintGrey', 'solid', 0.03);
  b.pbox(p, -len / 2 + 0.05, 0.66, -0.35, len / 2 - 0.05, 0.69, 0.35, 'soil', false);
  let s = Math.abs((p.x * 31 + p.z * 17) | 0) + 3;
  const rnd = () => ((s = (s * 16807 + 7) % 2147483647) / 2147483647);
  for (let x = -len / 2 + 0.2; x < len / 2 - 0.15; x += 0.24) {
    for (const z of [-0.18, 0.05, 0.22]) {
      const hgt = 0.15 + rnd() * 0.45;
      const pos = L(p, x + (rnd() - 0.5) * 0.1, 0.69 + hgt / 2, z + (rnd() - 0.5) * 0.08);
      if (rnd() > 0.5) b.geo(new THREE.ConeGeometry(0.06 + rnd() * 0.05, hgt, 5), rnd() > 0.5 ? 'plant' : 'plantDark', pos, new THREE.Euler((rnd() - 0.5) * 0.4, rnd() * 3, 0));
      else b.geo(new THREE.IcosahedronGeometry(0.06 + rnd() * 0.08, 0), 'plant', pos.setY(pos.y - hgt / 2 + 0.08), new THREE.Euler(rnd(), rnd(), rnd()));
    }
  }
  b.pbox(p, -len / 2 + 0.1, 2.25, -0.08, len / 2 - 0.1, 2.3, 0.08, 'metal', false);
  b.pbox(p, -len / 2 + 0.12, 2.23, -0.05, len / 2 - 0.12, 2.25, 0.05, 'growLight', false);
  k.pitem(p, -len / 2, 0.5, -0.45, len / 2, 1.2, 0.45, 'Tend the seedlings', 'plants');
}

export function shelves(k: Kit, p: Place, len: number, levels = 4, depth = 0.6): void {
  const b = k.b;
  for (const x of [-len / 2, len / 2 - 0.06]) b.pbox(p, x, 0, -depth, x + 0.06, 2.2, 0, 'metal', false);
  let s = Math.abs((p.x * 7 + p.z * 3) | 0) + 1;
  const rnd = () => ((s = (s * 16807 + 3) % 2147483647) / 2147483647);
  for (let i = 0; i < levels; i++) {
    const y = 0.1 + i * (2.0 / levels);
    b.pbox(p, -len / 2, y, -depth, len / 2, y + 0.04, 0, 'steel', false);
    for (let x = -len / 2 + 0.1; x < len / 2 - 0.3; x += 0.35 + rnd() * 0.2) {
      if (rnd() < 0.25) continue;
      const w = 0.25 + rnd() * 0.2;
      const h = 0.15 + rnd() * 0.25;
      b.pbox(p, x, y + 0.04, -depth + 0.05, x + w, y + 0.04 + h, -0.08, rnd() > 0.5 ? 'paintGrey' : 'paint', false, 0.015);
    }
  }
  col(k, p, -len / 2, 0, -depth, len / 2, 2.2, 0);
}

export function machine(k: Kit, p: Place, w: number, d: number, h: number, seed = 1): void {
  const b = k.b;
  b.pbox(p, -w / 2, 0, -d / 2, w / 2, h, d / 2, 'paintGrey', 'solid', 0.04);
  b.pbox(p, -w / 2 + 0.08, h * 0.3, d / 2, w / 2 - 0.08, h * 0.32, d / 2 + 0.01, 'paintDark', false);
  for (let i = 0; i < 6; i++) b.pbox(p, -w / 2 + 0.15, h * 0.5 + i * 0.05, d / 2, -w / 2 + 0.6, h * 0.5 + i * 0.05 + 0.02, d / 2 + 0.01, 'paintDark', false);
  b.pbox(p, w / 2 - 0.3, h * 0.7, d / 2, w / 2 - 0.22, h * 0.72, d / 2 + 0.015, seed % 3 === 0 ? 'statusAmber' : 'statusGreen', false);
  b.cyl(L(p, -w / 4, h, 0), L(p, -w / 4, 3.0, 0), 0.08, 'steel');
  b.cyl(L(p, w / 4, h, -d / 4), L(p, w / 4, 3.0, -d / 4), 0.05, 'paintDark');
}

export function weaponRack(k: Kit, p: Place): void {
  const b = k.b;
  b.pbox(p, -0.9, 0, -0.45, 0.9, 2.1, 0, 'paintDark', false, 0.02);
  b.pbox(p, -0.85, 0.1, -0.02, 0.85, 2.0, 0.01, 'glassInner', false);
  for (let i = 0; i < 4; i++) {
    const x = -0.6 + i * 0.4;
    b.pbox(p, x - 0.04, 0.5, -0.25, x + 0.04, 1.4, -0.15, 'metal', false);
    b.pbox(p, x - 0.05, 1.1, -0.28, x + 0.05, 1.25, -0.1, 'metal', false);
  }
  b.pbox(p, -0.9, 2.02, -0.02, 0.9, 2.05, 0.01, 'statusRed', false);
  col(k, p, -0.9, 0, -0.45, 0.9, 2.1, 0.02);
  k.pitem(p, -0.9, 0.3, -0.45, 0.9, 2.0, 0.1, 'Armory rack · locked', 'locked', "Armory rack. Firearms are released on the captain's authority only.");
}

/** EVA suit hanging in an open locker (front faces +z). */
export function suitLocker(k: Kit, p: Place, name: string): void {
  const b = k.b;
  b.pbox(p, -0.45, 0, -0.55, 0.45, 2.25, -0.5, 'paintGrey', false);
  b.pbox(p, -0.47, 0, -0.55, -0.43, 2.25, 0.05, 'paintGrey', false);
  b.pbox(p, 0.43, 0, -0.55, 0.47, 2.25, 0.05, 'paintGrey', false);
  b.pbox(p, -0.45, 2.21, -0.55, 0.45, 2.25, 0.05, 'paintGrey', false);
  // suit
  b.pbox(p, -0.22, 1.05, -0.38, 0.22, 1.62, -0.12, 'paint', false, 0.08);
  b.pbox(p, -0.18, 1.35, -0.4, 0.18, 1.6, -0.36, 'accent-spine', false, 0.02);
  b.geo(new THREE.SphereGeometry(0.17, 18, 14), 'paint', L(p, 0, 1.82, -0.25));
  b.geo(new THREE.SphereGeometry(0.15, 18, 14, 0, Math.PI, 0, Math.PI), 'blackGlass', L(p, 0, 1.82, -0.21), new THREE.Euler(0, faceYaw(p) - Math.PI / 2, 0));
  for (const sx of [-1, 1]) {
    b.cyl(L(p, sx * 0.26, 1.58, -0.25), L(p, sx * 0.3, 1.0, -0.22), 0.07, 'paint');
    b.cyl(L(p, sx * 0.11, 1.05, -0.25), L(p, sx * 0.12, 0.12, -0.24), 0.085, 'paint');
  }
  b.pbox(p, -0.3, 1.1, -0.5, 0.3, 1.6, -0.38, 'paintGrey', false, 0.05);
  col(k, p, -0.47, 0, -0.55, 0.47, 2.25, 0.05);
  k.pitem(p, -0.4, 0.6, -0.5, 0.4, 2.0, 0.05, `EVA suit · ${name}`, 'flavor', `suit:${name}`);
}

/** Wall-mounted unit with a screen (coffee, food, music). Back to wall at local z=0. */
export function wallUnit(k: Kit, p: Place, w: number, h: number, y: number, kind: ScreenKind, prompt: string, action: string, data?: unknown): void {
  const b = k.b;
  b.pbox(p, -w / 2, y, 0, w / 2, y + h, 0.28, 'paint', false, 0.03);
  b.pbox(p, -w / 2 + 0.05, y + 0.05, 0.28, w / 2 - 0.05, y + h * 0.35, 0.3, 'blackGlass', false);
  k.screen(kind, L(p, 0, y + h * 0.68, 0.29), faceYaw(p), Math.min(w - 0.12, 0.5), 7, '', 0);
  k.pitem(p, -w / 2, y, 0, w / 2, y + h, 0.4, prompt, action, data);
}

export function pipeRun(k: Kit, a: THREE.Vector3, bpos: THREE.Vector3, r = 0.06, key = 'steel'): void {
  k.b.cyl(a, bpos, r, key, 10);
}

export function holoTable(k: Kit, p: Place): THREE.Vector3 {
  const b = k.b;
  b.geo(new THREE.CylinderGeometry(0.95, 0.75, 0.9, 32), 'paintDark', L(p, 0, 0.45, 0));
  b.geo(new THREE.CylinderGeometry(0.98, 0.98, 0.05, 32), 'metal', L(p, 0, 0.92, 0));
  b.geo(new THREE.TorusGeometry(0.8, 0.02, 6, 48), 'podGlow', L(p, 0, 0.95, 0), new THREE.Euler(Math.PI / 2, 0, 0));
  b.geo(new THREE.CylinderGeometry(0.7, 0.7, 0.02, 32), 'blackGlass', L(p, 0, 0.955, 0));
  col(k, p, -0.9, 0, -0.9, 0.9, 0.95, 0.9);
  k.pitem(p, -0.95, 0.7, -0.95, 0.95, 1.8, 0.95, 'Orbital map', 'orbitalMap');
  return L(p, 0, 1.45, 0);
}


export type PodState = 'open' | 'sleeping' | 'burned' | 'revival';

/** Crew hypersleep pod: white shell, padded bed, head console, black-bordered canopy.
 *  Long axis along local z, head at -z. Returns the lie-down seat for an open pod. */
export function crewPod(k: Kit, p: Place, state: PodState, name: string, info: string): ReturnType<Kit['seat']> | null {
  const b = k.b;
  b.pbox(p, -0.5, 0, -1.12, 0.5, 0.06, 1.12, 'paintDark', false, 0.02);
  b.pbox(p, -0.3, 0.06, -0.8, 0.3, 0.42, 0.8, 'ribDark', false, 0.02);
  b.pbox(p, -0.48, 0.42, -1.15, 0.48, 0.8, 1.15, state === 'burned' ? 'soot' : 'podShell', false, 0.12);
  b.pbox(p, -0.36, 0.7, -1.0, 0.36, 0.8, 1.05, 'fabricLight', false, 0.05);
  b.pbox(p, -0.2, 0.8, -1.0, 0.2, 0.86, -0.76, 'fabricLight', false, 0.03);
  b.pbox(p, -0.46, 0.48, -1.16, 0.46, 0.52, 1.16, state === 'burned' ? 'podFail' : state === 'revival' ? 'statusAmber' : 'podGlow', false);
  // head console with readout
  b.pbox(p, -0.42, 0.8, -1.24, 0.42, 1.32, -1.08, state === 'burned' ? 'soot' : 'podShell', false, 0.04);
  k.screen('vitals', L(p, 0, 1.08, -1.065), faceYaw(p), 0.38, 52, '', 0.25);
  const hinge = { y: 0.82, z: -1.0 };
  if (state === 'open') {
    const a = -1.2;
    const cy = 0.14 * Math.cos(a) - 1.05 * Math.sin(a);
    const cz = 0.14 * Math.sin(a) + 1.05 * Math.cos(a);
    const rot = new THREE.Euler(a, faceYaw(p), 0, 'YXZ');
    b.geo(new THREE.BoxGeometry(0.84, 0.3, 2.1), 'glassInner', L(p, 0, hinge.y + cy, hinge.z + cz), rot);
    // black-bordered rim of the raised canopy (four bars along its lower edge)
    const yl = [0, Math.cos(a), Math.sin(a)];
    const zl = [0, -Math.sin(a), Math.cos(a)];
    const at = (ox: number, oy: number, oz: number) => L(p, ox, hinge.y + cy + oy * yl[1] + oz * zl[1], hinge.z + cz + oy * yl[2] + oz * zl[2]);
    for (const sx of [-0.43, 0.43]) b.geo(new THREE.BoxGeometry(0.05, 0.06, 2.12), 'blackGlass', at(sx, -0.14, 0), rot);
    for (const sz of [-1.05, 1.05]) b.geo(new THREE.BoxGeometry(0.9, 0.06, 0.05), 'blackGlass', at(0, -0.14, sz), rot);
  } else {
    b.pbox(p, -0.45, 0.8, -1.02, 0.45, 0.84, 1.12, 'blackGlass', false, 0.02);
    b.pbox(p, -0.42, 0.84, -1.0, 0.42, 1.12, 1.1, state === 'burned' ? 'soot' : state === 'revival' ? 'glassInner' : 'frost', false, 0.14);
    if (state !== 'burned') {
      b.pbox(p, -0.17, 0.82, -0.62, 0.17, 0.98, 0.86, 'sleeper', false, 0.08);
      b.geo(new THREE.SphereGeometry(0.13, 12, 10), 'sleeper', L(p, 0, 0.92, -0.8));
    }
  }
  col(k, p, -0.5, 0, -1.24, 0.5, state === 'open' ? 0.8 : 1.12, 1.15);
  k.pitem(p, -0.5, 0.5, -1.25, 0.5, 1.4, 1.15, `Pod · ${name}`, 'pod', info, 2.4);
  if (state === 'open') return k.seat(p, 0, 0.78, -0.5, `Your pod`, 'lie', false, 1.3, [0, -1]);
  return null;
}

/** Terraforming earthmover, clamped and strapped to the deck. Nose along local +z. */
export function earthmover(k: Kit, p: Place, tag: string): void {
  const b = k.b;
  b.pbox(p, -1.3, 0.9, -4.0, 1.3, 1.75, 4.0, 'ribDark', false, 0.05);
  for (const z of [-3.0, 0, 3.0]) {
    for (const sx of [-1, 1]) {
      b.geo(new THREE.CylinderGeometry(0.98, 0.98, 0.72, 28), 'rubber', L(p, sx * 1.62, 0.98, z), new THREE.Euler(0, faceYaw(p), Math.PI / 2, 'YXZ'));
      b.geo(new THREE.CylinderGeometry(0.45, 0.45, 0.74, 16), 'paintDark', L(p, sx * 1.62, 0.98, z), new THREE.Euler(0, faceYaw(p), Math.PI / 2, 'YXZ'));
      b.pbox(p, sx > 0 ? 1.2 : -2.0, 1.9, z - 1.05, sx > 0 ? 2.0 : -1.2, 2.02, z + 1.05, 'warning', false, 0.03);
    }
  }
  b.pbox(p, -1.75, 1.75, 2.2, 0.15, 3.45, 4.3, 'warning', false, 0.12);
  b.pbox(p, -1.6, 2.5, 4.28, 0.0, 3.25, 4.32, 'blackGlass', false);
  b.pbox(p, -1.78, 2.5, 2.5, -1.74, 3.25, 4.0, 'blackGlass', false);
  b.pbox(p, 0.35, 1.75, 2.0, 1.75, 2.85, 4.45, 'warning', false, 0.08);
  for (let i = 0; i < 5; i++) b.pbox(p, 0.5, 2.0 + i * 0.13, 4.45, 1.6, 2.06 + i * 0.13, 4.47, 'paintDark', false);
  b.pbox(p, -1.9, 1.85, -4.6, 1.9, 3.7, 1.7, 'warning', false, 0.1);
  b.pbox(p, -1.7, 3.55, -4.4, 1.7, 3.71, 1.5, 'paintDark', false);
  b.cyl(L(p, 1.2, 2.8, 3.2), L(p, 1.2, 4.0, 3.2), 0.1, 'paintDark', 10);
  k.graphic(tag, L(p, 1.91, 2.75, -1.5), faceYaw(p, 1, 0), 1.4, 0.7, { w: 256, h: 128, fg: '#151515' });
  k.graphic(tag, L(p, -1.91, 2.75, -1.5), faceYaw(p, -1, 0), 1.4, 0.7, { w: 256, h: 128, fg: '#151515' });
  // tie-down straps to deck anchors
  for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]] as const) {
    const a0 = L(p, sx * 1.3, 1.3, sz * 3.9);
    const a1 = L(p, sx * 2.9, 0.04, sz * 5.3);
    b.cyl(a0, a1, 0.035, 'warning', 6);
    b.pbox(p, sx * 2.9 - 0.25, 0, sz * 5.3 - 0.25, sx * 2.9 + 0.25, 0.06, sz * 5.3 + 0.25, 'ribDark', false, 0.02);
    b.pbox(p, sx * 1.62 - 0.5, 0, sz * 3.0 - 0.15, sx * 1.62 + 0.5, 0.12, sz * 3.0 + 0.15, 'hazard', false);
  }
  col(k, p, -2.0, 0, -4.6, 2.0, 3.7, 4.5);
  k.pitem(p, -2.0, 0.5, -4.6, 2.0, 3.5, 4.5, `Terraforming vehicle · ${tag}`, 'flavor', `${tag}. A forty-tonne earthmover, strapped to the deck for seven years. It will dig Haven's first foundations, if we ever get there.`, 3.2);
}
