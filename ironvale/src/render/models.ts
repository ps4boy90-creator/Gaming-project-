// Hand-built low-poly procedural models for every placeable object, plus
// scenery and vehicles. Everything is merged vertex-coloured geometry (see
// modelkit.ts): no textures, no per-part materials.
//
// Conventions: 1 unit = one tile, +Y up, floor at y = 0, each model centred on
// its footprint in X/Z, "front" faces +Z. Vehicles run along +X (nose at +X).
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { MB, type ModelResult, type PartOpts } from './modelkit';

export type SceneryKind = 'tree_oak' | 'tree_round' | 'tree_pine' | 'bush' | 'rock' | 'bus' | 'truck' | 'car' | 'streetlight';

// ------------------------------------------------------------------ palette
const C = {
  steel: 0xa9b1ba,
  steelD: 0x8b939c,
  steelL: 0xc9d0d6,
  frame: 0x6b7480,
  gun: 0x4a525c,
  dark: 0x3a4048,
  darker: 0x2c3138,
  black: 0x24282e,
  white: 0xf2f2ee,
  cream: 0xeeeae0,
  beige: 0xd9d2c0,
  mattress: 0xd8d3c4,
  blanket: 0x7d8ea3,
  blanketD: 0x6c7d93,
  orange: 0xc9703a,
  wood: 0xa9794e,
  woodD: 0x8a5f3c,
  woodL: 0xc49a6c,
  bark: 0x7a5a3c,
  blue: 0x4f7fb5,
  blueD: 0x3f6694,
  navy: 0x2f4a78,
  slate: 0x46586e,
  slateD: 0x3f4a59,
  teal: 0x4f9a94,
  red: 0xb8473f,
  redD: 0x8f3a34,
  yellow: 0xe3b93f,
  gold: 0xd4a94a,
  purple: 0x8a66a8,
  pink: 0xe08fae,
  green: 0x4f9a4a,
  greenD: 0x3e8442,
  greenL: 0x6bb35a,
  pine: 0x2f6e4a,
  concrete: 0xbdb8ab,
  concreteD: 0x9a968a,
  card: 0xc2a070,
  cardL: 0xd6bc8c,
  glass: 0x2b3440,
  screen: 0x7ab6e6,
  lamp: 0xfff1c9,
};

const HP = Math.PI / 2;

// ------------------------------------------------------------------ helpers
type Fn = () => ModelResult;

/** Deterministic pseudo-random numbers so models are identical on every build. */
function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function trivialIndex(g: THREE.BufferGeometry) {
  const n = g.attributes.position.count;
  const idx = new Uint32Array(n);
  for (let i = 0; i < n; i++) idx[i] = i;
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  return g;
}

/** Re-shade a geometry with flat (per-face) normals for a crisp low-poly look. */
function facet(g: THREE.BufferGeometry): THREE.BufferGeometry {
  const n = g.toNonIndexed();
  n.computeVertexNormals();
  g.dispose();
  return trivialIndex(n);
}

/** Flatten anything that pokes below the floor so nothing z-fights with it. */
function clampFloor(g: THREE.BufferGeometry) {
  const p = g.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < p.count; i++) if (p.getY(i) < 0) p.setY(i, 0);
  p.needsUpdate = true;
}

/**
 * Build a model from two builders: `m` keeps each primitive's own normals,
 * `f` is re-shaded flat (faceted cones, pyramids, low-segment trunks...).
 */
function model(fn: (m: MB, f: MB) => void): ModelResult {
  const m = new MB();
  const f = new MB();
  fn(m, f);
  const a = m.build();
  const b = f.build();
  const solids: THREE.BufferGeometry[] = [];
  if (a.solid.attributes.position) solids.push(a.solid);
  if (b.solid.attributes.position) solids.push(facet(b.solid));
  const glows: THREE.BufferGeometry[] = [];
  if (a.glow) glows.push(a.glow);
  if (b.glow) glows.push(b.glow);
  const solid = solids.length === 1 ? solids[0] : mergeGeometries(solids, false)!;
  clampFloor(solid);
  solid.computeBoundingBox();
  solid.computeBoundingSphere();
  const res: ModelResult = { solid };
  if (glows.length) {
    res.glow = glows.length === 1 ? glows[0] : mergeGeometries(glows, false)!;
    res.glow.computeBoundingBox();
    res.glow.computeBoundingSphere();
  }
  return res;
}

/** Rotation that takes the +Y axis onto the direction (dx, dy, dz). */
function aim(dx: number, dy: number, dz: number): { rx: number; rz: number; len: number } {
  const len = Math.hypot(dx, dy, dz) || 1;
  return { rx: Math.atan2(dz, dy), rz: -Math.asin(Math.max(-1, Math.min(1, dx / len))), len };
}

/** Square-section beam between two points. `t` = width, `t2` = depth (defaults to t). */
function beam(m: MB, x1: number, y1: number, z1: number, x2: number, y2: number, z2: number, t: number, color: number, t2 = t, o?: PartOpts) {
  const a = aim(x2 - x1, y2 - y1, z2 - z1);
  m.box(t, a.len, t2, (x1 + x2) / 2, (y1 + y2) / 2 - a.len / 2, (z1 + z2) / 2, color, { ...o, rx: a.rx, rz: a.rz });
}

/** Round rod between two points (r1 at the start, r2 at the end). */
function rod(m: MB, x1: number, y1: number, z1: number, x2: number, y2: number, z2: number, r1: number, color: number, seg = 6, r2 = r1, o?: PartOpts) {
  const a = aim(x2 - x1, y2 - y1, z2 - z1);
  m.cyl(r2, r1, a.len, (x1 + x2) / 2, (y1 + y2) / 2 - a.len / 2, (z1 + z2) / 2, color, seg, { ...o, rx: a.rx, rz: a.rz });
}

/** Cylinder lying along Z, centred on (cx, cy, cz). rFront is the radius of the +Z end. */
function cylZ(m: MB, r: number, len: number, cx: number, cy: number, cz: number, color: number, seg = 10, o?: PartOpts, rFront = r) {
  m.cyl(rFront, r, len, cx, cy - len / 2, cz, color, seg, { ...o, rx: HP });
}

/** Cylinder lying along X, centred on (cx, cy, cz). */
function cylX(m: MB, r: number, len: number, cx: number, cy: number, cz: number, color: number, seg = 10, o?: PartOpts) {
  m.cyl(r, r, len, cx, cy - len / 2, cz, color, seg, { ...o, rz: -HP });
}

/** Upright ring facing +Z / -Z, centred on (cx, cy, cz). */
function ringZ(m: MB, r: number, tube: number, cx: number, cy: number, cz: number, color: number, seg = 14, o?: PartOpts) {
  m.torus(r, tube, cx, cy - tube, cz, color, seg, { ...o, rx: HP });
}

/** Four legs at (+-hx, +-hz) around (cx, cz). */
function legs4(m: MB, hx: number, hz: number, h: number, t: number, color: number, cx = 0, cz = 0, y = 0) {
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) m.box(t, h, t, cx + sx * hx, y, cz + sz * hz, color);
}

/**
 * A leaf-like faceted blob whose long axis runs from (x, y, z) along (dx, dy, dz).
 * `len` is its length, `wid` its width, `thick` its thickness.
 */
function leaf(m: MB, x: number, y: number, z: number, dx: number, dy: number, dz: number, len: number, wid: number, thick: number, color: number) {
  const a = aim(dx, dy, dz);
  const ux = dx / a.len, uy = dy / a.len, uz = dz / a.len;
  const r = len / 2;
  const cxp = x + ux * r, cyp = y + uy * r, czp = z + uz * r;
  const flatX = Math.abs(dx) > Math.abs(dz);
  m.blob(r, cxp, cyp - r, czp, color, flatX ? thick / len : wid / len, 1, flatX ? wid / len : thick / len, 0, { rx: a.rx, rz: a.rz });
}

/** Sub-builder that places axis-aligned parts in a frame rotated by `ry` about (ox, oz). */
function grp(m: MB, ox: number, oy: number, oz: number, ry = 0) {
  const c = Math.cos(ry), s = Math.sin(ry);
  const X = (x: number, z: number) => ox + x * c + z * s;
  const Z = (x: number, z: number) => oz - x * s + z * c;
  return {
    box(w: number, h: number, d: number, x: number, y: number, z: number, color: number, o?: PartOpts) {
      m.box(w, h, d, X(x, z), oy + y, Z(x, z), color, { ...o, ry: (o?.ry ?? 0) + ry });
      return this;
    },
    rbox(w: number, h: number, d: number, x: number, y: number, z: number, color: number, r = 0.03, o?: PartOpts) {
      m.rbox(w, h, d, X(x, z), oy + y, Z(x, z), color, r, { ...o, ry: (o?.ry ?? 0) + ry });
      return this;
    },
    cyl(rt: number, rb: number, h: number, x: number, y: number, z: number, color: number, seg = 12, o?: PartOpts) {
      m.cyl(rt, rb, h, X(x, z), oy + y, Z(x, z), color, seg, { ...o, ry: (o?.ry ?? 0) + ry });
      return this;
    },
  };
}

// ================================================================== HOUSING

/** Mattress + blanket + pillow whose top surface is at `top`. Head at -Z. */
function bedding(m: MB, top: number, blanket: number, stripe: number, cheap = false) {
  if (cheap) m.box(0.72, 0.12, 1.66, 0, top - 0.12, 0, C.mattress);
  else m.rbox(0.72, 0.12, 1.66, 0, top - 0.12, 0, C.mattress, 0.04);
  m.rbox(0.745, 0.125, 1.0, 0, top - 0.118, 0.33, blanket, 0.04);
  m.box(0.752, 0.118, 0.07, 0, top - 0.108, 0.62, stripe);
  m.box(0.752, 0.118, 0.11, 0, top - 0.108, -0.12, C.cream); // folded-back sheet
  m.rbox(0.46, 0.07, 0.26, 0, top - 0.006, -0.64, C.cream, 0.03);
}

const bed: Fn = () =>
  model((m) => {
    // steel tube frame
    for (const sx of [-1, 1]) {
      m.box(0.055, 0.62, 0.055, sx * 0.385, 0, -0.885, C.frame);
      m.box(0.055, 0.44, 0.055, sx * 0.385, 0, 0.885, C.frame);
      m.box(0.04, 0.06, 1.74, sx * 0.385, 0.16, 0, C.frame);
    }
    m.box(0.74, 0.03, 1.7, 0, 0.185, 0, C.gun); // slat deck
    m.box(0.8, 0.045, 0.045, 0, 0.59, -0.885, C.frame);
    m.box(0.76, 0.03, 0.03, 0, 0.4, -0.885, C.frame);
    for (const x of [-0.19, 0, 0.19]) m.box(0.028, 0.2, 0.028, x, 0.4, -0.885, C.steelD);
    m.box(0.8, 0.045, 0.045, 0, 0.41, 0.885, C.frame);
    m.box(0.76, 0.03, 0.03, 0, 0.27, 0.885, C.frame);
    bedding(m, 0.34, C.blanket, C.orange);
  });

const bunk: Fn = () =>
  model((m) => {
    for (const sx of [-1, 1]) {
      for (const sz of [-1, 1]) m.box(0.06, 1.22, 0.06, sx * 0.385, 0, sz * 0.885, C.frame);
      m.box(0.04, 0.06, 1.74, sx * 0.385, 0.16, 0, C.frame);
      m.box(0.04, 0.07, 1.74, sx * 0.385, 0.765, 0, C.frame);
      // upper guard rails (open at the foot end on the ladder side)
      m.box(0.03, 0.035, sx < 0 ? 1.74 : 1.2, sx * 0.385, 1.06, sx < 0 ? 0 : -0.27, C.steelD);
      for (const z of sx < 0 ? [-0.45, 0, 0.45] : [-0.45, 0.3]) m.box(0.025, 0.24, 0.025, sx * 0.385, 0.83, z, C.steelD);
    }
    m.box(0.74, 0.03, 1.7, 0, 0.185, 0, C.gun);
    m.box(0.74, 0.03, 1.7, 0, 0.8, 0, C.gun);
    for (const sz of [-1, 1]) {
      m.box(0.78, 0.045, 0.045, 0, 1.17, sz * 0.885, C.frame);
      m.box(0.76, 0.03, 0.03, 0, 0.5, sz * 0.885, C.frame);
    }
    m.box(0.76, 0.03, 0.03, 0, 1.0, -0.885, C.frame);
    // ladder on the foot end
    for (const x of [0.06, 0.3]) m.box(0.03, 1.12, 0.03, x, 0, 0.925, C.steelD);
    for (const y of [0.2, 0.42, 0.64, 0.86, 1.06]) m.box(0.27, 0.028, 0.03, 0.18, y, 0.925, C.steelD);
    bedding(m, 0.34, C.blanket, C.orange, true);
    bedding(m, 0.95, C.blanket, C.orange, true);
  });

const toilet: Fn = () =>
  model((m) => {
    // back unit with integrated basin
    m.rbox(0.58, 0.6, 0.27, 0, 0, -0.285, C.steel, 0.03);
    m.box(0.5, 0.02, 0.2, 0, 0.6, -0.285, C.steelL);
    m.box(0.34, 0.006, 0.12, 0, 0.62, -0.275, C.steelD); // basin recess
    m.cyl(0.016, 0.016, 0.07, 0, 0.62, -0.37, C.frame, 6);
    m.box(0.022, 0.02, 0.08, 0, 0.675, -0.34, C.frame);
    cylZ(m, 0.03, 0.02, -0.17, 0.47, -0.148, C.steelL, 8); // flush button
    // paper roll
    cylX(m, 0.05, 0.09, 0.2, 0.44, -0.12, C.white, 8);
    m.box(0.13, 0.02, 0.03, 0.2, 0.49, -0.14, C.frame);
    // bowl
    m.box(0.24, 0.2, 0.16, 0, 0, -0.1, C.steelD);
    m.cyl(0.15, 0.17, 0.035, 0, 0, 0.07, C.steelD, 12);
    m.cyl(0.2, 0.13, 0.2, 0, 0.03, 0.07, C.steelL, 12);
    m.torus(0.165, 0.036, 0, 0.168, 0.07, C.steel, 14);
    m.cyl(0.132, 0.132, 0.008, 0, 0.226, 0.07, 0x55768e, 12);
  });

const cell_desk: Fn = () =>
  model((m) => {
    m.box(0.82, 0.04, 0.4, 0, 0.42, -0.215, C.wood);
    m.box(0.82, 0.14, 0.035, 0, 0.46, -0.4, C.woodD);
    for (const sx of [-1, 1]) m.box(0.04, 0.42, 0.36, sx * 0.37, 0, -0.22, C.frame);
    m.box(0.7, 0.22, 0.03, 0, 0.18, -0.385, C.frame);
    m.box(0.7, 0.025, 0.2, 0, 0.2, -0.28, C.gun); // foot shelf
    // clutter
    m.box(0.17, 0.03, 0.23, -0.2, 0.46, -0.2, C.red, { ry: 0.25 });
    m.box(0.15, 0.025, 0.2, -0.19, 0.49, -0.2, C.blue, { ry: -0.1 });
    m.cyl(0.036, 0.03, 0.075, 0.24, 0.46, -0.14, C.cream, 8);
    m.box(0.2, 0.006, 0.15, 0.08, 0.46, -0.16, C.white, { ry: -0.2 });
    m.box(0.012, 0.012, 0.13, 0.12, 0.466, -0.15, C.yellow, { ry: 0.5 });
    // bolted stool
    m.cyl(0.11, 0.12, 0.02, 0, 0, 0.2, C.frame, 10);
    m.cyl(0.035, 0.035, 0.21, 0, 0.02, 0.2, C.frame, 8);
    m.cyl(0.155, 0.14, 0.04, 0, 0.22, 0.2, C.steelL, 12);
  });

const locker: Fn = () =>
  model((m) => {
    m.box(0.76, 0.04, 0.48, 0, 0, 0, C.dark);
    m.rbox(0.82, 1.03, 0.52, 0, 0.035, 0, 0x6a7f98, 0.02);
    m.box(0.84, 0.03, 0.54, 0, 1.055, 0, 0x586b83);
    for (const sx of [-1, 1]) {
      const x = sx * 0.2;
      m.box(0.37, 0.93, 0.02, x, 0.08, 0.262, 0x88a0ba);
      for (let i = 0; i < 3; i++) m.box(0.22, 0.016, 0.008, x, 0.86 + i * 0.04, 0.272, C.darker);
      for (let i = 0; i < 2; i++) m.box(0.22, 0.016, 0.008, x, 0.14 + i * 0.04, 0.272, C.darker);
      m.box(0.03, 0.11, 0.03, x - sx * 0.13, 0.5, 0.272, C.steelL);
      m.box(0.045, 0.05, 0.02, x - sx * 0.13, 0.45, 0.292, C.yellow); // padlock
      m.box(0.11, 0.05, 0.006, x, 0.74, 0.273, C.cream);
      m.box(0.34, 0.9, 0.008, x, 0.1, -0.262, 0x5f7289); // back panels
    }
  });

// ================================================================== HYGIENE

const shower: Fn = () =>
  model((m) => {
    // tiled tray with a low rim and a drain
    m.box(0.86, 0.025, 0.86, 0, 0, 0, 0xcfd9de);
    for (const s of [-1, 1]) {
      m.box(0.86, 0.04, 0.04, 0, 0, s * 0.41, 0xaab6be);
      m.box(0.04, 0.04, 0.78, s * 0.41, 0, 0, 0xaab6be);
      m.box(0.78, 0.004, 0.012, 0, 0.025, s * 0.14, 0xb3c0c8);
      m.box(0.012, 0.004, 0.78, s * 0.14, 0.025, 0, 0xb3c0c8);
    }
    m.cyl(0.075, 0.075, 0.006, 0, 0.025, 0, C.steelD, 10);
    m.cyl(0.045, 0.045, 0.009, 0, 0.025, 0, C.dark, 8);
    // riser pipe, valves, arm and rose
    m.box(0.16, 0.03, 0.1, 0, 0.025, -0.385, C.steelD);
    m.cyl(0.028, 0.028, 1.3, 0, 0.03, -0.385, C.steelL, 8);
    m.box(0.13, 0.1, 0.06, 0, 0.66, -0.375, C.steel);
    m.sphere(0.028, -0.035, 0.682, -0.34, C.red, 1, 1, 1, 6);
    m.sphere(0.028, 0.035, 0.682, -0.34, C.blue, 1, 1, 1, 6);
    m.box(0.13, 0.015, 0.09, 0, 0.92, -0.34, C.steel);
    m.rbox(0.07, 0.03, 0.05, 0, 0.935, -0.33, C.yellow, 0.012);
    m.sphere(0.034, 0, 1.3, -0.385, C.steelL, 1, 1, 1, 6);
    rod(m, 0, 1.335, -0.385, 0, 1.3, -0.09, 0.022, C.steelL, 6);
    m.cyl(0.04, 0.105, 0.06, 0, 1.235, -0.07, C.steel, 10, { rx: 0.2 });
    m.cyl(0.09, 0.09, 0.008, 0, 1.228, -0.068, C.dark, 10, { rx: 0.2 });
  });

const sink: Fn = () =>
  model((m) => {
    m.box(0.3, 0.38, 0.24, 0, 0, -0.24, C.steelD); // pedestal
    m.box(0.36, 0.03, 0.3, 0, 0, -0.24, C.frame);
    // basin with a real recess
    m.box(0.72, 0.05, 0.46, 0, 0.36, -0.15, C.steelD);
    m.box(0.72, 0.1, 0.05, 0, 0.4, 0.055, C.steelL);
    m.box(0.72, 0.1, 0.09, 0, 0.4, -0.335, C.steelL);
    for (const sx of [-1, 1]) m.box(0.05, 0.1, 0.46, sx * 0.335, 0.4, -0.15, C.steelL);
    m.cyl(0.03, 0.03, 0.004, 0, 0.41, -0.12, C.dark, 8);
    // tap
    m.cyl(0.018, 0.018, 0.1, 0, 0.5, -0.34, C.frame, 6);
    m.box(0.026, 0.022, 0.13, 0, 0.59, -0.29, C.frame);
    m.cyl(0.022, 0.022, 0.03, -0.12, 0.5, -0.34, C.red, 6);
    m.cyl(0.022, 0.022, 0.03, 0.12, 0.5, -0.34, C.blue, 6);
    // splashback + mirror
    m.box(0.72, 0.5, 0.04, 0, 0.36, -0.4, 0xd5dde1);
    m.box(0.5, 0.26, 0.012, 0, 0.56, -0.376, C.frame);
    m.box(0.45, 0.21, 0.012, 0, 0.585, -0.372, 0xa9cfdc);
    // soap
    m.cyl(0.03, 0.03, 0.08, 0.27, 0.5, -0.32, 0x58a887, 8);
    m.cyl(0.012, 0.012, 0.035, 0.27, 0.58, -0.32, C.white, 6);
  });

const laundry_machine: Fn = () =>
  model((m) => {
    m.box(0.76, 0.05, 0.7, 0, 0, 0, C.dark);
    m.rbox(0.82, 0.83, 0.76, 0, 0.04, 0, 0xdfe2e0, 0.04);
    // control strip
    m.box(0.74, 0.13, 0.012, 0, 0.705, 0.38, 0x4a5560);
    cylZ(m, 0.042, 0.03, 0.25, 0.77, 0.395, C.steelL, 10);
    m.box(0.2, 0.08, 0.012, -0.24, 0.73, 0.386, C.steelL);
    m.box(0.045, 0.035, 0.012, -0.05, 0.752, 0.388, 0x62b06e);
    m.box(0.045, 0.035, 0.012, 0.03, 0.752, 0.388, C.orange);
    m.box(0.045, 0.035, 0.012, 0.11, 0.752, 0.388, C.cream);
    // porthole door
    ringZ(m, 0.215, 0.045, 0, 0.36, 0.385, C.steel, 16);
    cylZ(m, 0.185, 0.03, 0, 0.36, 0.385, 0x2c4558, 14);
    cylZ(m, 0.105, 0.036, -0.04, 0.31, 0.385, C.orange, 8);
    cylZ(m, 0.06, 0.038, 0.07, 0.4, 0.385, C.cream, 8);
    m.box(0.035, 0.12, 0.035, 0.265, 0.3, 0.4, C.frame);
    // service panel + hose at the back
    m.box(0.5, 0.4, 0.01, 0, 0.12, -0.382, C.steelL);
    m.box(0.1, 0.1, 0.02, 0.2, 0.62, -0.385, C.dark);
    rod(m, 0.2, 0.62, -0.395, 0.3, 0.06, -0.395, 0.018, C.frame, 5);
    // folded laundry + detergent on top
    m.rbox(0.32, 0.05, 0.24, -0.18, 0.87, -0.08, C.cream, 0.02);
    m.rbox(0.3, 0.05, 0.22, -0.17, 0.92, -0.07, C.orange, 0.02, { ry: 0.12 });
    m.cyl(0.055, 0.06, 0.15, 0.22, 0.87, -0.14, C.blue, 8);
    m.cyl(0.025, 0.025, 0.04, 0.22, 1.02, -0.14, C.white, 6);
  });

const laundry_basket: Fn = () =>
  model((m) => {
    for (const sx of [-1, 1])
      for (const sz of [-1, 1]) {
        cylX(m, 0.05, 0.035, sx * 0.3, 0.05, sz * 0.2, C.darker, 8);
        m.box(0.03, 0.06, 0.03, sx * 0.3, 0.07, sz * 0.2, C.frame);
      }
    m.box(0.74, 0.03, 0.54, 0, 0.11, 0, C.frame);
    m.rbox(0.7, 0.4, 0.5, 0, 0.13, 0, 0x5b84b1, 0.05);
    for (const sx of [-1, 1]) {
      for (const sz of [-1, 1]) m.box(0.03, 0.44, 0.03, sx * 0.355, 0.11, sz * 0.255, C.steelD);
      m.box(0.03, 0.03, 0.54, sx * 0.355, 0.52, 0, C.steelD);
    }
    for (const sz of [-1, 1]) m.box(0.74, 0.03, 0.03, 0, 0.52, sz * 0.255, C.steelD);
    // push handle at the back
    for (const sx of [-1, 1]) m.box(0.03, 0.26, 0.03, sx * 0.3, 0.52, -0.29, C.steelD, { rx: -0.2 });
    m.box(0.66, 0.035, 0.035, 0, 0.77, -0.315, C.steelL);
    m.box(0.22, 0.11, 0.006, -0.12, 0.27, 0.252, C.cream);
    // heap of uniforms
    m.blob(0.2, -0.13, 0.4, 0.02, C.orange, 1.25, 0.55, 1);
    m.blob(0.17, 0.15, 0.42, -0.06, C.cream, 1.2, 0.55, 1.1, 1, { ry: 0.6 });
    m.blob(0.12, 0.05, 0.5, 0.1, C.orange, 1.2, 0.55, 1, 0, { ry: 1.1 });
    m.rbox(0.13, 0.17, 0.03, 0.2, 0.38, 0.272, C.orange, 0.012, { rx: -0.08 });
  });

// ================================================================== FOOD

const cooker: Fn = () =>
  model((m) => {
    m.box(0.74, 0.04, 0.64, 0, 0, 0.03, C.dark);
    m.rbox(0.82, 0.5, 0.72, 0, 0.03, 0.03, C.steel, 0.025);
    // splashback
    m.box(0.82, 0.74, 0.05, 0, 0, -0.385, C.steelD);
    m.box(0.82, 0.03, 0.13, 0, 0.71, -0.35, C.steel);
    // hob
    m.box(0.78, 0.025, 0.64, 0, 0.53, 0.04, 0x33383f);
    const hobs: [number, number, number][] = [
      [-0.19, -0.12, C.black],
      [0.19, -0.12, C.black],
      [-0.19, 0.2, C.black],
      [0.19, 0.2, 0xc8553a],
    ];
    for (const [x, z, col] of hobs) {
      m.torus(0.095, 0.014, x, 0.55, z, col, 12);
      m.cyl(0.04, 0.04, 0.008, x, 0.555, z, col, 8);
    }
    // stock pot
    m.cyl(0.13, 0.12, 0.16, 0.19, 0.57, -0.12, C.steelL, 12);
    m.cyl(0.115, 0.115, 0.006, 0.19, 0.727, -0.12, C.orange, 12);
    for (const sx of [-1, 1]) m.box(0.05, 0.022, 0.035, 0.19 + sx * 0.145, 0.67, -0.12, C.dark);
    // frying pan with an egg
    m.cyl(0.115, 0.095, 0.035, -0.19, 0.57, 0.2, C.darker, 12);
    m.cyl(0.055, 0.055, 0.006, -0.2, 0.602, 0.2, C.white, 8);
    m.sphere(0.02, -0.21, 0.602, 0.205, C.yellow, 1, 0.7, 1, 6);
    beam(m, -0.12, 0.6, 0.29, -0.03, 0.61, 0.385, 0.028, C.dark, 0.018);
    // oven front
    m.box(0.64, 0.3, 0.015, 0, 0.09, 0.39, C.steelD);
    m.box(0.42, 0.14, 0.008, 0, 0.18, 0.398, C.darker);
    cylX(m, 0.014, 0.56, 0, 0.43, 0.418, C.steelL, 6);
    for (const sx of [-1, 1]) m.box(0.02, 0.02, 0.03, sx * 0.24, 0.42, 0.4, C.frame);
    for (let i = 0; i < 5; i++) cylZ(m, 0.026, 0.03, -0.28 + i * 0.14, 0.485, 0.395, i === 4 ? C.red : C.dark, 8);
  });

const fridge: Fn = () =>
  model((m) => {
    m.box(0.7, 0.04, 0.62, 0, 0, -0.02, C.dark);
    m.rbox(0.78, 1.06, 0.7, 0, 0.03, -0.03, 0xaeb7c0, 0.04);
    m.box(0.72, 0.6, 0.03, 0, 0.07, 0.322, 0xd3d9de);
    m.box(0.72, 0.35, 0.03, 0, 0.7, 0.322, 0xd3d9de);
    m.box(0.035, 0.36, 0.04, -0.28, 0.25, 0.345, C.frame);
    m.box(0.035, 0.2, 0.04, -0.28, 0.76, 0.345, C.frame);
    m.box(0.11, 0.1, 0.006, 0.14, 0.86, 0.338, C.yellow, { rz: 0.08 });
    m.box(0.07, 0.05, 0.006, 0.2, 0.5, 0.338, C.red);
    m.box(0.06, 0.06, 0.006, 0.05, 0.42, 0.338, C.blue, { rz: -0.15 });
    m.box(0.6, 0.02, 0.22, 0, 1.09, -0.2, C.dark);
    // condenser grille on the back
    m.box(0.6, 0.66, 0.02, 0, 0.2, -0.385, C.dark);
    for (let i = 0; i < 4; i++) m.box(0.56, 0.02, 0.012, 0, 0.3 + i * 0.14, -0.398, C.frame);
  });

const kitchen_counter: Fn = () =>
  model((m) => {
    m.box(0.76, 0.06, 0.62, 0, 0, -0.02, C.dark);
    m.box(0.82, 0.4, 0.7, 0, 0.06, 0, C.steelD);
    for (const sx of [-1, 1]) {
      m.box(0.37, 0.32, 0.014, sx * 0.2, 0.1, 0.352, C.steel);
      m.box(0.022, 0.11, 0.024, sx * 0.06, 0.25, 0.366, C.frame);
    }
    m.rbox(0.86, 0.05, 0.76, 0, 0.45, 0, C.steelL, 0.015);
    m.box(0.86, 0.09, 0.04, 0, 0.5, -0.36, C.steel);
    // chopping board and veg
    m.box(0.38, 0.025, 0.27, -0.15, 0.5, 0.08, C.woodL, { ry: 0.12 });
    m.sphere(0.042, -0.26, 0.525, 0.13, C.red, 1, 0.9, 1, 8);
    m.blob(0.065, -0.1, 0.52, 0.02, C.greenL, 1, 0.85, 1, 1);
    rod(m, -0.2, 0.545, -0.02, -0.07, 0.54, 0.15, 0.022, C.orange, 6, 0.008);
    m.box(0.022, 0.006, 0.17, 0.12, 0.5, 0.12, C.steelL, { ry: -0.2 });
    m.box(0.028, 0.016, 0.08, 0.145, 0.5, 0.24, C.darker, { ry: -0.2 });
    // bowl + plates
    m.cyl(0.105, 0.065, 0.075, 0.24, 0.5, -0.16, C.cream, 10);
    m.cyl(0.09, 0.09, 0.006, 0.24, 0.572, -0.16, C.greenL, 10);
    m.cyl(0.085, 0.085, 0.05, 0.27, 0.5, 0.2, C.white, 10);
  });

const serving_counter: Fn = () =>
  model((m) => {
    m.box(1.78, 0.05, 0.5, 0, 0, -0.09, C.dark);
    m.box(1.84, 0.41, 0.56, 0, 0.05, -0.09, C.steelD);
    m.box(1.78, 0.27, 0.014, 0, 0.11, 0.192, C.blue);
    m.box(1.78, 0.035, 0.018, 0, 0.3, 0.192, C.beige);
    m.box(1.86, 0.045, 0.62, 0, 0.455, -0.09, C.steelL);
    // bain-marie wells
    const foods = [C.orange, 0xe2c36a, 0x6fa857];
    for (let i = 0; i < 3; i++) {
      const x = -0.58 + i * 0.58;
      m.box(0.5, 0.014, 0.36, x, 0.5, -0.07, C.frame);
      m.box(0.44, 0.012, 0.3, x, 0.508, -0.07, foods[i]);
    }
    m.blob(0.07, -0.66, 0.5, -0.1, 0xb65a30, 1.2, 0.45, 1, 0);
    m.blob(0.08, 0.02, 0.5, -0.05, 0xf0dc9a, 1.3, 0.5, 1, 1);
    m.blob(0.06, 0.52, 0.5, -0.1, 0x84bd68, 1.3, 0.5, 1, 0);
    rod(m, -0.5, 0.52, -0.05, -0.42, 0.7, -0.16, 0.009, C.steelL, 5);
    rod(m, 0.66, 0.52, -0.05, 0.74, 0.7, -0.16, 0.009, C.steelL, 5);
    // overshelf on posts
    for (const x of [-0.88, 0, 0.88]) m.box(0.035, 0.31, 0.035, x, 0.5, -0.34, C.frame);
    m.box(1.84, 0.028, 0.24, 0, 0.8, -0.27, C.steelL);
    m.cyl(0.075, 0.075, 0.07, -0.62, 0.828, -0.27, C.white, 10);
    for (let i = 0; i < 3; i++) m.cyl(0.032, 0.028, 0.07, 0.4 + i * 0.09, 0.828, -0.26, C.blue, 8);
    m.box(0.2, 0.08, 0.14, -0.1, 0.828, -0.27, C.beige);
    // tray rail
    for (const x of [-0.8, 0, 0.8]) m.box(0.03, 0.03, 0.22, x, 0.375, 0.3, C.frame);
    for (const z of [0.24, 0.32, 0.4]) cylX(m, 0.013, 1.84, 0, 0.415, z, C.steelL, 6);
    for (let i = 0; i < 4; i++) m.box(0.3, 0.014, 0.2, -0.68, 0.43 + i * 0.016, 0.32, i % 2 ? C.beige : C.orange, { ry: i * 0.03 });
    m.box(0.3, 0.014, 0.2, 0.42, 0.43, 0.32, C.orange);
    m.cyl(0.06, 0.045, 0.014, 0.4, 0.444, 0.32, C.white, 8);
  });

const table: Fn = () =>
  model((m) => {
    m.box(1.76, 0.035, 0.72, 0, 0.36, 0, C.frame);
    m.rbox(1.84, 0.05, 0.8, 0, 0.39, 0, C.steelL, 0.02);
    for (const sx of [-1, 1]) {
      const x = sx * 0.62;
      m.box(0.1, 0.35, 0.36, x, 0.02, 0, C.frame);
      m.box(0.16, 0.03, 0.72, x, 0, 0, C.frame);
      for (const sz of [-1, 1]) m.cyl(0.022, 0.022, 0.014, x, 0.03, sz * 0.31, C.darker, 6);
    }
    m.box(1.24, 0.05, 0.05, 0, 0.12, 0, C.frame);
    // meal trays
    const t1 = grp(m, -0.45, 0.44, 0.13, 0.12);
    t1.box(0.34, 0.016, 0.24, 0, 0, 0, C.orange);
    t1.cyl(0.075, 0.055, 0.016, -0.06, 0.016, 0, C.white, 8);
    t1.cyl(0.03, 0.026, 0.06, 0.11, 0.016, -0.05, C.blue, 6);
    m.blob(0.045, -0.5, 0.468, 0.12, 0xe2c36a, 1, 0.6, 1, 0);
    const t2 = grp(m, 0.42, 0.44, -0.14, -0.08);
    t2.box(0.34, 0.016, 0.24, 0, 0, 0, C.beige);
    t2.cyl(0.07, 0.045, 0.04, 0.05, 0.016, 0, C.white, 8);
    t2.cyl(0.03, 0.026, 0.06, -0.11, 0.016, 0.05, C.red, 6);
  });

const bench: Fn = () =>
  model((m) => {
    for (const sz of [-1, 1]) m.box(1.8, 0.035, 0.165, 0, 0.225, sz * 0.092, C.woodL);
    for (const sx of [-1, 1]) {
      const x = sx * 0.66;
      m.box(0.05, 0.2, 0.3, x, 0.025, 0, C.frame);
      m.box(0.08, 0.025, 0.4, x, 0, 0, C.frame);
      m.box(0.09, 0.03, 0.34, x, 0.196, 0, C.frame);
    }
    m.box(1.3, 0.04, 0.04, 0, 0.16, 0, C.frame);
  });

const bin: Fn = () =>
  model((m) => {
    m.cyl(0.21, 0.17, 0.44, 0, 0, 0, 0x5c8f72, 12);
    m.cyl(0.203, 0.198, 0.06, 0, 0.2, 0, 0x7fb093, 12);
    m.torus(0.2, 0.024, 0, 0.415, 0, C.darker, 12);
    m.cyl(0.18, 0.18, 0.01, 0, 0.436, 0, C.black, 12);
    m.blob(0.075, -0.06, 0.41, 0.03, C.white, 1, 0.8, 1, 0, { ry: 0.5 });
    m.cyl(0.03, 0.03, 0.09, 0.08, 0.42, -0.04, C.red, 6, { rz: 0.5, rx: 0.3 });
    m.box(0.09, 0.02, 0.04, 0.02, 0.45, 0.1, C.yellow, { ry: 0.6, rz: 0.2 });
  });

// ================================================================== LEISURE

const tv: Fn = () =>
  model((m) => {
    // low cabinet
    legs4(m, 0.36, 0.15, 0.04, 0.06, C.darker, 0, -0.12);
    m.rbox(0.84, 0.25, 0.42, 0, 0.035, -0.12, C.wood, 0.02);
    for (const sx of [-1, 1]) {
      m.box(0.38, 0.17, 0.012, sx * 0.2, 0.075, 0.09, C.woodD);
      m.box(0.03, 0.03, 0.02, sx * 0.05, 0.15, 0.1, C.gold);
    }
    m.box(0.26, 0.04, 0.17, -0.24, 0.285, -0.02, C.dark);
    m.box(0.03, 0.012, 0.006, -0.32, 0.3, 0.066, 0x62b06e);
    // flat screen
    m.box(0.32, 0.02, 0.16, 0.06, 0.285, -0.16, C.darker);
    m.box(0.07, 0.08, 0.04, 0.06, 0.3, -0.17, C.darker);
    m.box(0.84, 0.52, 0.05, 0, 0.365, -0.165, C.black);
    m.box(0.5, 0.3, 0.04, 0, 0.46, -0.2, C.dark);
    m.box(0.77, 0.45, 0.008, 0, 0.4, -0.138, C.screen, { glow: true });
    m.box(0.77, 0.13, 0.009, 0, 0.4, -0.1375, 0x86d095, { glow: true });
    m.box(0.3, 0.09, 0.01, -0.18, 0.5, -0.137, 0x9bdaa6, { glow: true });
    cylZ(m, 0.055, 0.01, 0.22, 0.73, -0.137, 0xfff0a6, 10, { glow: true });
    m.box(0.2, 0.04, 0.01, -0.16, 0.74, -0.137, 0xeaf4fb, { glow: true });
  });

const sofa: Fn = () =>
  model((m) => {
    const body = 0x57867f, light = 0x6f9f96, dark = 0x47706a;
    legs4(m, 0.8, 0.3, 0.05, 0.07, C.woodD);
    m.box(1.76, 0.1, 0.76, 0, 0.045, 0, dark);
    for (const sx of [-1, 1]) {
      m.rbox(0.77, 0.1, 0.56, sx * 0.385, 0.14, 0.1, light, 0.035);
      m.rbox(0.17, 0.33, 0.8, sx * 0.835, 0.07, 0, body, 0.05);
    }
    m.rbox(1.6, 0.46, 0.2, 0, 0.14, -0.3, body, 0.05);
    m.box(0.012, 0.3, 0.012, 0, 0.26, -0.196, dark); // seam
    m.box(0.13, 0.075, 0.008, -0.5, 0.06, 0.381, C.woodL); // patch
  });

const pool_table: Fn = () =>
  model((m) => {
    const felt = 0x3f9163, feltD = 0x347a52;
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) m.cyl(0.075, 0.05, 0.3, sx * 0.74, 0, sz * 0.28, C.woodD, 8);
    m.box(1.8, 0.16, 0.82, 0, 0.28, 0, C.woodD);
    m.box(1.62, 0.012, 0.64, 0, 0.44, 0, felt);
    for (const s of [-1, 1]) {
      m.box(1.82, 0.05, 0.1, 0, 0.44, s * 0.37, C.wood);
      m.box(0.1, 0.05, 0.64, s * 0.86, 0.44, 0, C.wood);
      m.box(1.58, 0.036, 0.022, 0, 0.44, s * 0.311, feltD);
      m.box(0.022, 0.036, 0.6, s * 0.801, 0.44, 0, feltD);
      for (const x of [-0.8, 0, 0.8]) m.cyl(0.05, 0.05, 0.008, x, 0.486, s * (x === 0 ? 0.335 : 0.315), C.black, 8);
    }
    const balls: [number, number, number][] = [
      [0.42, 0.04, C.white],
      [-0.34, 0, C.red],
      [-0.4, 0.034, C.yellow],
      [-0.4, -0.034, C.blue],
      [-0.46, 0.066, C.orange],
      [-0.46, 0, C.black],
      [-0.46, -0.066, C.purple],
      [0.08, -0.16, C.red],
      [-0.08, 0.2, C.yellow],
    ];
    for (const [x, z, col] of balls) m.sphere(0.03, x, 0.452, z, col, 1, 1, 1, 7);
    rod(m, 0.05, 0.505, 0.37, 0.8, 0.505, -0.05, 0.014, 0xdcbf90, 5, 0.007);
    m.box(0.045, 0.04, 0.045, -0.6, 0.49, 0.37, C.blue);
  });

const bookshelf: Fn = () =>
  model((m) => {
    for (const sx of [-1, 1]) m.box(0.05, 1.05, 0.42, sx * 0.4, 0, 0, C.wood);
    m.box(0.76, 0.08, 0.4, 0, 0, 0, C.woodD);
    m.box(0.9, 0.05, 0.46, 0, 1.04, 0, C.woodD);
    m.box(0.76, 0.96, 0.03, 0, 0.08, 0, C.woodD);
    for (const y of [0.4, 0.72]) m.box(0.76, 0.03, 0.4, 0, y, 0, C.woodL);
    const cols = [C.red, C.blue, C.yellow, C.green, C.purple, C.beige, C.orange, 0x3f6f7a, C.navy, C.redD];
    const r = rng(7);
    for (const y of [0.08, 0.43, 0.75])
      for (const sz of [-1, 1]) {
        let x = -0.365;
        let n = 0;
        while (x < 0.3) {
          const w = 0.055 + r() * 0.05;
          const h = 0.19 + r() * 0.08;
          const col = cols[Math.floor(r() * cols.length)];
          if (r() < 0.14 && x < 0.16 && n > 0) {
            // a little lying stack
            m.box(0.19, 0.045, 0.15, x + 0.1, y, sz * 0.105, col);
            m.box(0.17, 0.04, 0.14, x + 0.1, y + 0.045, sz * 0.105, cols[(n + 3) % cols.length]);
            x += 0.21;
          } else {
            const lean = x + w > 0.3 && r() < 0.6 ? -0.16 : 0;
            m.box(w, h, 0.15 + r() * 0.03, x + w / 2 + (lean ? 0.012 : 0), y, sz * 0.105, col, lean ? { rz: lean } : undefined);
            x += w + 0.006;
          }
          n++;
        }
      }
  });

const chair: Fn = () =>
  model((m) => {
    for (const sx of [-1, 1]) {
      rod(m, sx * 0.2, 0, 0.2, sx * 0.17, 0.22, 0.16, 0.016, C.frame, 6);
      rod(m, sx * 0.2, 0, -0.22, sx * 0.17, 0.22, -0.17, 0.016, C.frame, 6);
      rod(m, sx * 0.17, 0.22, -0.18, sx * 0.17, 0.6, -0.245, 0.015, C.frame, 6);
    }
    m.rbox(0.44, 0.045, 0.42, 0, 0.215, 0, C.blue, 0.02);
    m.rbox(0.44, 0.22, 0.04, 0, 0.42, -0.235, C.blue, 0.02, { rx: -0.16 });
    m.box(0.16, 0.03, 0.045, 0, 0.5, -0.24, C.blueD, { rx: -0.16 }); // grip slot
  });

const phone: Fn = () =>
  model((m) => {
    m.box(0.36, 0.03, 0.32, 0, 0, -0.14, C.dark);
    m.box(0.14, 0.5, 0.1, 0, 0.03, -0.18, C.frame);
    // shallow hood so the phone stays visible from above
    m.box(0.68, 0.56, 0.04, 0, 0.48, -0.3, C.blue);
    for (const sx of [-1, 1]) {
      m.box(0.04, 0.56, 0.16, sx * 0.34, 0.48, -0.22, C.blue);
      m.box(0.04, 0.2, 0.14, sx * 0.34, 0.48, -0.08, C.blue);
    }
    m.box(0.74, 0.05, 0.3, 0, 1.03, -0.17, C.blueD);
    m.box(0.64, 0.03, 0.3, 0, 0.48, -0.15, C.steel);
    m.box(0.4, 0.05, 0.008, 0, 1.03, -0.018, C.cream);
    // phone unit
    m.rbox(0.36, 0.42, 0.14, 0.06, 0.53, -0.2, C.steelD, 0.02);
    m.box(0.15, 0.15, 0.01, 0.13, 0.6, -0.128, C.darker);
    for (let i = 0; i < 9; i++) m.box(0.03, 0.03, 0.012, 0.09 + (i % 3) * 0.04, 0.615 + Math.floor(i / 3) * 0.042, -0.126, C.cream);
    m.box(0.16, 0.05, 0.01, 0.13, 0.84, -0.128, 0x9fd0a8);
    m.box(0.06, 0.016, 0.01, 0.13, 0.79, -0.128, C.black);
    // handset + cord
    m.box(0.05, 0.24, 0.045, -0.06, 0.65, -0.11, C.black);
    m.rbox(0.08, 0.075, 0.075, -0.06, 0.845, -0.105, C.black, 0.02);
    m.rbox(0.08, 0.075, 0.075, -0.06, 0.62, -0.105, C.black, 0.02);
    rod(m, -0.06, 0.62, -0.09, -0.14, 0.55, -0.05, 0.008, C.dark, 5);
    rod(m, -0.14, 0.55, -0.05, -0.02, 0.535, -0.13, 0.008, C.dark, 5);
  });

const weight_bench: Fn = () =>
  model((m) => {
    const pad = 0xa3453a;
    m.rbox(0.3, 0.07, 1.38, 0, 0.23, -0.02, pad, 0.03);
    m.box(0.08, 0.05, 1.3, 0, 0.18, -0.02, C.gun);
    m.box(0.06, 0.18, 0.06, 0, 0, 0.6, C.gun);
    m.box(0.42, 0.04, 0.07, 0, 0, 0.6, C.gun);
    m.box(0.06, 0.18, 0.06, 0, 0, -0.42, C.gun);
    // rack
    for (const sx of [-1, 1]) {
      m.box(0.05, 0.8, 0.05, sx * 0.3, 0, -0.42, C.gun);
      m.box(0.06, 0.04, 0.4, sx * 0.3, 0, -0.44, C.gun);
      m.box(0.055, 0.03, 0.09, sx * 0.3, 0.74, -0.39, C.frame);
      m.box(0.055, 0.07, 0.025, sx * 0.3, 0.74, -0.345, C.frame);
      cylX(m, 0.14, 0.035, sx * 0.355, 0.795, -0.39, C.darker, 12);
      cylX(m, 0.095, 0.03, sx * 0.388, 0.795, -0.39, C.blue, 10);
    }
    m.box(0.6, 0.04, 0.04, 0, 0.1, -0.42, C.gun);
    cylX(m, 0.017, 0.84, 0, 0.795, -0.39, C.steelL, 6);
    // dumbbell by the foot
    cylX(m, 0.014, 0.16, 0.26, 0.05, 0.8, C.steelL, 6);
    for (const sx of [-1, 1]) cylX(m, 0.05, 0.05, 0.26 + sx * 0.085, 0.05, 0.8, C.darker, 6);
  });

const punching_bag: Fn = () =>
  model((m) => {
    const bagC = 0xa8473c, band = 0x7d342c;
    for (const sx of [-1, 1]) m.box(0.07, 0.04, 0.78, sx * 0.3, 0, -0.02, C.gun);
    m.box(0.67, 0.04, 0.08, 0, 0, -0.36, C.gun);
    m.box(0.08, 1.32, 0.08, 0, 0.04, -0.36, C.frame);
    m.box(0.07, 0.07, 0.46, 0, 1.29, -0.15, C.frame);
    beam(m, 0, 1.0, -0.33, 0, 1.3, -0.08, 0.04, C.gun);
    for (const sx of [-1, 1]) beam(m, sx * 0.28, 0.04, -0.36, 0, 0.4, -0.36, 0.04, C.gun);
    rod(m, 0, 1.3, 0.04, 0, 1.1, 0.04, 0.012, C.steelL, 5);
    m.cyl(0.07, 0.15, 0.05, 0, 1.06, 0.04, band, 12);
    m.cyl(0.15, 0.15, 0.6, 0, 0.46, 0.04, bagC, 12);
    m.sphere(0.15, 0, 0.395, 0.04, bagC, 1, 0.45, 1, 12);
    m.cyl(0.154, 0.154, 0.045, 0, 0.92, 0.04, band, 12);
    m.cyl(0.154, 0.154, 0.045, 0, 0.56, 0.04, band, 12);
    m.cyl(0.155, 0.155, 0.035, 0, 0.75, 0.04, C.beige, 12);
  });

const basketball_hoop: Fn = () =>
  model((m) => {
    const hoop = 0xd8562e;
    m.rbox(0.54, 0.13, 0.3, 0, 0, -0.3, C.dark, 0.03);
    m.box(0.542, 0.04, 0.302, 0, 0.05, -0.3, C.yellow);
    m.box(0.08, 1.5, 0.08, 0, 0.12, -0.36, C.frame);
    beam(m, 0, 1.56, -0.36, 0, 1.66, -0.12, 0.06, C.frame);
    beam(m, 0, 1.3, -0.36, 0, 1.46, -0.12, 0.05, C.frame);
    // backboard
    m.box(0.82, 0.54, 0.035, 0, 1.36, -0.105, C.white);
    for (const y of [1.36, 1.87]) m.box(0.82, 0.03, 0.008, 0, y, -0.085, hoop);
    for (const sx of [-1, 1]) m.box(0.03, 0.54, 0.008, sx * 0.395, 1.36, -0.085, hoop);
    m.box(0.3, 0.022, 0.008, 0, 1.47, -0.085, hoop);
    m.box(0.3, 0.022, 0.008, 0, 1.68, -0.085, hoop);
    for (const sx of [-1, 1]) m.box(0.022, 0.23, 0.008, sx * 0.14, 1.47, -0.085, hoop);
    // ring and net
    m.box(0.07, 0.03, 0.08, 0, 1.445, -0.05, hoop);
    m.torus(0.13, 0.014, 0, 1.446, 0.11, hoop, 14);
    for (let i = 0; i < 8; i++) {
      const a0 = (i / 8) * Math.PI * 2, a1 = ((i + 1) / 8) * Math.PI * 2;
      beam(m, Math.cos(a0) * 0.125, 1.45, 0.11 + Math.sin(a0) * 0.125, Math.cos(a1) * 0.075, 1.27, 0.11 + Math.sin(a1) * 0.075, 0.012, C.cream);
      beam(m, Math.cos(a1) * 0.125, 1.45, 0.11 + Math.sin(a1) * 0.125, Math.cos(a0) * 0.075, 1.27, 0.11 + Math.sin(a0) * 0.075, 0.012, C.cream);
    }
  });

const pew: Fn = () =>
  model((m) => {
    for (const sx of [-1, 1]) {
      m.rbox(0.07, 0.68, 0.6, sx * 0.885, 0, -0.03, C.woodD, 0.03);
      m.box(0.09, 0.04, 0.2, sx * 0.885, 0.4, 0.17, C.woodD); // arm cap
    }
    m.box(1.72, 0.04, 0.42, 0, 0.22, 0.04, C.wood);
    m.box(1.72, 0.07, 0.04, 0, 0.15, -0.12, C.woodD);
    m.box(1.72, 0.07, 0.04, 0, 0.15, 0.2, C.woodD);
    m.box(1.72, 0.46, 0.045, 0, 0.25, -0.255, C.wood, { rx: -0.12 });
    m.box(1.76, 0.045, 0.08, 0, 0.69, -0.285, C.woodD);
    m.box(1.6, 0.02, 0.07, 0, 0.42, -0.325, C.woodD);
    m.box(0.12, 0.14, 0.03, -0.45, 0.44, -0.32, C.redD);
    m.box(0.12, 0.14, 0.03, 0.4, 0.44, -0.32, C.navy);
    m.box(0.14, 0.028, 0.19, 0, 0.26, 0.05, C.redD, { ry: 0.15 });
  });

const altar: Fn = () =>
  model((m) => {
    m.box(1.84, 0.06, 0.84, 0, 0, 0, C.woodD);
    m.box(1.5, 0.44, 0.56, 0, 0.06, 0, C.wood);
    for (const sx of [-1, 1]) m.box(0.09, 0.44, 0.6, sx * 0.72, 0.06, 0, C.woodD);
    for (const sz of [-1, 1]) for (const sx of [-1, 1]) m.box(0.3, 0.3, 0.012, sx * 0.5, 0.13, sz * 0.282, C.woodL);
    m.box(1.64, 0.05, 0.68, 0, 0.5, 0, C.woodD);
    // cloth runner
    m.box(0.62, 0.012, 0.7, 0, 0.55, 0, C.cream);
    for (const sz of [-1, 1]) {
      m.box(0.62, 0.34, 0.012, 0, 0.222, sz * 0.347, C.cream);
      m.box(0.62, 0.09, 0.016, 0, 0.28, sz * 0.347, C.purple);
      m.box(0.62, 0.02, 0.018, 0, 0.245, sz * 0.347, C.gold);
    }
    // candles
    for (const sx of [-1, 1]) {
      const x = sx * 0.58;
      m.cyl(0.05, 0.065, 0.025, x, 0.55, 0, C.gold, 8);
      m.cyl(0.016, 0.022, 0.1, x, 0.575, 0, C.gold, 6);
      m.cyl(0.04, 0.02, 0.025, x, 0.675, 0, C.gold, 8);
      m.cyl(0.024, 0.024, 0.16, x, 0.7, 0, C.cream, 8);
      m.cone(0.02, 0.06, x, 0.862, 0, 0xffd27a, 6, { glow: true });
    }
    // open book on a rest, chalice
    m.box(0.36, 0.03, 0.24, 0, 0.562, 0.04, C.redD, { rx: 0.12 });
    m.box(0.16, 0.02, 0.21, -0.083, 0.588, 0.04, C.white, { rx: 0.12, rz: 0.08 });
    m.box(0.16, 0.02, 0.21, 0.083, 0.588, 0.04, C.white, { rx: 0.12, rz: -0.08 });
    m.cyl(0.035, 0.04, 0.012, 0.33, 0.55, -0.12, C.gold, 8);
    m.cyl(0.01, 0.01, 0.06, 0.33, 0.562, -0.12, C.gold, 5);
    m.cyl(0.045, 0.015, 0.06, 0.33, 0.62, -0.12, C.gold, 8);
    // flowers
    m.cyl(0.035, 0.045, 0.09, -0.33, 0.55, -0.12, C.blue, 8);
    m.blob(0.06, -0.33, 0.64, -0.12, C.green, 1, 0.8, 1, 0);
    m.blob(0.03, -0.35, 0.72, -0.1, C.white, 1, 1, 1, 0);
    m.blob(0.03, -0.3, 0.71, -0.14, C.pink, 1, 1, 1, 0);
  });

const visit_table: Fn = () =>
  model((m) => {
    m.box(0.09, 0.035, 2.3, 0, 0, 0, C.frame);
    m.box(0.42, 0.03, 0.42, 0, 0, 0, C.frame);
    m.box(0.14, 0.36, 0.14, 0, 0.03, 0, C.frame);
    m.box(0.74, 0.03, 0.68, 0, 0.365, 0, C.frame);
    m.rbox(0.82, 0.05, 0.76, 0, 0.39, 0, C.woodL, 0.02);
    // low divider with a booth number
    m.box(0.82, 0.15, 0.03, 0, 0.44, 0, C.blue);
    m.box(0.84, 0.02, 0.05, 0, 0.59, 0, C.blueD);
    for (const sz of [-1, 1]) {
      m.box(0.12, 0.07, 0.006, 0, 0.48, sz * 0.017, C.cream);
      // bolted stools
      m.cyl(0.12, 0.13, 0.02, 0, 0.035, sz, C.frame, 10);
      m.cyl(0.04, 0.04, 0.19, 0, 0.035, sz, C.frame, 8);
      m.cyl(0.175, 0.16, 0.045, 0, 0.215, sz, C.blue, 12);
    }
  });

// ================================================================== MEDICAL

const medical_bed: Fn = () =>
  model((m) => {
    const fr = 0xe1e5e6, sheet = 0xf2f2ee, tealB = 0x5fa8a0;
    for (const sx of [-1, 1])
      for (const sz of [-1, 1]) {
        cylX(m, 0.05, 0.04, sx * 0.34, 0.05, sz * 0.8, C.darker, 8);
        m.box(0.04, 0.17, 0.04, sx * 0.34, 0.06, sz * 0.8, C.steelD);
      }
    m.box(0.8, 0.05, 1.78, 0, 0.2, 0, fr);
    m.box(0.3, 0.03, 1.4, 0, 0.17, 0, C.steelD);
    // mattress: flat part + raised head section
    m.box(0.72, 0.13, 1.23, 0, 0.25, 0.255, sheet);
    m.rbox(0.72, 0.13, 0.5, 0, 0.301, -0.618, sheet, 0.04, { rx: 0.2 });
    m.box(0.5, 0.12, 0.04, 0, 0.25, -0.8, C.steelD);
    m.rbox(0.44, 0.06, 0.24, 0, 0.44, -0.655, 0xdcecec, 0.025, { rx: 0.2 });
    m.rbox(0.745, 0.135, 0.8, 0, 0.251, 0.45, tealB, 0.04);
    m.box(0.752, 0.125, 0.1, 0, 0.262, 0.1, 0xdcecec);
    // head and foot boards
    m.box(0.82, 0.52, 0.045, 0, 0.24, -0.895, fr);
    m.box(0.82, 0.32, 0.045, 0, 0.24, 0.895, fr);
    m.box(0.17, 0.21, 0.012, 0.16, 0.3, 0.922, C.woodL);
    m.box(0.14, 0.16, 0.006, 0.16, 0.31, 0.93, C.white);
    m.box(0.07, 0.025, 0.012, 0.16, 0.49, 0.93, C.frame);
    // side rails
    for (const sx of [-1, 1]) {
      m.box(0.025, 0.025, 0.62, sx * 0.39, 0.53, -0.2, C.steel);
      for (const z of [-0.49, -0.2, 0.09]) m.box(0.02, 0.29, 0.02, sx * 0.39, 0.25, z, C.steel);
    }
    // IV stand
    m.cyl(0.015, 0.015, 1.12, 0.385, 0.25, -0.845, C.steelL, 6);
    m.box(0.18, 0.016, 0.016, 0.33, 1.36, -0.845, C.steelL);
    m.rbox(0.09, 0.15, 0.04, 0.26, 1.2, -0.845, 0xbfe3ea, 0.015);
    m.box(0.07, 0.05, 0.042, 0.26, 1.21, -0.845, 0x8fd0dc);
    rod(m, 0.26, 1.2, -0.845, 0.3, 0.56, -0.5, 0.006, 0xd9e6ea, 4);
  });

const medicine_cabinet: Fn = () =>
  model((m) => {
    const door = 0xe1e6e5, cross = 0x3f9a6a;
    m.box(0.72, 0.04, 0.4, 0, 0, -0.03, 0x9aa3ab);
    m.rbox(0.8, 1.0, 0.46, 0, 0.035, -0.03, C.white, 0.03);
    for (const sx of [-1, 1]) {
      m.box(0.355, 0.46, 0.014, sx * 0.187, 0.52, 0.2, door);
      m.box(0.02, 0.11, 0.022, sx * 0.04, 0.56, 0.212, C.steelD);
    }
    m.box(0.22, 0.075, 0.01, 0, 0.782, 0.21, cross);
    m.box(0.075, 0.22, 0.01, 0, 0.71, 0.21, cross);
    for (const y of [0.09, 0.29]) {
      m.box(0.73, 0.18, 0.014, 0, y, 0.2, door);
      m.box(0.22, 0.022, 0.022, 0, y + 0.11, 0.212, C.steelD);
    }
    // supplies on top
    m.cyl(0.04, 0.04, 0.1, -0.24, 1.035, -0.06, 0x8a5a3a, 8);
    m.cyl(0.028, 0.028, 0.03, -0.24, 1.135, -0.06, C.white, 6);
    m.cyl(0.032, 0.032, 0.075, -0.13, 1.035, 0.02, C.white, 8);
    m.cyl(0.034, 0.034, 0.02, -0.13, 1.11, 0.02, C.blue, 8);
    m.rbox(0.26, 0.11, 0.17, 0.16, 1.035, -0.03, cross, 0.02);
    m.box(0.1, 0.03, 0.006, 0.16, 1.075, 0.056, C.white);
    m.box(0.03, 0.09, 0.006, 0.16, 1.045, 0.056, C.white);
  });

// ================================================================== WORK & STUDY

const workshop_saw: Fn = () =>
  model((m) => {
    const body = 0x4e7d6a, bodyD = 0x416958;
    legs4(m, 0.84, 0.32, 0.4, 0.06, C.frame);
    m.box(0.86, 0.04, 0.56, -0.32, 0, 0, C.dark);
    m.box(0.9, 0.36, 0.62, -0.32, 0.04, 0, body);
    m.box(0.8, 0.025, 0.6, 0.48, 0.12, 0, C.frame);
    m.box(0.3, 0.16, 0.3, 0.5, 0.145, -0.05, C.card);
    m.cyl(0.08, 0.08, 0.14, 0.24, 0.145, 0.12, C.steelD, 8);
    m.cyl(0.082, 0.082, 0.02, 0.24, 0.27, 0.12, C.red, 8);
    // switchgear on the front
    m.box(0.14, 0.12, 0.03, -0.58, 0.2, 0.31, C.darker);
    cylZ(m, 0.022, 0.02, -0.61, 0.26, 0.33, 0x62b06e, 6);
    cylZ(m, 0.022, 0.02, -0.55, 0.26, 0.33, C.red, 6);
    m.box(0.13, 0.13, 0.008, -0.22, 0.17, 0.312, C.yellow);
    cylZ(m, 0.04, 0.035, -0.22, 0.235, 0.325, C.red, 8);
    m.box(0.3, 0.012, 0.008, -0.32, 0.36, 0.312, bodyD);
    cylX(m, 0.07, 0.06, -0.79, 0.2, -0.1, C.dark, 8);
    // table
    m.box(1.84, 0.045, 0.8, 0, 0.4, 0, C.steelL);
    m.box(0.52, 0.004, 0.035, -0.32, 0.445, 0.06, C.darker);
    // blade, riving knife and guard
    cylZ(m, 0.23, 0.014, -0.32, 0.45, 0.06, 0xe9edf0, 16);
    cylZ(m, 0.19, 0.018, -0.32, 0.45, 0.06, 0xc3cbd2, 16);
    cylZ(m, 0.06, 0.026, -0.32, 0.45, 0.06, C.gun, 8);
    m.box(0.035, 0.27, 0.014, -0.585, 0.445, 0.06, C.frame);
    m.box(0.2, 0.03, 0.014, -0.5, 0.7, 0.06, C.frame);
    m.rbox(0.16, 0.06, 0.07, -0.4, 0.665, 0.06, 0xe0902e, 0.02);
    // rip fence
    m.box(1.72, 0.075, 0.045, 0, 0.445, -0.24, C.steel);
    m.box(0.07, 0.05, 0.12, 0.88, 0.445, -0.22, C.red);
    // timber
    m.box(0.95, 0.03, 0.15, 0.32, 0.445, -0.13, C.woodL);
    m.box(0.5, 0.03, 0.05, 0.2, 0.445, 0.13, C.woodL);
    for (let i = 0; i < 3; i++) m.box(0.62, 0.03, 0.15, 0.54, 0.445 + i * 0.03, 0.27, i === 1 ? C.wood : C.woodL, { ry: (i - 1) * 0.06 });
    m.blob(0.12, -0.25, -0.03, 0.34, 0xd9bb8c, 1.2, 0.4, 0.6, 0);
  });

const workshop_press: Fn = () =>
  model((m) => {
    const body = 0x4a6078, bodyL = 0x5a7390;
    m.rbox(0.82, 0.34, 0.74, 0, 0, 0, body, 0.03);
    m.box(0.46, 0.04, 0.36, 0, 0.34, -0.08, C.steelD);
    for (const sx of [-1, 1]) {
      m.cyl(0.045, 0.045, 0.52, sx * 0.31, 0.34, -0.08, C.steelL, 8);
      m.cyl(0.065, 0.065, 0.05, sx * 0.31, 0.34, -0.08, C.gun, 8);
    }
    m.rbox(0.82, 0.22, 0.42, 0, 0.84, -0.08, bodyL, 0.03);
    m.cyl(0.11, 0.11, 0.1, 0, 1.06, -0.08, C.dark, 10);
    m.cyl(0.07, 0.07, 0.28, 0, 0.58, -0.08, C.steelL, 10);
    m.box(0.38, 0.06, 0.3, 0, 0.52, -0.08, C.steel);
    // plate being stamped
    m.box(0.27, 0.012, 0.14, 0, 0.38, -0.08, C.yellow);
    for (const x of [-0.08, -0.03, 0.03, 0.08]) m.box(0.028, 0.004, 0.07, x, 0.392, -0.08, C.navy);
    // hazard strip, gauge, controls
    m.box(0.74, 0.06, 0.008, 0, 0.855, 0.132, C.yellow);
    for (let i = 0; i < 6; i++) m.box(0.045, 0.06, 0.01, -0.32 + i * 0.128, 0.855, 0.133, C.darker, { rz: 0.5 });
    cylZ(m, 0.055, 0.02, 0.22, 0.99, 0.135, C.white, 10);
    m.box(0.012, 0.04, 0.006, 0.22, 0.99, 0.147, C.red, { rz: 0.6 });
    m.box(0.13, 0.17, 0.09, -0.31, 0.5, 0.0, C.darker);
    cylZ(m, 0.024, 0.02, -0.34, 0.62, 0.05, 0x62b06e, 6);
    cylZ(m, 0.024, 0.02, -0.28, 0.62, 0.05, C.red, 6);
    // finished plates and blanks
    for (let i = 0; i < 6; i++) m.box(0.14, 0.013, 0.27, 0.28, 0.34 + i * 0.013, 0.2, i === 5 ? 0xf0cb55 : C.yellow, { ry: (i % 3 - 1) * 0.07 });
    for (let i = 0; i < 4; i++) m.box(0.14, 0.013, 0.27, -0.28, 0.34 + i * 0.013, 0.2, C.steelL, { ry: (i % 2) * 0.06 });
    m.box(0.27, 0.013, 0.14, 0, 0.34, 0.24, C.yellow, { ry: 0.2 });
  });

const school_desk: Fn = () =>
  model((m) => {
    // chair (sitter at z = -0.15, facing +Z)
    for (const sx of [-1, 1]) {
      m.box(0.026, 0.22, 0.026, sx * 0.15, 0, -0.02, C.frame);
      m.box(0.026, 0.56, 0.026, sx * 0.15, 0, -0.33, C.frame);
    }
    m.rbox(0.36, 0.04, 0.36, 0, 0.22, -0.17, C.blue, 0.015);
    m.rbox(0.36, 0.15, 0.035, 0, 0.43, -0.345, C.blue, 0.015);
    // desk
    m.box(0.76, 0.035, 0.38, 0, 0.425, 0.22, C.woodL);
    m.box(0.62, 0.02, 0.3, 0, 0.345, 0.22, C.frame);
    m.box(0.62, 0.08, 0.02, 0, 0.345, 0.37, C.frame);
    for (const sx of [-1, 1]) {
      m.box(0.03, 0.425, 0.03, sx * 0.34, 0, 0.36, C.frame);
      m.box(0.03, 0.425, 0.03, sx * 0.34, 0, 0.08, C.frame);
      m.box(0.03, 0.03, 0.4, sx * 0.34, 0, 0.22, C.frame);
      m.box(0.03, 0.08, 0.3, sx * 0.34, 0.345, 0.22, C.frame);
    }
    m.box(0.17, 0.014, 0.22, -0.1, 0.46, 0.2, C.white, { ry: 0.15 });
    m.box(0.014, 0.014, 0.15, 0.09, 0.46, 0.22, C.yellow, { ry: -0.4 });
    m.sphere(0.034, 0.26, 0.46, 0.3, C.red, 1, 0.9, 1, 7);
  });

const blackboard: Fn = () =>
  model((m) => {
    const board = 0x2f5d4a, chalk = 0xe4ece4;
    for (const sx of [-1, 1]) {
      m.box(0.07, 0.04, 0.72, sx * 0.8, 0, 0, C.gun);
      m.box(0.055, 1.2, 0.055, sx * 0.8, 0.04, 0, C.woodD);
      beam(m, sx * 0.8, 0.04, 0.3, sx * 0.8, 0.42, 0.02, 0.03, C.gun);
      beam(m, sx * 0.8, 0.04, -0.3, sx * 0.8, 0.42, -0.02, 0.03, C.gun);
    }
    m.box(1.6, 0.78, 0.03, 0, 0.44, 0, C.woodD);
    m.box(1.5, 0.68, 0.012, 0, 0.49, 0.017, board);
    m.box(1.62, 0.045, 0.05, 0, 0.44, 0.004, C.wood);
    m.box(1.62, 0.045, 0.05, 0, 1.19, 0.004, C.wood);
    for (const sx of [-1, 1]) m.box(0.045, 0.7, 0.05, sx * 0.765, 0.485, 0.004, C.wood);
    for (const y of [0.62, 0.98]) m.box(1.5, 0.05, 0.014, 0, y, -0.02, C.wood); // back battens
    // chalk tray
    m.box(1.5, 0.02, 0.09, 0, 0.44, 0.065, C.wood);
    m.box(1.5, 0.03, 0.012, 0, 0.455, 0.105, C.wood);
    m.box(0.07, 0.016, 0.016, -0.42, 0.46, 0.07, C.white, { ry: 0.2 });
    m.box(0.06, 0.016, 0.016, -0.3, 0.46, 0.065, C.yellow, { ry: -0.3 });
    m.box(0.11, 0.035, 0.055, 0.34, 0.46, 0.065, C.dark);
    // chalk marks
    const z = 0.0245;
    m.box(0.52, 0.02, 0.004, -0.36, 1.06, z, chalk);
    m.box(0.44, 0.014, 0.004, -0.4, 0.96, z, chalk);
    m.box(0.56, 0.014, 0.004, -0.34, 0.89, z, chalk);
    m.box(0.36, 0.014, 0.004, -0.44, 0.82, z, chalk);
    m.box(0.2, 0.014, 0.004, -0.52, 0.68, z, 0xf0d870);
    const tri: [number, number][] = [[0.14, 0.64], [0.58, 0.64], [0.42, 0.98]];
    for (let i = 0; i < 3; i++) {
      const [x1, y1] = tri[i], [x2, y2] = tri[(i + 1) % 3];
      beam(m, x1, y1, z, x2, y2, z, 0.016, chalk, 0.004);
    }
    m.box(0.05, 0.05, 0.004, 0.2, 0.655, z, 0xf0d870);
  });

/** Slatted wooden crate of side `s` sitting at (x, y, z), turned by ry. */
function crate(m: MB, x: number, y: number, z: number, s: number, ry: number, tone = 0) {
  const body = tone ? 0xb48a5a : 0xc0966a, slat = tone ? 0x94683f : 0x9f7449;
  const g = grp(m, x, y, z, ry);
  const h = s / 2, t = 0.045, e = 0.008;
  g.box(s, s, s, 0, 0, 0, body);
  for (const sx of [-1, 1]) {
    for (const sz of [-1, 1]) g.box(t, s + e, t, sx * (h - t / 2 + e), 0, sz * (h - t / 2 + e), slat);
    g.box(t, t, s - t, sx * (h - t / 2 + e), 0, 0, slat);
    g.box(t, t, s - t, sx * (h - t / 2 + e), s - t + e, 0, slat);
    g.box(e, t, s - t, sx * (h + e / 2), s / 2 - t / 2, 0, slat);
  }
  for (const sz of [-1, 1]) {
    g.box(s - t, t, t, 0, 0, sz * (h - t / 2 + e), slat);
    g.box(s - t, t, t, 0, s - t + e, sz * (h - t / 2 + e), slat);
    const L = Math.hypot(s - t * 2, s - t * 2);
    g.box(t, L, e, 0, s / 2 - L / 2, sz * (h + e / 2), slat, { rz: sz * (Math.PI / 4) });
  }
}

const crates: Fn = () =>
  model((m) => {
    crate(m, -0.17, 0, -0.15, 0.44, 0.04);
    crate(m, 0.21, 0, 0.2, 0.36, -0.1, 1);
    crate(m, -0.14, 0.448, -0.15, 0.3, 0.4, 1);
    crate(m, -0.25, 0, 0.26, 0.22, 0.2);
    // sack
    m.blob(0.14, 0.2, 0.33, 0.2, 0xcbb894, 1, 0.75, 0.85, 1, { ry: 0.4 });
    m.cyl(0.03, 0.045, 0.04, 0.2, 0.52, 0.2, 0xb9a47e, 6);
    m.box(0.09, 0.05, 0.006, 0.2, 0.12, 0.385, C.darker, { ry: -0.1 });
  });

const shelving: Fn = () =>
  model((m) => {
    const up = 0x4a6078;
    for (const sx of [-1, 1]) {
      for (const sz of [-1, 1]) m.box(0.05, 1.16, 0.05, sx * 0.88, 0, sz * 0.2, up);
      for (const y of [0.3, 0.7, 1.08]) m.box(0.03, 0.03, 0.4, sx * 0.88, y, 0, up);
      beam(m, sx * 0.88, 0.32, -0.19, sx * 0.88, 0.7, 0.19, 0.025, up);
      beam(m, sx * 0.88, 0.72, 0.19, sx * 0.88, 1.08, -0.19, 0.025, up);
    }
    const levels = [0.12, 0.5, 0.88];
    for (const y of levels) {
      for (const sz of [-1, 1]) m.box(1.74, 0.055, 0.03, 0, y, sz * 0.215, C.orange);
      m.box(1.72, 0.02, 0.42, 0, y + 0.035, 0, C.woodL);
    }
    const box = (x: number, y: number, w: number, h: number, d: number, col = C.card, ry = 0) => {
      m.box(w, h, d, x, y, 0, col, { ry });
      m.box(w * 0.22, 0.004, d, x, y + h, 0, C.cardL, { ry });
    };
    const [a, b, c] = levels.map((y) => y + 0.055);
    box(-0.6, a, 0.42, 0.26, 0.34);
    box(-0.14, a, 0.36, 0.2, 0.32, 0xb89462, 0.06);
    m.cyl(0.13, 0.13, 0.28, 0.3, a, 0, C.blue, 10);
    m.cyl(0.135, 0.135, 0.02, 0.3, a + 0.2, 0, C.blueD, 10);
    m.cyl(0.13, 0.13, 0.28, 0.6, a, 0.02, C.blue, 10);
    m.cyl(0.135, 0.135, 0.02, 0.6, a + 0.2, 0.02, C.blueD, 10);
    box(-0.66, b, 0.28, 0.2, 0.3, 0xb89462);
    box(-0.34, b, 0.3, 0.28, 0.32, C.card, -0.05);
    m.rbox(0.32, 0.14, 0.2, 0.08, b, 0.02, C.red, 0.02);
    m.box(0.12, 0.03, 0.03, 0.08, b + 0.14, 0.02, C.darker);
    box(0.55, b, 0.4, 0.16, 0.34);
    box(0.52, b + 0.165, 0.3, 0.12, 0.28, 0xb89462, 0.1);
    box(-0.52, c, 0.5, 0.18, 0.34, C.card, 0.03);
    for (let i = 0; i < 3; i++) {
      m.cyl(0.065, 0.065, 0.14, -0.08 + i * 0.16, c, i === 1 ? 0.06 : -0.03, C.steelL, 8);
      m.cyl(0.067, 0.067, 0.02, -0.08 + i * 0.16, c + 0.14, i === 1 ? 0.06 : -0.03, [C.teal, C.yellow, C.red][i], 8);
    }
    box(0.62, c, 0.3, 0.22, 0.3, 0xb89462, -0.08);
  });

// ================================================================== SECURITY

const cctv: Fn = () =>
  model((m) => {
    m.cyl(0.12, 0.14, 0.04, 0, 0, 0, C.frame, 10);
    m.cyl(0.05, 0.06, 0.1, 0, 0.04, 0, C.frame, 8);
    m.cyl(0.03, 0.04, 1.4, 0, 0.04, 0, C.steelD, 8);
    m.box(0.11, 0.15, 0.07, 0, 0.86, -0.05, C.steelL);
    m.box(0.02, 0.05, 0.006, 0, 0.93, -0.012, C.dark);
    m.cyl(0.045, 0.045, 0.03, 0, 1.44, 0, C.frame, 8);
    beam(m, 0, 1.42, 0, 0, 1.48, 0.12, 0.035, C.frame);
    // housing pitched down toward +Z
    const t = 0.38;
    const ny = Math.cos(t), nz = Math.sin(t); // housing "up"
    const ay = -Math.sin(t), az = Math.cos(t); // housing "forward"
    const cy = 1.46, cz = 0.17;
    m.rbox(0.12, 0.105, 0.28, 0, cy - 0.0525, cz, 0xe6e8e6, 0.02, { rx: t });
    m.box(0.14, 0.016, 0.34, 0, cy + ny * 0.06 + ay * 0.03 - 0.008, cz + nz * 0.06 + az * 0.03, C.steelL, { rx: t });
    m.cyl(0.038, 0.038, 0.03, 0, cy + ay * 0.145 - 0.015, cz + az * 0.145, C.black, 8, { rx: HP + t });
    m.box(0.02, 0.02, 0.012, 0.038, cy + ay * 0.14 + ny * 0.03 - 0.01, cz + az * 0.14 + nz * 0.03, 0xff4a3a, { rx: t, glow: true });
    m.box(0.02, 0.008, 0.012, 0.038, cy + ay * 0.14 + ny * 0.02 - 0.004, cz + az * 0.14 + nz * 0.02, C.darker, { rx: t });
  });

const cctv_monitor: Fn = () =>
  model((m) => {
    const body = 0x47525f, top = 0x343c46;
    m.box(1.8, 0.04, 0.44, 0, 0, -0.2, C.darker);
    m.box(1.84, 0.33, 0.5, 0, 0.04, -0.2, body);
    m.box(1.86, 0.035, 0.56, 0, 0.37, -0.18, top);
    m.box(1.84, 0.5, 0.11, 0, 0.405, -0.395, body);
    m.box(1.86, 0.03, 0.14, 0, 0.905, -0.385, top);
    // front panels + back vents
    for (const x of [-0.6, 0, 0.6]) m.box(0.54, 0.25, 0.01, x, 0.08, 0.05, 0x525e6c);
    for (const sx of [-1, 1]) for (let i = 0; i < 3; i++) m.box(0.4, 0.025, 0.008, sx * 0.5, 0.14 + i * 0.07, -0.452, C.darker);
    // monitors
    const scr = [0x7fc4d8, 0x8fd0b0, 0x86b4e2, 0x9fc8d0];
    for (let i = 0; i < 4; i++) {
      const x = -0.675 + i * 0.45;
      m.box(0.41, 0.31, 0.04, x, 0.51, -0.325, C.black);
      m.box(0.355, 0.25, 0.008, x, 0.54, -0.303, scr[i], { glow: true });
      m.box(0.355, 0.07, 0.009, x, 0.54, -0.3025, i % 2 ? 0x6fa8c4 : 0x74b596, { glow: true });
      m.box(0.09, 0.11, 0.01, x + (i % 2 ? 0.07 : -0.06), 0.6, -0.302, i % 2 ? 0x5f93b0 : 0x5f9c80, { glow: true });
      m.box(0.03, 0.03, 0.01, x + 0.14, 0.745, -0.302, 0xff5a48, { glow: true });
    }
    // desk controls
    m.box(0.36, 0.016, 0.13, 0, 0.405, -0.06, C.steelL);
    m.box(0.3, 0.004, 0.09, 0, 0.421, -0.06, C.frame);
    const btn = [C.red, 0x62b06e, C.yellow, C.blue, C.cream, C.orange];
    for (let i = 0; i < 6; i++) m.box(0.045, 0.014, 0.045, -0.72 + (i % 3) * 0.07, 0.405, -0.1 + Math.floor(i / 3) * 0.07, btn[i]);
    m.box(0.24, 0.01, 0.17, -0.65, 0.405, -0.065, C.darker);
    m.cyl(0.05, 0.06, 0.02, 0.62, 0.405, -0.06, C.darker, 8);
    rod(m, 0.62, 0.42, -0.06, 0.635, 0.5, -0.04, 0.012, C.steelD, 5);
    m.sphere(0.026, 0.636, 0.485, -0.038, C.red, 1, 1, 1, 6);
    m.cyl(0.035, 0.03, 0.07, 0.36, 0.405, -0.02, C.cream, 8);
    // operator stool in the front strip
    m.cyl(0.13, 0.14, 0.02, 0, 0, 0.3, C.darker, 10);
    m.cyl(0.03, 0.03, 0.2, 0, 0.02, 0.3, C.steel, 6);
    m.cyl(0.15, 0.14, 0.045, 0, 0.215, 0.3, C.slateD, 12);
  });

const metal_detector: Fn = () =>
  model((m) => {
    const shell = 0xd5dadd;
    m.box(0.68, 0.012, 0.6, 0, 0, 0, C.gun);
    for (const sz of [-1, 1]) m.box(0.68, 0.014, 0.035, 0, 0, sz * 0.28, C.yellow);
    for (const sx of [-1, 1]) {
      m.box(0.14, 0.04, 0.46, sx * 0.4, 0, 0, C.frame);
      m.rbox(0.1, 1.17, 0.36, sx * 0.4, 0, 0, shell, 0.02);
      m.box(0.106, 0.06, 0.366, sx * 0.4, 0.92, 0, C.blue);
      m.box(0.008, 0.78, 0.22, sx * 0.348, 0.12, 0, C.dark);
    }
    m.rbox(0.9, 0.13, 0.36, 0, 1.15, 0, shell, 0.02);
    for (const sz of [-1, 1]) {
      m.box(0.34, 0.075, 0.008, 0, 1.178, sz * 0.182, C.black);
      m.box(0.05, 0.035, 0.012, -0.09, 1.198, sz * 0.183, 0x62b06e);
      m.box(0.05, 0.035, 0.012, 0, 1.198, sz * 0.183, C.yellow);
      m.box(0.05, 0.035, 0.012, 0.09, 1.198, sz * 0.183, C.redD);
    }
    m.cyl(0.05, 0.06, 0.02, 0, 1.28, 0, C.frame, 8);
    m.cyl(0.035, 0.04, 0.05, 0, 1.3, 0, 0x6dea9a, 8, { glow: true });
  });

const guard_tower: Fn = () =>
  model((m, f) => {
    const rail = C.slateD, roof = C.slate;
    // concrete stair core
    m.box(1.5, 0.08, 1.5, 0, 0, 0, C.concreteD);
    m.box(1.1, 0.26, 1.1, 0, 0.08, 0, C.concreteD);
    m.box(0.96, 1.72, 0.96, 0, 0.08, 0, C.concrete);
    m.box(1.06, 0.1, 1.06, 0, 1.7, 0, C.concreteD);
    m.box(0.44, 0.72, 0.1, 0, 0.08, 0.51, C.frame);
    m.box(0.33, 0.63, 0.02, 0, 0.08, 0.556, roof);
    m.box(0.03, 0.08, 0.02, 0.1, 0.38, 0.57, C.steelL);
    m.box(0.5, 0.05, 0.2, 0, 0.08, 0.66, C.concreteD);
    m.box(0.12, 0.05, 0.08, 0, 0.84, 0.5, C.dark);
    for (const s of [-1, 1]) {
      for (const y of [0.75, 1.2]) {
        m.box(0.014, 0.26, 0.1, s * 0.481, y, 0, C.darker);
        m.box(0.03, 0.03, 0.16, s * 0.485, y - 0.03, 0, C.concreteD);
      }
      m.box(0.1, 0.26, 0.014, 0, 1.0, -0.481, C.darker);
    }
    m.box(0.1, 0.26, 0.014, 0, 1.2, 0.481, C.darker);
    m.box(0.16, 0.03, 0.03, 0, 1.17, 0.485, C.concreteD);
    // brackets and deck
    for (const s of [-1, 1])
      for (const t of [-0.3, 0.3]) {
        beam(m, s * 0.48, 1.42, t, s * 0.86, 1.8, t, 0.06, C.gun);
        beam(m, t, 1.42, s * 0.48, t, 1.8, s * 0.86, 0.06, C.gun);
      }
    m.box(1.84, 0.1, 1.84, 0, 1.8, 0, C.frame);
    m.box(1.7, 0.006, 1.7, 0, 1.9, 0, 0x7d8792);
    m.box(0.3, 0.008, 0.3, -0.52, 1.9, -0.52, C.dark);
    // open railing all round
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) m.box(0.07, 0.46, 0.07, sx * 0.865, 1.9, sz * 0.865, rail);
    for (const s of [-1, 1]) {
      m.box(1.66, 0.09, 0.03, 0, 1.9, s * 0.88, rail);
      m.box(0.03, 0.09, 1.66, s * 0.88, 1.9, 0, rail);
      m.box(1.66, 0.03, 0.03, 0, 2.12, s * 0.875, rail);
      m.box(0.03, 0.03, 1.66, s * 0.875, 2.12, 0, rail);
      m.box(1.8, 0.05, 0.07, 0, 2.33, s * 0.87, C.beige);
      m.box(0.07, 0.05, 1.8, s * 0.87, 2.33, 0, C.beige);
      for (const t of [-0.43, 0, 0.43]) {
        m.box(0.03, 0.43, 0.03, t, 1.9, s * 0.875, rail);
        m.box(0.03, 0.43, 0.03, s * 0.875, 1.9, t, rail);
      }
      // slim canopy posts sit on the axes, clear of the diagonal sight lines to the guard
      m.box(0.05, 1.26, 0.05, s * 0.52, 1.9, 0, rail);
      m.box(0.05, 1.26, 0.05, 0, 1.9, s * 0.52, rail);
      beam(m, s * 0.52, 2.95, 0, s * 0.3, 3.15, 0, 0.035, rail);
      beam(m, 0, 2.95, s * 0.52, 0, 3.15, s * 0.3, 0.035, rail);
    }
    // small high canopy: the guard (y 1.9 - 2.85) stays visible beneath it
    f.cyl(0.68, 0.68, 0.05, 0, 3.15, 0, C.beige, 8, { ry: Math.PI / 8 });
    f.cone(0.64, 0.24, 0, 3.2, 0, roof, 8, { ry: Math.PI / 8 });
    m.cyl(0.012, 0.012, 0.2, 0, 3.42, 0, C.steelL, 5);
    m.sphere(0.035, 0, 3.6, 0, C.red, 1, 1, 1, 6);
    // searchlight on a stand at the front rail
    const sx = 0.5, sz = 0.72, t = 0.32;
    m.cyl(0.025, 0.035, 0.52, sx, 1.9, sz, C.dark, 6);
    m.box(0.3, 0.025, 0.06, sx, 2.4, sz, C.dark);
    for (const s of [-1, 1]) m.box(0.025, 0.16, 0.06, sx + s * 0.14, 2.4, sz, C.dark);
    const ay = -Math.sin(t), az = Math.cos(t);
    m.cyl(0.125, 0.1, 0.2, sx, 2.54 - 0.1, sz, C.darker, 10, { rx: HP + t });
    m.cyl(0.13, 0.13, 0.03, sx, 2.54 + ay * 0.1 - 0.015, sz + az * 0.1, C.steelD, 10, { rx: HP + t });
    m.cyl(0.105, 0.105, 0.02, sx, 2.54 + ay * 0.115 - 0.01, sz + az * 0.115, C.lamp, 10, { rx: HP + t, glow: true });
  });

const weapon_rack: Fn = () =>
  model((m) => {
    const body = 0x47525f;
    m.box(0.84, 0.3, 0.44, 0, 0, -0.1, body);
    for (const sx of [-1, 1]) {
      m.box(0.39, 0.2, 0.012, sx * 0.205, 0.05, 0.122, 0x56636f);
      m.box(0.14, 0.022, 0.022, sx * 0.205, 0.18, 0.134, C.steelL);
    }
    m.box(0.86, 0.02, 0.46, 0, 0.3, -0.1, 0x343c46);
    m.box(0.84, 0.8, 0.05, 0, 0.32, -0.3, 0x8a95a1);
    m.box(0.88, 0.05, 0.16, 0, 1.1, -0.25, body);
    for (const sx of [-1, 1]) m.box(0.04, 0.8, 0.12, sx * 0.42, 0.32, -0.27, body);
    // batons
    m.box(0.44, 0.03, 0.08, -0.19, 0.5, -0.24, C.steel);
    m.box(0.44, 0.03, 0.08, -0.19, 0.78, -0.24, C.steel);
    for (let i = 0; i < 4; i++) {
      const x = -0.35 + i * 0.105;
      m.cyl(0.02, 0.02, 0.5, x, 0.4, -0.215, C.black, 6);
      m.cyl(0.027, 0.027, 0.12, x, 0.82, -0.215, C.gun, 6);
    }
    // tasers
    m.box(0.36, 0.025, 0.1, 0.2, 0.9, -0.23, C.steel);
    for (const x of [0.11, 0.29]) {
      m.box(0.12, 0.045, 0.035, x, 0.97, -0.22, C.yellow);
      m.box(0.04, 0.07, 0.035, x - 0.03, 0.925, -0.22, C.darker);
    }
    // riot shield + helmet
    m.rbox(0.32, 0.56, 0.035, 0.22, 0.32, -0.19, C.slate, 0.03, { rx: -0.14 });
    m.box(0.22, 0.1, 0.01, 0.22, 0.7, -0.218, 0x9fc4d8, { rx: -0.14 });
    m.box(0.24, 0.05, 0.01, 0.22, 0.5, -0.172, C.cream, { rx: -0.14 });
    m.sphere(0.1, -0.22, 0.32, 0.0, C.darker, 1, 0.9, 1.05, 10);
    m.box(0.15, 0.055, 0.03, -0.22, 0.38, 0.085, 0x9fc4d8);
  });

// ================================================================== OFFICE

const office_desk: Fn = () =>
  model((m) => {
    const fab = C.slateD;
    // main desk across the front row
    m.box(1.84, 0.03, 0.8, 0, 0.41, 0.5, C.woodD);
    m.box(1.86, 0.02, 0.82, 0, 0.44, 0.5, C.wood);
    m.box(1.72, 0.34, 0.03, 0, 0.07, 0.85, C.woodD);
    m.box(0.04, 0.41, 0.72, 0.87, 0, 0.5, C.woodD);
    m.box(0.46, 0.4, 0.62, -0.64, 0.01, 0.52, C.woodD);
    for (let i = 0; i < 3; i++) {
      m.box(0.4, 0.105, 0.012, -0.64, 0.045 + i * 0.12, 0.204, C.wood);
      m.box(0.1, 0.02, 0.02, -0.64, 0.09 + i * 0.12, 0.192, C.gold);
    }
    // return wing along the left of the back row
    m.box(0.7, 0.03, 0.98, -0.57, 0.41, -0.42, C.woodD);
    m.box(0.72, 0.02, 1.0, -0.57, 0.44, -0.42, C.wood);
    m.box(0.62, 0.41, 0.04, -0.57, 0, -0.88, C.woodD);
    m.box(0.04, 0.41, 0.94, -0.89, 0, -0.42, C.woodD);
    // printer + folders on the wing
    m.box(0.38, 0.15, 0.32, -0.6, 0.46, -0.62, 0xd9d9d4);
    m.box(0.3, 0.012, 0.2, -0.6, 0.61, -0.6, C.dark);
    m.box(0.22, 0.008, 0.16, -0.6, 0.622, -0.56, C.white);
    m.box(0.22, 0.012, 0.14, -0.4, 0.5, -0.62, C.white);
    m.box(0.24, 0.03, 0.32, -0.6, 0.46, -0.16, 0xd9b97a, { ry: 0.1 });
    m.box(0.24, 0.03, 0.32, -0.59, 0.49, -0.16, C.blue, { ry: -0.08 });
    m.box(0.24, 0.03, 0.32, -0.6, 0.52, -0.16, C.red, { ry: 0.16 });
    // monitor (screen faces the sitter at -Z), keyboard, mouse
    m.box(0.22, 0.015, 0.15, 0.5, 0.46, 0.6, C.darker);
    m.box(0.045, 0.14, 0.03, 0.5, 0.47, 0.62, C.darker);
    m.box(0.5, 0.32, 0.035, 0.5, 0.56, 0.585, C.black);
    m.box(0.44, 0.26, 0.008, 0.5, 0.59, 0.5635, C.screen, { glow: true });
    m.box(0.2, 0.03, 0.009, 0.42, 0.78, 0.563, 0xdcecf8, { glow: true });
    m.box(0.3, 0.03, 0.009, 0.47, 0.72, 0.563, 0xb4d6f0, { glow: true });
    m.box(0.06, 0.06, 0.006, 0.5, 0.7, 0.605, C.steelD);
    m.box(0.32, 0.016, 0.11, 0.5, 0.46, 0.36, 0xd9d9d4);
    m.box(0.05, 0.022, 0.08, 0.76, 0.46, 0.36, 0xd9d9d4);
    // banker's lamp, phone, papers, mug, nameplate
    m.cyl(0.065, 0.075, 0.02, -0.34, 0.46, 0.72, C.gold, 8);
    m.cyl(0.012, 0.012, 0.2, -0.34, 0.48, 0.72, C.gold, 5);
    m.box(0.24, 0.035, 0.11, -0.34, 0.67, 0.71, C.greenD);
    m.box(0.2, 0.035, 0.08, -0.34, 0.705, 0.71, C.greenD);
    m.box(0.2, 0.05, 0.14, -0.02, 0.46, 0.72, C.darker);
    m.box(0.22, 0.035, 0.05, -0.02, 0.51, 0.75, C.black);
    m.box(0.21, 0.006, 0.28, 0.02, 0.46, 0.42, C.white, { ry: 0.25 });
    m.box(0.21, 0.006, 0.28, 0.05, 0.466, 0.4, C.white, { ry: -0.1 });
    m.cyl(0.036, 0.03, 0.075, 0.8, 0.46, 0.66, C.orange, 8);
    m.box(0.26, 0.055, 0.03, 0.3, 0.46, 0.84, C.gold, { rx: 0.25 });
    // swivel chair at (0.5, -0.5), facing +Z
    const cx = 0.5, cz = -0.5;
    for (let i = 0; i < 5; i++) {
      const a = (i / 5) * Math.PI * 2 + 0.3;
      beam(m, cx, 0.07, cz, cx + Math.cos(a) * 0.21, 0.04, cz + Math.sin(a) * 0.21, 0.035, C.darker);
      m.sphere(0.028, cx + Math.cos(a) * 0.21, 0, cz + Math.sin(a) * 0.21, C.black, 1, 1, 1, 6);
    }
    m.cyl(0.025, 0.03, 0.14, cx, 0.06, cz, C.steel, 6);
    m.rbox(0.42, 0.07, 0.42, cx, 0.19, cz, fab, 0.03);
    m.box(0.06, 0.2, 0.03, cx, 0.2, cz - 0.215, C.darker);
    m.rbox(0.4, 0.42, 0.06, cx, 0.34, cz - 0.225, fab, 0.03, { rx: -0.1 });
    for (const s of [-1, 1]) {
      m.box(0.03, 0.14, 0.03, cx + s * 0.225, 0.24, cz - 0.02, C.darker);
      m.box(0.045, 0.03, 0.24, cx + s * 0.225, 0.37, cz - 0.02, C.darker);
    }
    // waste basket
    m.cyl(0.085, 0.07, 0.2, -0.08, 0, -0.8, C.gun, 8);
    m.blob(0.055, -0.08, 0.17, -0.8, C.white, 1, 0.7, 1, 0);
  });

const filing_cabinet: Fn = () =>
  model((m) => {
    const unit = (x: number, h: number, n: number, body: number, face: number) => {
      m.box(0.38, 0.03, 0.56, x, 0, 0, C.dark);
      m.rbox(0.4, h, 0.6, x, 0.02, 0, body, 0.015);
      const dh = (h - 0.06) / n;
      for (let i = 0; i < n; i++) {
        const y = 0.05 + i * dh;
        m.box(0.35, dh - 0.025, 0.014, x, y, 0.3, face);
        m.box(0.14, 0.022, 0.022, x, y + dh * 0.32, 0.312, C.gun);
        m.box(0.1, 0.045, 0.006, x, y + dh * 0.55, 0.309, C.cream);
      }
    };
    unit(-0.205, 0.98, 4, 0x8a97a3, 0x9eabb7);
    unit(0.205, 0.74, 3, 0xb7b3a4, 0xc8c4b5);
    // archive box with folders on the short unit
    m.box(0.32, 0.15, 0.4, 0.2, 0.76, -0.04, C.card);
    m.box(0.34, 0.04, 0.42, 0.2, 0.9, -0.04, C.cardL);
    m.box(0.1, 0.04, 0.006, 0.2, 0.82, 0.164, C.cream);
    // papers on the tall unit
    m.box(0.24, 0.035, 0.32, -0.2, 1.0, 0.02, C.white, { ry: 0.12 });
    m.box(0.24, 0.02, 0.32, -0.2, 1.035, 0.02, 0xd9b97a, { ry: -0.1 });
  });

const plant: Fn = () =>
  model((m, f) => {
    f.cyl(0.175, 0.12, 0.25, 0, 0, 0, 0xb5653f, 10);
    f.cyl(0.19, 0.185, 0.045, 0, 0.235, 0, 0xc67a52, 10);
    m.cyl(0.16, 0.16, 0.008, 0, 0.275, 0, 0x4a3a2c, 10);
    rod(m, 0, 0.27, 0, 0.02, 0.68, -0.01, 0.018, C.greenD, 5, 0.01);
    const r = rng(11);
    const n = 9;
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 + r() * 0.5;
      const h = 0.3 + (i % 3) * 0.14 + r() * 0.05;
      const out = 0.75 + r() * 0.35, upw = 0.55 + (i % 3) * 0.28;
      const col = [C.green, C.greenD, C.greenL][i % 3];
      leaf(m, Math.cos(a) * 0.02, h, Math.sin(a) * 0.02, Math.cos(a) * out, upw, Math.sin(a) * out, 0.3 + r() * 0.06, 0.15, 0.035, col);
    }
    leaf(m, 0.02, 0.62, -0.01, 0.15, 1, 0.1, 0.3, 0.15, 0.04, C.greenL);
    leaf(m, 0.02, 0.6, -0.01, -0.3, 1, -0.2, 0.26, 0.13, 0.04, C.green);
  });

const vending: Fn = () =>
  model((m) => {
    const body = 0xb04a40;
    m.box(0.72, 0.04, 0.56, 0, 0, -0.03, C.darker);
    m.rbox(0.8, 1.1, 0.64, 0, 0.03, -0.03, body, 0.03);
    m.box(0.806, 0.1, 0.5, 0, 0.52, -0.05, C.cream);
    m.box(0.72, 1.0, 0.012, 0, 0.08, 0.289, C.darker);
    // lit product window
    m.box(0.46, 0.6, 0.008, -0.1, 0.42, 0.296, 0xe6f1f4, { glow: true });
    const pc = [C.red, C.yellow, C.blue, 0x62b06e, C.orange, C.purple, 0x3f8a84, C.pink];
    const r = rng(5);
    for (let row = 0; row < 3; row++) {
      const y = 0.42 + row * 0.2;
      m.box(0.46, 0.014, 0.016, -0.1, y, 0.304, C.dark);
      for (let i = 0; i < 4; i++) {
        const col = pc[Math.floor(r() * pc.length)];
        m.box(0.07, 0.1 + r() * 0.04, 0.014, -0.265 + i * 0.11, y + 0.014, 0.304, col);
      }
    }
    for (const sx of [-1, 1]) m.box(0.014, 0.6, 0.016, -0.1 + sx * 0.237, 0.42, 0.304, C.dark);
    m.box(0.49, 0.014, 0.016, -0.1, 1.02, 0.304, C.dark);
    // coin panel
    m.box(0.15, 0.3, 0.01, 0.25, 0.6, 0.297, C.steelD);
    m.box(0.11, 0.045, 0.008, 0.25, 0.95, 0.297, 0x8fe0a0, { glow: true });
    for (let i = 0; i < 6; i++) m.box(0.035, 0.03, 0.012, 0.225 + (i % 2) * 0.05, 0.7 + Math.floor(i / 2) * 0.05, 0.3, C.cream);
    m.box(0.012, 0.05, 0.012, 0.25, 0.63, 0.3, C.black);
    // delivery flap + marquee
    m.box(0.52, 0.16, 0.014, -0.08, 0.16, 0.297, C.dark);
    m.box(0.44, 0.08, 0.016, -0.08, 0.2, 0.299, C.gun);
    m.box(0.72, 0.06, 0.012, 0, 1.045, 0.296, C.cream);
    m.box(0.6, 0.5, 0.01, 0, 0.2, -0.352, C.darker);
  });

// ================================================================== OUTDOOR

const lamp_post: Fn = () =>
  model((m) => {
    m.box(0.32, 0.14, 0.32, 0, 0, 0, C.concreteD);
    m.box(0.22, 0.05, 0.22, 0, 0.14, 0, C.concrete);
    m.cyl(0.035, 0.055, 2.14, 0, 0.19, 0, C.frame, 8);
    m.box(0.11, 0.17, 0.07, 0, 0.62, 0.06, C.steelD);
    m.box(0.02, 0.04, 0.006, 0.02, 0.7, 0.097, C.yellow);
    m.box(0.09, 0.09, 0.3, 0, 2.28, 0, C.dark);
    // two floodlight heads, back to back
    for (const s of [-1, 1]) {
      const t = s * 0.3; // pitch down
      const nz = Math.cos(t) * s, ny = -Math.abs(Math.sin(t));
      const cy = 2.3, cz = s * 0.17;
      m.rbox(0.34, 0.24, 0.1, 0, cy - 0.12, cz, C.dark, 0.02, { rx: t });
      m.box(0.37, 0.02, 0.13, 0, cy + Math.cos(t) * 0.125 - 0.01, cz + s * Math.abs(Math.sin(t)) * 0.125 + nz * 0.01, C.darker, { rx: t });
      m.box(0.29, 0.19, 0.012, 0, cy + ny * 0.052 - 0.095, cz + nz * 0.052, C.lamp, { rx: t, glow: true });
    }
  });

const outdoor_bench: Fn = () =>
  model((m) => {
    const iron = C.dark;
    for (const sx of [-1, 1]) {
      const x = sx * 0.82;
      m.box(0.05, 0.4, 0.05, x, 0, 0.2, iron);
      beam(m, x, 0, -0.16, x, 0.66, -0.31, 0.05, iron);
      m.box(0.05, 0.04, 0.42, x, 0.19, 0.02, iron);
      m.box(0.065, 0.035, 0.5, x, 0.4, 0, iron);
      m.box(0.08, 0.02, 0.08, x, 0, 0.2, iron);
    }
    m.box(0.04, 0.2, 0.3, 0, 0, 0.03, iron);
    for (let i = 0; i < 4; i++) m.box(1.72, 0.03, 0.088, 0, 0.23, -0.125 + i * 0.1, i % 2 ? C.wood : 0xb4855a);
    for (let i = 0; i < 3; i++) m.box(1.72, 0.09, 0.03, 0, 0.34 + i * 0.105, -0.228 - i * 0.024, i % 2 ? 0xb4855a : C.wood, { rx: -0.22 });
  });

const tree: Fn = () =>
  model((m, f) => {
    f.cyl(0.12, 0.2, 0.14, 0, 0, 0, C.bark, 6);
    f.cyl(0.075, 0.12, 0.9, 0, 0.1, 0, C.bark, 6);
    rod(f, 0, 0.72, 0, 0.24, 1.08, 0.1, 0.05, C.bark, 5, 0.03);
    rod(f, 0, 0.66, 0, -0.24, 1.0, -0.1, 0.05, C.bark, 5, 0.03);
    m.blob(0.5, 0, 0.92, 0, C.green, 1, 0.9, 1, 1, { ry: 0.4 });
    m.blob(0.36, 0.27, 1.25, 0.12, C.greenL, 1, 0.9, 1, 1, { ry: 1.2 });
    m.blob(0.36, -0.27, 1.1, -0.1, C.greenD, 1, 0.9, 1, 1, { ry: 2.0 });
    m.blob(0.32, 0.0, 1.56, -0.04, C.greenL, 1, 0.95, 1, 1, { ry: 0.9 });
    m.blob(0.3, -0.06, 0.98, 0.3, C.green, 1, 0.85, 1, 1, { ry: 2.6 });
    m.blob(0.28, 0.1, 1.05, -0.32, C.greenD, 1, 0.85, 1, 1, { ry: 1.7 });
  });

const bushObj: Fn = () =>
  model((m) => {
    m.blob(0.3, -0.1, -0.1, 0.02, C.greenD, 1, 0.9, 1, 1, { ry: 0.3 });
    m.blob(0.27, 0.14, -0.08, -0.1, C.green, 1, 0.9, 1, 1, { ry: 1.3 });
    m.blob(0.23, 0.1, -0.06, 0.17, C.green, 1, 0.9, 1, 1, { ry: 2.1 });
    m.blob(0.2, -0.02, 0.2, -0.02, C.greenL, 1, 0.85, 1, 1, { ry: 0.8 });
    m.blob(0.15, -0.22, 0.1, 0.2, C.greenL, 1, 0.9, 1, 0, { ry: 0.2 });
    for (const [x, y, z] of [[0.2, 0.3, 0.2], [-0.24, 0.32, -0.08], [0.02, 0.5, 0.08], [0.28, 0.22, -0.2]]) m.blob(0.032, x, y, z, C.pink, 1, 1, 1, 0);
  });

const flower_bed: Fn = () =>
  model((m) => {
    for (const s of [-1, 1]) {
      m.box(0.86, 0.2, 0.06, 0, 0, s * 0.4, C.wood);
      m.box(0.86, 0.02, 0.07, 0, 0.2, s * 0.4, C.woodL);
      m.box(0.06, 0.2, 0.74, s * 0.4, 0, 0, C.woodD);
      m.box(0.07, 0.02, 0.74, s * 0.4, 0.2, 0, C.woodL);
      for (const t of [-1, 1]) m.box(0.075, 0.24, 0.075, s * 0.4, 0, t * 0.4, C.woodD);
    }
    m.box(0.76, 0.16, 0.76, 0, 0, 0, 0x4a3a2c);
    const cols = [0xd9534f, C.yellow, C.white, C.purple, C.pink, C.orange];
    const r = rng(3);
    for (let i = 0; i < 3; i++)
      for (let j = 0; j < 3; j++) {
        const x = -0.23 + i * 0.23 + (r() - 0.5) * 0.08, z = -0.23 + j * 0.23 + (r() - 0.5) * 0.08;
        const h = 0.13 + r() * 0.1;
        m.box(0.014, h, 0.014, x, 0.16, z, C.greenD);
        m.blob(0.055, x, 0.16 + h - 0.03, z, cols[(i * 3 + j * 2 + (i === j ? 1 : 0)) % cols.length], 1, 0.75, 1, 0, { ry: r() * 3 });
        m.blob(0.07, x + (r() - 0.5) * 0.1, 0.14, z + (r() - 0.5) * 0.1, i % 2 ? C.green : C.greenL, 1, 0.5, 1, 0, { ry: r() * 3 });
      }
  });

const flagpole: Fn = () =>
  model((m) => {
    m.box(0.5, 0.1, 0.5, 0, 0, 0, C.concreteD);
    m.box(0.34, 0.1, 0.34, 0, 0.1, 0, C.concrete);
    m.cyl(0.055, 0.07, 0.1, 0, 0.2, 0, C.steelD, 8);
    m.cyl(0.022, 0.034, 2.5, 0, 0.2, 0, 0xd5dadd, 8);
    m.sphere(0.05, 0, 2.69, 0, C.gold, 1, 1, 1, 8);
    rod(m, 0.035, 0.9, 0, 0.035, 2.64, 0, 0.005, C.beige, 4);
    m.box(0.03, 0.06, 0.02, 0.04, 0.9, 0, C.gun);
    // waving flag: three hinged panels with a pale band and an emblem
    const pts: [number, number][] = [[0.03, 0], [0.22, 0.055], [0.41, -0.03], [0.58, 0.035]];
    for (let i = 0; i < 3; i++) {
      const [x1, z1] = pts[i], [x2, z2] = pts[i + 1];
      const L = Math.hypot(x2 - x1, z2 - z1) + 0.012, ry = -Math.atan2(z2 - z1, x2 - x1);
      const cx = (x1 + x2) / 2, cz = (z1 + z2) / 2, y = 2.26 - i * 0.012;
      m.box(L, 0.13, 0.014, cx, y, cz, C.navy, { ry });
      m.box(L, 0.09, 0.014, cx, y + 0.13, cz, C.cream, { ry });
      m.box(L, 0.15, 0.014, cx, y + 0.22, cz, C.navy, { ry });
    }
    m.blob(0.045, 0.31, 2.345, 0.012, C.gold, 1, 1, 0.5, 0);
  });

const dumpster: Fn = () =>
  model((m) => {
    const body = 0x3e7a54, trim = 0x346847, lid = 0x2e3936;
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) cylZ(m, 0.065, 0.05, sx * 0.68, 0.065, sz * 0.3, C.black, 8);
    m.box(1.6, 0.5, 0.7, 0, 0.1, 0, body);
    m.box(1.78, 0.06, 0.8, 0, 0.58, 0, trim);
    for (const sz of [-1, 1]) for (const x of [-0.62, -0.2, 0.2, 0.62]) m.box(0.06, 0.46, 0.03, x, 0.12, sz * 0.36, trim);
    for (const sx of [-1, 1]) {
      m.box(0.04, 0.12, 0.34, sx * 0.82, 0.3, 0, C.frame);
      m.box(0.03, 0.46, 0.06, sx * 0.81, 0.12, 0, trim);
    }
    m.box(0.22, 0.15, 0.008, -0.41, 0.3, 0.354, C.yellow);
    m.box(0.1, 0.07, 0.01, -0.41, 0.34, 0.355, C.darker);
    // closed lid (left), propped lid (right) showing the rubbish
    m.box(0.87, 0.035, 0.82, -0.44, 0.64, 0, lid);
    m.box(0.3, 0.03, 0.04, -0.44, 0.675, 0.34, C.gun);
    m.box(0.84, 0.012, 0.72, 0.44, 0.635, 0, C.black);
    const t = -0.75;
    m.box(0.87, 0.035, 0.82, 0.44, 0.66 + 0.41 * Math.sin(-t) - 0.0175, -0.4 + 0.41 * Math.cos(t), lid, { rx: t });
    m.blob(0.2, 0.26, 0.5, 0.1, C.darker, 1.1, 0.8, 1, 1, { ry: 0.5 });
    m.blob(0.17, 0.6, 0.52, -0.02, 0x3a4048, 1, 0.85, 1, 1, { ry: 1.4 });
    m.blob(0.13, 0.42, 0.56, 0.24, C.cream, 1.1, 0.7, 1, 0, { ry: 0.7 });
    m.box(0.3, 0.02, 0.22, 0.56, 0.72, 0.2, C.card, { rx: -0.5, ry: 0.3 });
  });

// ================================================================== SCENERY

const tree_oak: Fn = () =>
  model((m, f) => {
    const bark = 0x6f5136;
    f.cyl(0.2, 0.32, 0.16, 0, 0, 0, bark, 7);
    f.cyl(0.14, 0.2, 0.95, 0, 0.12, 0, bark, 7);
    rod(f, 0, 0.9, 0, 0.42, 1.5, 0.15, 0.085, bark, 5, 0.045);
    rod(f, 0, 0.85, 0, -0.42, 1.45, -0.12, 0.085, bark, 5, 0.045);
    rod(f, 0, 0.95, 0, -0.05, 1.6, 0.36, 0.07, bark, 5, 0.04);
    m.blob(0.72, 0, 1.2, 0, C.green, 1, 0.8, 1, 1, { ry: 0.3 });
    m.blob(0.5, 0.52, 1.28, 0.2, C.greenL, 1, 0.85, 1, 1, { ry: 1.1 });
    m.blob(0.52, -0.52, 1.22, -0.15, C.greenD, 1, 0.85, 1, 1, { ry: 2.2 });
    m.blob(0.5, 0.08, 1.86, -0.08, C.greenL, 1, 0.85, 1, 1, { ry: 0.7 });
    m.blob(0.42, -0.15, 1.3, 0.52, C.green, 1, 0.85, 1, 1, { ry: 2.9 });
    m.blob(0.45, 0.2, 1.36, -0.52, C.greenD, 1, 0.85, 1, 1, { ry: 1.8 });
    m.blob(0.36, -0.34, 1.86, 0.2, C.green, 1, 0.85, 1, 1, { ry: 0.1 });
    m.blob(0.3, 0.46, 1.78, 0.28, C.greenL, 1, 0.85, 1, 1, { ry: 2.4 });
  });

const tree_round: Fn = () =>
  model((m, f) => {
    const bark = 0x8a6a4a, g1 = 0x5aa85a, g2 = 0x4a9450, g3 = 0x7cc068;
    f.cyl(0.1, 0.17, 0.12, 0, 0, 0, bark, 6);
    f.cyl(0.065, 0.1, 1.05, 0, 0.08, 0, bark, 6);
    m.blob(0.62, 0, 0.98, 0, g1, 1, 1, 1, 1, { ry: 0.5 });
    m.blob(0.4, 0.06, 1.66, 0.02, g3, 1, 0.95, 1, 1, { ry: 1.4 });
    m.blob(0.36, -0.34, 1.1, 0.24, g2, 1, 0.9, 1, 1, { ry: 2.3 });
    m.blob(0.36, 0.36, 1.2, -0.22, g2, 1, 0.9, 1, 1, { ry: 0.2 });
    m.blob(0.3, 0.3, 1.5, 0.3, g3, 1, 0.9, 1, 1, { ry: 1.9 });
  });

const tree_pine: Fn = () =>
  model((m, f) => {
    const bark = 0x5d4630;
    f.cyl(0.11, 0.18, 0.12, 0, 0, 0, bark, 6);
    f.cyl(0.075, 0.12, 0.75, 0, 0.08, 0, bark, 6);
    const tiers: [number, number, number, number][] = [
      [0.78, 0.95, 0.5, C.pine],
      [0.64, 0.9, 1.02, 0x38805a],
      [0.5, 0.82, 1.52, C.pine],
      [0.36, 0.74, 2.0, 0x38805a],
      [0.22, 0.6, 2.5, 0x459168],
    ];
    tiers.forEach(([r, h, y, col], i) => f.cone(r, h, 0, y, 0, col, 8, { ry: i * 0.45 }));
  });

const bushScenery: Fn = () =>
  model((m) => {
    m.blob(0.42, -0.12, -0.14, 0.04, C.greenD, 1.1, 0.85, 1, 1, { ry: 0.3 });
    m.blob(0.36, 0.26, -0.1, -0.14, C.green, 1, 0.9, 1, 1, { ry: 1.3 });
    m.blob(0.3, 0.18, -0.08, 0.28, C.green, 1, 0.9, 1, 1, { ry: 2.1 });
    m.blob(0.28, -0.04, 0.28, -0.04, C.greenL, 1, 0.85, 1, 1, { ry: 0.8 });
    m.blob(0.22, -0.38, 0.06, 0.26, C.greenL, 1, 0.9, 1, 0, { ry: 0.2 });
    m.blob(0.2, 0.44, 0.12, 0.1, C.greenL, 1, 0.9, 1, 0, { ry: 1.2 });
  });

const rock: Fn = () =>
  model((m) => {
    m.blob(0.36, -0.04, -0.1, 0, 0x8f9499, 1.25, 0.8, 1, 0, { ry: 0.4, rx: 0.2 });
    m.blob(0.24, 0.32, -0.07, 0.16, 0xa3a8ab, 1.1, 0.8, 1, 0, { ry: 1.3, rz: 0.3 });
    m.blob(0.17, -0.34, -0.05, 0.22, 0x7b8085, 1.2, 0.75, 1, 0, { ry: 2.2 });
    m.blob(0.13, 0.1, -0.04, -0.34, 0x8a8f94, 1.1, 0.8, 1, 0, { ry: 0.9 });
    m.blob(0.16, -0.12, 0.34, -0.02, 0x6f9a58, 1.3, 0.3, 1.1, 0, { ry: 0.6 });
  });

const streetlight: Fn = () =>
  model((m) => {
    m.cyl(0.09, 0.11, 0.26, 0, 0, 0, C.dark, 8);
    m.cyl(0.035, 0.055, 2.2, 0, 0.26, 0, C.gun, 8);
    rod(m, 0, 2.42, 0, 0, 2.6, 0.28, 0.032, C.gun, 6, 0.028);
    rod(m, 0, 2.6, 0.28, 0, 2.6, 0.5, 0.028, C.gun, 6);
    m.rbox(0.18, 0.07, 0.4, 0, 2.55, 0.58, C.dark, 0.025);
    m.box(0.14, 0.05, 0.3, 0, 2.515, 0.6, C.lamp, { glow: true });
  });

/** Round wheel on the Z axis: tyre + hub cap on both sides. */
function wheels(m: MB, xs: number[], z: number, r: number, w: number) {
  for (const x of xs)
    for (const s of [-1, 1]) {
      cylZ(m, r, w, x, r, s * z, C.black, 14);
      cylZ(m, r * 0.52, w + 0.012, x, r, s * z, 0xb4bcc4, 8);
      cylZ(m, r * 0.2, w + 0.024, x, r, s * z, C.gun, 6);
    }
}

const bus: Fn = () =>
  model((m) => {
    const body = 0xe9e9e6, stripe = C.navy;
    wheels(m, [-1.35, 1.42], 0.655, 0.3, 0.2);
    m.box(4.2, 0.2, 1.24, 0, 0.2, 0, C.darker);
    // cabin and bonnet
    m.rbox(3.7, 1.2, 1.48, -0.35, 0.36, 0, body, 0.1);
    m.rbox(0.92, 0.62, 1.42, 1.76, 0.36, 0, body, 0.1);
    m.rbox(3.4, 0.1, 1.28, -0.35, 1.5, 0, 0xd5d8d6, 0.04);
    m.box(0.5, 0.07, 0.5, -1.1, 1.59, 0, 0xb4bcc4);
    m.box(0.5, 0.07, 0.5, -0.1, 1.59, 0, 0xb4bcc4);
    m.box(0.14, 0.07, 0.5, 1.1, 1.59, 0, 0xd9862e);
    for (const s of [-1, 1]) {
      const z = s * 0.741;
      // stripe + wheel arches
      m.box(3.5, 0.14, 0.012, -0.35, 0.74, z, stripe);
      m.box(3.5, 0.03, 0.012, -0.35, 0.68, z, C.blue);
      m.box(0.72, 0.14, 0.012, 1.74, 0.74, s * 0.711, stripe);
      for (const x of [-1.35, 1.42]) m.box(0.76, 0.3, 0.014, x, 0.355, x > 0 ? s * 0.712 : z, C.darker);
      // barred windows
      for (let i = 0; i < 5; i++) m.box(0.44, 0.34, 0.012, -1.9 + i * 0.55, 1.0, z, C.glass);
      for (const y of [1.09, 1.22]) m.box(2.66, 0.022, 0.02, -0.8, y, s * 0.745, C.steel);
      for (let i = 0; i < 5; i++) m.box(0.022, 0.34, 0.02, -1.9 + i * 0.55, 1.0, s * 0.745, C.steel);
      m.box(0.44, 0.34, 0.012, 1.02, 1.0, z, C.glass); // driver / door glass
      m.box(0.34, 0.2, 0.014, -0.5, 0.42, z, stripe); // badge
      m.box(0.2, 0.07, 0.016, -0.5, 0.485, z, C.gold);
      // mirrors
      m.box(0.05, 0.16, 0.04, 1.46, 1.04, s * 0.82, C.darker);
      m.box(0.04, 0.03, 0.1, 1.46, 1.1, s * 0.78, C.darker);
      // lights
      m.box(0.016, 0.13, 0.2, 2.215, 0.62, s * 0.5, C.lamp, { glow: true });
      m.box(0.014, 0.07, 0.1, 2.213, 0.52, s * 0.52, 0xe09a3a);
      m.box(0.014, 0.12, 0.16, -2.201, 0.6, s * 0.56, C.red);
    }
    // entry door on the kerb side (+Z)
    m.box(0.5, 0.92, 0.008, 1.02, 0.42, 0.744, 0xd0d4d2);
    m.box(0.012, 0.92, 0.012, 1.02, 0.42, 0.748, C.frame);
    m.box(0.4, 0.36, 0.012, 1.02, 0.94, 0.746, C.glass);
    // windscreen, grille, bumpers, rear door
    m.box(0.012, 0.46, 1.26, 1.502, 0.98, 0, C.glass);
    m.box(0.02, 0.46, 0.03, 1.504, 0.98, 0, body);
    m.box(0.016, 0.26, 0.74, 2.213, 0.5, 0, C.dark);
    for (let i = 0; i < 3; i++) m.box(0.02, 0.02, 0.7, 2.216, 0.56 + i * 0.07, 0, C.steelD);
    m.box(0.12, 0.14, 1.46, 2.22, 0.3, 0, C.dark);
    m.box(0.1, 0.14, 1.46, -2.22, 0.3, 0, C.dark);
    m.box(0.012, 0.9, 0.66, -2.202, 0.5, 0, 0xd0d4d2);
    m.box(0.014, 0.3, 0.5, -2.204, 1.0, 0, C.glass);
    for (const z of [-0.12, 0.12]) m.box(0.02, 0.3, 0.022, -2.206, 1.0, z, C.steel);
  });

const truck: Fn = () =>
  model((m) => {
    const cab = 0x3f8a84, cabD = 0x357670, box = 0xeeeae0;
    wheels(m, [-1.15, 1.32], 0.64, 0.28, 0.2);
    m.box(3.8, 0.16, 1.1, 0, 0.24, 0, C.darker);
    cylX(m, 0.12, 0.5, 0.2, 0.3, 0.56, C.steelD, 8);
    cylX(m, 0.12, 0.5, 0.2, 0.3, -0.56, C.steelD, 8);
    // cab
    m.rbox(1.06, 1.06, 1.44, 1.4, 0.34, 0, cab, 0.1);
    m.box(0.012, 0.42, 1.22, 1.932, 0.86, 0, C.glass);
    m.box(0.016, 0.2, 0.9, 1.932, 0.44, 0, C.dark);
    for (let i = 0; i < 2; i++) m.box(0.02, 0.02, 0.86, 1.935, 0.5 + i * 0.07, 0, C.steelD);
    m.box(0.1, 0.13, 1.46, 1.94, 0.27, 0, C.dark);
    m.box(0.3, 0.05, 0.9, 1.3, 1.4, 0, cabD);
    for (const s of [-1, 1]) {
      m.box(0.5, 0.36, 0.012, 1.5, 0.9, s * 0.721, C.glass);
      m.box(0.012, 0.5, 0.012, 1.2, 0.4, s * 0.722, cabD);
      m.box(0.1, 0.03, 0.02, 1.34, 0.78, s * 0.724, C.steelL);
      m.box(0.7, 0.28, 0.014, 1.32, 0.34, s * 0.722, C.darker);
      m.box(0.05, 0.2, 0.05, 1.8, 0.98, s * 0.8, C.darker);
      m.box(0.04, 0.03, 0.1, 1.8, 1.06, s * 0.76, C.darker);
      m.box(0.016, 0.11, 0.2, 1.934, 0.6, s * 0.54, C.lamp, { glow: true });
      m.box(0.014, 0.1, 0.14, -2.012, 0.56, s * 0.6, C.red);
      // box livery
      m.box(2.6, 0.2, 0.012, -0.62, 0.72, s * 0.751, cab);
      m.box(2.6, 0.04, 0.012, -0.62, 0.95, s * 0.751, C.orange);
      cylZ(m, 0.24, 0.012, -0.62, 1.36, s * 0.751, C.orange, 14);
      m.box(0.22, 0.2, 0.016, -0.62, 1.26, s * 0.752, box);
      m.box(0.8, 0.26, 0.014, -1.15, 0.44, s * 0.752, C.darker);
    }
    // cargo box
    m.rbox(2.76, 1.36, 1.5, -0.62, 0.44, 0, box, 0.05);
    m.box(2.6, 0.03, 1.36, -0.62, 1.79, 0, 0xd9d6cc);
    m.box(0.012, 1.2, 1.3, -2.002, 0.5, 0, C.steelL);
    for (let i = 0; i < 5; i++) m.box(0.014, 0.014, 1.3, -2.004, 0.68 + i * 0.2, 0, C.steelD);
    m.box(0.02, 0.05, 0.2, -2.006, 0.56, 0, C.dark);
    m.box(0.14, 0.06, 1.44, -2.02, 0.3, 0, C.dark);
  });

const car: Fn = () =>
  model((m) => {
    const body = 0xe9e9e9;
    wheels(m, [-0.74, 0.76], 0.515, 0.19, 0.17);
    m.rbox(2.36, 0.37, 1.16, 0, 0.15, 0, body, 0.09);
    m.rbox(1.3, 0.34, 1.02, -0.14, 0.48, 0, C.glass, 0.07);
    m.rbox(1.16, 0.07, 0.98, -0.14, 0.79, 0, body, 0.03);
    for (const s of [-1, 1]) {
      for (const x of [-0.76, -0.14, 0.48]) m.box(0.075, 0.3, 0.06, x, 0.5, s * 0.486, body);
      for (const x of [-0.74, 0.76]) m.box(0.5, 0.2, 0.012, x, 0.15, s * 0.578, C.darker);
      m.box(0.012, 0.26, 0.008, -0.14, 0.2, s * 0.582, 0xb9b9b9);
      m.box(0.07, 0.02, 0.014, -0.3, 0.42, s * 0.584, C.gun);
      m.box(0.07, 0.02, 0.014, 0.32, 0.42, s * 0.584, C.gun);
      m.box(0.06, 0.05, 0.08, 0.5, 0.5, s * 0.6, body);
      m.box(0.016, 0.085, 0.24, 1.176, 0.35, s * 0.38, C.lamp, { glow: true });
      m.box(0.016, 0.075, 0.26, -1.176, 0.37, s * 0.38, C.red);
    }
    m.box(0.016, 0.08, 0.46, 1.176, 0.24, 0, C.dark);
    m.box(0.07, 0.07, 1.1, 1.16, 0.15, 0, C.gun);
    m.box(0.07, 0.07, 1.1, -1.16, 0.15, 0, C.gun);
    m.box(0.016, 0.07, 0.24, -1.178, 0.25, 0, C.cream);
  });

const OBJECT_MODELS: Record<string, Fn> = {
  bed, bunk, toilet, cell_desk, locker,
  shower, sink, laundry_machine, laundry_basket,
  cooker, fridge, kitchen_counter, serving_counter, table, bench, bin,
  tv, sofa, pool_table, bookshelf, chair, phone, weight_bench, punching_bag, basketball_hoop, pew, altar, visit_table,
  medical_bed, medicine_cabinet,
  workshop_saw, workshop_press, school_desk, blackboard, crates, shelving,
  cctv, cctv_monitor, metal_detector, guard_tower, weapon_rack,
  office_desk, filing_cabinet, plant, vending,
  lamp_post, outdoor_bench, tree, bush: bushObj, flower_bed, flagpole, dumpster,
};

const SCENERY_MODELS: Record<SceneryKind, Fn> = {
  tree_oak, tree_round, tree_pine, bush: bushScenery, rock, streetlight, bus, truck, car,
};

/** Model for a placeable object. `id` is an ObjectDef.id from data/defs.ts. */
export function buildObjectModel(id: string): ModelResult {
  const fn = OBJECT_MODELS[id];
  if (!fn) throw new Error(`models: no model for object "${id}"`);
  return fn();
}

/** Model for a piece of scenery or a vehicle. */
export function buildScenery(kind: SceneryKind): ModelResult {
  const fn = SCENERY_MODELS[kind];
  if (!fn) throw new Error(`models: no scenery model "${kind}"`);
  return fn();
}
