import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { Kit, Opening, yawFacing } from './kit';
import * as P from './props';
import { BlindSpec, wallBlind } from './blinds';
import { ScreenKind } from './atlas';

/*  The bridge, modelled on the Covenant's: a low (2.45 m), split-level flight deck under a faceted
 *  wraparound canopy with blinders; analogue consoles following the glass; exposed-frame harness
 *  chairs for the pilot, co-pilot, comms and systems; a captain's chair; and the holo-nav table
 *  the crew gather around. Deck 1, behind the bulkhead at x = 8. */

const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

type Pt = { x: number; z: number };

/** Local frame at (x, y, z) with mesh yaw m: local +x along, local +z forward. */
function frame(k: Kit, x: number, y: number, z: number, m: number) {
  const base = new THREE.Matrix4().makeRotationY(m).setPosition(x, y, z);
  const q = new THREE.Quaternion();
  const one = V(1, 1, 1);
  const put = (g: THREE.BufferGeometry, key: string, lp: THREE.Vector3, le = new THREE.Euler()) => {
    q.setFromEuler(le);
    k.b.add(g, key, new THREE.Matrix4().multiplyMatrices(base, new THREE.Matrix4().compose(lp, q, one)));
  };
  const pt = (lx: number, ly: number, lz: number) => V(lx, ly, lz).applyMatrix4(base);
  const box = (x0: number, y0: number, z0: number, x1: number, y1: number, z1: number, key: string, round = 0) => {
    const w = x1 - x0;
    const h = y1 - y0;
    const d = z1 - z0;
    const r = Math.min(round, w / 2 - 1e-3, h / 2 - 1e-3, d / 2 - 1e-3);
    put(r > 0.004 ? new RoundedBoxGeometry(w, h, d, 2, r) : new THREE.BoxGeometry(w, h, d), key, V((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2));
  };
  const cyl = (a: THREE.Vector3, b: THREE.Vector3, r: number, key: string, seg = 10) => k.b.cyl(pt(a.x, a.y, a.z), pt(b.x, b.y, b.z), r, key, seg);
  /** World AABB of a local box, added as a collider. */
  const solid = (x0: number, y0: number, z0: number, x1: number, y1: number, z1: number, tag = 'solid') => {
    const cs = [pt(x0, y0, z0), pt(x1, y0, z0), pt(x0, y0, z1), pt(x1, y0, z1)];
    const xs = cs.map((c) => c.x);
    const zs = cs.map((c) => c.z);
    k.world.add(Math.min(...xs), y + y0, Math.min(...zs), Math.max(...xs), y + y1, Math.max(...zs), tag);
  };
  return { put, pt, box, cyl, solid };
}

/** Facet geometry: midpoint, length, mesh yaw whose local +z points into the room. */
function facet(a: Pt, b: Pt, inside: Pt) {
  const dx = b.x - a.x;
  const dz = b.z - a.z;
  const len = Math.hypot(dx, dz);
  let m = Math.atan2(-dz / len, dx / len);
  const mx = (a.x + b.x) / 2;
  const mz = (a.z + b.z) / 2;
  // local +z = (sin m, cos m); flip if it points away from the room
  if (Math.sin(m) * (inside.x - mx) + Math.cos(m) * (inside.z - mz) < 0) m += Math.PI;
  return { mx, mz, len, m, nx: Math.sin(m), nz: Math.cos(m) };
}

/** Exposed-frame flight chair with harness (stripped-back framework, re-upholstered). */
function flightChair(k: Kit, x: number, y: number, z: number, m: number, label: string, cushion = 'fabric'): void {
  const c = frame(k, x, y, z, m);
  c.put(new THREE.CylinderGeometry(0.28, 0.31, 0.04, 20), 'paintDark', V(0, 0.02, 0));
  c.put(new THREE.CylinderGeometry(0.07, 0.09, 0.36, 12), 'steel', V(0, 0.22, 0));
  c.box(-0.27, 0.38, -0.27, 0.27, 0.42, 0.26, 'metal');
  c.box(-0.25, 0.42, -0.25, 0.25, 0.52, 0.25, cushion, 0.04);
  for (const sx of [-0.25, 0.25]) c.cyl(V(sx, 0.42, -0.27), V(sx, 1.32, -0.4), 0.022, 'steel', 8);
  c.cyl(V(-0.25, 1.32, -0.4), V(0.25, 1.32, -0.4), 0.022, 'steel', 8);
  c.cyl(V(-0.25, 0.42, 0.24), V(0.25, 0.42, 0.24), 0.018, 'steel', 8);
  c.put(new RoundedBoxGeometry(0.46, 0.78, 0.09, 2, 0.04), cushion, V(0, 0.9, -0.31), new THREE.Euler(-0.14, 0, 0));
  c.put(new RoundedBoxGeometry(0.3, 0.17, 0.1, 2, 0.04), cushion, V(0, 1.23, -0.37), new THREE.Euler(-0.14, 0, 0));
  for (const sx of [-1, 1]) {
    c.box(sx * 0.31 - 0.035, 0.62, -0.22, sx * 0.31 + 0.035, 0.67, 0.2, 'paintDark', 0.01);
    c.cyl(V(sx * 0.31, 0.42, -0.15), V(sx * 0.31, 0.62, -0.15), 0.015, 'steel', 6);
    c.box(sx * 0.31 - 0.025, 0.67, 0.04, sx * 0.31 + 0.025, 0.676, 0.16, sx > 0 ? 'statusAmber' : 'statusGreen');
  }
  for (const sx of [-0.1, 0.1]) c.put(new THREE.BoxGeometry(0.05, 0.62, 0.012), 'warning', V(sx, 0.93, -0.255), new THREE.Euler(-0.14, 0, 0));
  c.box(-0.06, 0.53, 0.0, 0.06, 0.58, 0.04, 'chrome');
  c.solid(-0.3, 0, -0.45, 0.3, 0.7, 0.28);
  const s = c.pt(0, 0.52, 0.02);
  const e = c.pt(0, 0, 0.85);
  k.seatAt(s.x, s.y, s.z, yawFacing(Math.sin(m), Math.cos(m)), label, e.x, e.z);
}

/** Console that follows a canopy facet: low dash, angled CRTs, toggles, knobs, lit buttons. */
function facetConsole(k: Kit, f: ReturnType<typeof facet>, y: number, depth: number, kinds: ScreenKind[], seed: number): void {
  const c = frame(k, f.mx, y, f.mz, f.m);
  const L = f.len - 0.3;
  const z0 = 0.16;
  const z1 = z0 + depth;
  c.box(-L / 2, 0, z0, L / 2, 0.76, z1 - 0.06, 'paintDark', 0.02);
  c.box(-L / 2, 0, z1 - 0.06, L / 2, 0.08, z1, 'rubber');
  c.box(-L / 2 - 0.01, 0.76, z0 - 0.02, L / 2 + 0.01, 0.8, z1 + 0.02, 'metal', 0.01);
  c.solid(-L / 2, 0, z0, L / 2, 0.82, z1);
  // angled CRTs along the back edge
  const n = kinds.length;
  kinds.forEach((kind, i) => {
    const x = -L / 2 + (L * (i + 0.5)) / n;
    const sw = Math.min(0.46, L / n - 0.08);
    c.box(x - sw / 2 - 0.03, 0.8, z0 + 0.02, x + sw / 2 + 0.03, 0.86, z0 + 0.2, 'paintDark', 0.01);
    k.screen(kind, c.pt(x, 0.98, z0 + 0.13), f.m, sw, 141 + ((seed + i) % 3), '', 0.55);
  });
  // hardware
  let sd = seed * 13 + 5;
  const rnd = () => ((sd = (sd * 16807) % 2147483647) / 2147483647);
  for (let z = z0 + 0.26; z < z1 - 0.06; z += 0.075) {
    for (let x = -L / 2 + 0.06; x < L / 2 - 0.05; x += 0.05) {
      const r = rnd();
      if (r < 0.15) continue;
      if (r < 0.42) c.put(new THREE.BoxGeometry(0.008, 0.045, 0.008), 'chrome', V(x, 0.83, z), new THREE.Euler(rnd() > 0.5 ? 0.45 : -0.45, 0, 0));
      else if (r < 0.6) c.put(new THREE.CylinderGeometry(0.017, 0.02, 0.025, 10), 'paintDark', V(x, 0.813, z));
      else c.box(x - 0.015, 0.8, z - 0.015, x + 0.015, 0.814, z + 0.015, r < 0.74 ? 'statusAmber' : r < 0.8 ? 'statusGreen' : r < 0.83 ? 'statusRed' : 'paintGrey');
    }
  }
  c.box(-L / 2 + 0.05, 0.6, z1 - 0.005, L / 2 - 0.05, 0.62, z1 + 0.005, 'ledStrip');
}

/** A canopy facet: lower wall, posts, header, glass, inner trims with a warm light line. */
function canopyFacet(k: Kit, f: ReturnType<typeof facet>, y: number, sill: number, top: number): void {
  const c = frame(k, f.mx, y, f.mz, f.m);
  const L = f.len;
  const post = 0.16;
  c.box(-L / 2, 0, -0.16, L / 2, sill, 0.16, 'wallDark');
  c.box(-L / 2, top, -0.18, L / 2, 2.62, 0.18, 'ribDark');
  c.box(-L / 2, 0, -0.19, -L / 2 + post, 2.62, 0.19, 'ribDark');
  c.box(L / 2 - post, 0, -0.19, L / 2, 2.62, 0.19, 'ribDark');
  c.box(-L / 2 + post, sill, -0.012, L / 2 - post, top, 0.012, 'glass');
  c.box(-L / 2 + post, sill - 0.05, 0.14, L / 2 - post, sill, 0.3, 'metal');
  c.box(-L / 2 + post, top, 0.1, L / 2 - post, top + 0.05, 0.22, 'ribDark');
  c.box(-L / 2 + post + 0.05, top - 0.012, 0.16, L / 2 - post - 0.05, top, 0.2, 'lightWarm');
  // colliders along the facet (wall-tagged so they block interaction rays)
  const segs = 4;
  for (let i = 0; i < segs; i++) {
    const x0 = -L / 2 + (L * i) / segs;
    const x1 = -L / 2 + (L * (i + 1)) / segs;
    c.solid(x0, 0, -0.16, x1, 2.62, 0.16, 'wall');
  }
}

/** Extruded floor/ceiling slab from a plan polygon. */
function slab(k: Kit, pts: Pt[], y0: number, thick: number, key: string): void {
  const sh = new THREE.Shape();
  sh.moveTo(pts[0].x, -pts[0].z);
  for (const p of pts.slice(1)) sh.lineTo(p.x, -p.z);
  sh.closePath();
  const g = new THREE.ExtrudeGeometry(sh, { depth: thick, bevelEnabled: false });
  g.rotateX(-Math.PI / 2);
  g.translate(0, y0, 0);
  k.b.add(g, key);
}

export function buildBridge(k: Kit, y: number, accentDeck: string, blinds: BlindSpec[]): THREE.Vector3 {
  const H = 2.45;
  const inside: Pt = { x: 12, z: 0 };
  // nose outline from the starboard side round to port
  const nose: Pt[] = [
    { x: 12.5, z: 6.0 },
    { x: 15.0, z: 5.6 },
    { x: 16.9, z: 4.0 },
    { x: 17.9, z: 1.5 },
    { x: 17.9, z: -1.5 },
    { x: 16.9, z: -4.0 },
    { x: 15.0, z: -5.6 },
    { x: 12.5, z: -6.0 },
  ];
  k.room({ id: 'bridge', name: 'Bridge', deck: 'command', x0: 8, x1: 17.9, z0: -6, z1: 6, y0: y, h: H, ambience: 'hab' }, { floor: 'none', ceil: null, profile: 'none', intensity: 2.4, lightColor: 0xffd9b0 });
  const outline: Pt[] = [{ x: 8, z: 6 }, ...nose, { x: 8, z: -6 }];
  slab(k, outline, y - 0.2, 0.2, 'floor');
  slab(k, outline, y + H, 0.25, 'ceil');
  k.world.add(8, y - 0.2, -6, 17.9, y, 6);
  k.world.add(8, y + H, -6, 17.9, y + H + 0.25, 6);

  // side walls with a viewport each, then the faceted canopy
  const side = (z: number, dir: 1 | -1) => {
    const op: Opening = { at: 10.3, w: 2.2, y0: 0.8, y1: 2.05, kind: 'window' };
    k.wallZ(z, 8, 12.5, y, { t: 0.4, offset: z > 0 ? 0.2 : -0.2, openings: [op] });
    blinds.push(wallBlind('z', z, dir, 10.3, 2.2, y, 0.8, 2.05));
  };
  side(6, -1);
  side(-6, 1);
  const facets = nose.slice(0, -1).map((a, i) => facet(a, nose[i + 1], inside));
  for (const f of facets) {
    canopyFacet(k, f, y, 0.7, 2.05);
    blinds.push({ x: f.mx + f.nx * 0.15, z: f.mz + f.nz * 0.15, yaw: f.m, w: f.len - 0.34, y, y0: 0.7, y1: 2.05 });
  }

  // raised forward flight deck (split level), hazard edge, rails with a gap at the centre
  const ry = 0.24;
  const deckPts: Pt[] = [{ x: 14.2, z: 5.73 }, ...nose.slice(1, -1), { x: 14.2, z: -5.73 }];
  slab(k, deckPts, y, ry, 'deckPlate');
  k.world.add(14.2, y, -5.73, 17.9, y + ry, 5.73);
  k.b.box(14.16, y, -5.7, 14.24, y + ry + 0.012, 5.7, 'hazard', false);
  k.b.box(14.24, y + ry, -5.6, 14.3, y + ry + 0.012, 5.6, 'ledStrip', false);
  for (const [z0, z1] of [[1.1, 5.6], [-5.6, -1.1]]) {
    k.b.cyl(V(14.2, y + ry + 0.95, z0), V(14.2, y + ry + 0.95, z1), 0.025, 'steel', 8);
    for (const zz of [z0, (z0 + z1) / 2, z1]) k.b.cyl(V(14.2, y, zz), V(14.2, y + ry + 0.95, zz), 0.02, 'steel', 6);
    k.world.add(14.15, y, Math.min(z0, z1), 14.25, y + 1.2, Math.max(z0, z1));
  }
  const fy = y + ry;

  // consoles following the glass
  facetConsole(k, facets[3], fy, 0.7, ['nav', 'telemetry', 'orbit', 'status'], 141);
  facetConsole(k, facets[2], fy, 0.62, ['comms', 'telemetry', 'status'], 151);
  facetConsole(k, facets[4], fy, 0.62, ['status', 'orbit', 'nav'], 161);
  facetConsole(k, facets[1], fy, 0.62, ['comms', 'telemetry'], 171);
  facetConsole(k, facets[5], fy, 0.62, ['status', 'telemetry'], 181);

  // pilot and co-pilot face the front glass; comms and systems face their own facets
  flightChair(k, 16.45, fy, 0.82, Math.PI / 2, 'Pilot seat');
  flightChair(k, 16.45, fy, -0.82, Math.PI / 2, 'Co-pilot seat');
  for (const [fi, label] of [[1, 'Comms station'], [5, 'Systems station']] as const) {
    const f = facets[fi];
    const d = 0.16 + 0.62 + 0.62;
    flightChair(k, f.mx + f.nx * d, fy, f.mz + f.nz * d, f.m + Math.PI, label);
  }
  // joysticks and a throttle quadrant at the front console
  const fc = frame(k, facets[3].mx, fy, facets[3].mz, facets[3].m);
  for (const sx of [-0.82, 0.82]) {
    for (const off of [-0.32, 0.32]) {
      fc.put(new THREE.CylinderGeometry(0.05, 0.06, 0.04, 12), 'paintDark', V(sx + off, 0.82, 0.78));
      fc.cyl(V(sx + off, 0.82, 0.78), V(sx + off, 1.02, 0.84), 0.014, 'metal', 8);
      fc.put(new THREE.SphereGeometry(0.03, 10, 8), 'rubber', V(sx + off, 1.04, 0.85));
    }
  }
  fc.box(-0.14, 0.8, 0.5, 0.14, 0.88, 0.8, 'paintDark', 0.01);
  for (const tx of [-0.08, 0, 0.08]) fc.cyl(V(tx, 0.88, 0.62), V(tx, 0.99, 0.58), 0.009, 'chrome', 6);

  // overhead switch banks hanging just inside the canopy, tilted toward the crew
  for (const fi of [2, 3, 4]) {
    const f = facets[fi];
    const c = frame(k, f.mx, y, f.mz, f.m);
    const L = f.len - 0.4;
    c.put(new THREE.BoxGeometry(L, 0.07, 0.55), 'paintDark', V(0, H - 0.2, 0.55), new THREE.Euler(0.55, 0, 0));
    let sd = fi * 31;
    const rnd = () => ((sd = (sd * 16807) % 2147483647) / 2147483647);
    for (let x = -L / 2 + 0.06; x < L / 2 - 0.05; x += 0.07) {
      for (let r = 0; r < 4; r++) {
        const v = rnd();
        const key = v < 0.18 ? 'statusAmber' : v < 0.26 ? 'statusGreen' : v < 0.29 ? 'statusRed' : 'paintGrey';
        c.put(new THREE.BoxGeometry(0.035, 0.012, 0.035), key, V(x, H - 0.25 + r * 0.06, 0.38 + r * 0.1), new THREE.Euler(0.55, 0, 0));
      }
    }
  }
  // centre overhead spine and ceiling beams
  k.b.box(9.0, y + H - 0.16, -0.38, 14.0, y + H, 0.38, 'ribDark', false, 0.02);
  for (let x = 9.2; x < 13.9; x += 0.08) {
    for (const z of [-0.26, -0.14, 0.14, 0.26]) {
      const v = Math.sin(x * 91 + z * 37);
      k.b.box(x - 0.016, y + H - 0.175, z - 0.016, x + 0.016, y + H - 0.16, z + 0.016, v > 0.7 ? 'statusAmber' : v > 0.55 ? 'statusGreen' : 'paintGrey', false);
    }
  }
  k.b.box(9.0, y + H - 0.18, -0.02, 14.0, y + H - 0.16, 0.02, 'lightWarm', false);
  for (const x of [9.6, 11.2, 12.8]) k.b.box(x - 0.1, y + H - 0.14, -6, x + 0.1, y + H, 6, 'rib', false);
  // downlights over each station
  for (const [x, z] of [[16.45, 0.82], [16.45, -0.82], [15.4, 3.6], [15.4, -3.6], [13.4, 0], [11.0, 0]]) {
    k.b.geo(new THREE.CylinderGeometry(0.1, 0.12, 0.05, 16), 'ribDark', V(x, y + H - 0.025, z));
    k.b.geo(new THREE.CylinderGeometry(0.075, 0.075, 0.01, 16), 'lightWarm', V(x, y + H - 0.05, z));
  }

  // lower level: captain's chair behind the pilots, holo-nav table, side stations
  flightChair(k, 13.4, y, 0, Math.PI / 2, "Captain's chair", 'fabricAmber');
  P.consoleUnit(k, { x: 10.3, y, z: 5.55, rot: 2 }, 2.6, ['status', 'telemetry'], 45);
  P.consoleUnit(k, { x: 10.3, y, z: -5.55, rot: 0 }, 2.6, ['comms', 'orbit'], 47);
  P.chair(k, { x: 10.3, y, z: 4.6, rot: 2 }, 'Engineering station');
  P.chair(k, { x: 10.3, y, z: -4.6, rot: 0 }, 'Science station');
  k.graphic('BRIDGE · FLIGHT DECK', V(8.11, y + 1.85, 3.6), Math.PI / 2, 1.8, 0.27, { fg: '#e8e3d6' });
  void accentDeck;
  return P.holoTable(k, { x: 11.0, y, z: 0 });
}
