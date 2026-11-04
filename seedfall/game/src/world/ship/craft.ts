import * as THREE from 'three';
import { Kit } from './kit';
import { Place } from './builder';
import { L, faceYaw } from './props';

/** Geometry placer in a craft's local frame (nose = local +z). */
function placer(k: Kit, p: Place) {
  const yaw = faceYaw(p);
  const place = new THREE.Matrix4().makeRotationY(yaw).setPosition(p.x, p.y, p.z);
  const local = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const one = new THREE.Vector3(1, 1, 1);
  return (g: THREE.BufferGeometry, key: string, pos: THREE.Vector3, rot = new THREE.Euler(), pre?: THREE.Matrix4) => {
    q.setFromEuler(rot);
    local.compose(pos, q, one);
    const m = new THREE.Matrix4().multiplyMatrices(place, local);
    if (pre) m.multiply(pre);
    k.b.add(g, key, m);
  };
}

function solid(k: Kit, p: Place, x0: number, y0: number, z0: number, x1: number, y1: number, z1: number): void {
  const a = L(p, x0, y0, z0);
  const b = L(p, x1, y1, z1);
  k.world.add(Math.min(a.x, b.x), a.y, Math.min(a.z, b.z), Math.max(a.x, b.x), b.y, Math.max(a.z, b.z));
}

/** LND-01 Kestrel: 22 m dropship on its cradle. */
export function buildKestrel(k: Kit, p: Place): void {
  const put = placer(k, p);
  const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
  // fuselage from a side profile (X = length, Y = height), extruded across the width
  const prof = new THREE.Shape();
  const pts: [number, number][] = [
    [-11, 1.6], [-10.7, 4.9], [-4, 5.5], [3.5, 5.3], [7.5, 4.6], [10.2, 3.3], [11, 2.5], [10.4, 1.75], [6, 1.3], [-8, 1.25],
  ];
  prof.moveTo(pts[0][0], pts[0][1]);
  for (const [x, y] of pts.slice(1)) prof.lineTo(x, y);
  prof.closePath();
  const body = new THREE.ExtrudeGeometry(prof, { depth: 4.0, bevelEnabled: true, bevelThickness: 0.4, bevelSize: 0.35, bevelSegments: 4, curveSegments: 4 });
  // shape X → local z, shape Y → local y, extrusion Z → local x (centred)
  const remap = new THREE.Matrix4().set(0, 0, 1, -2.0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1);
  // that matrix maps (X,Y,Z) → (Z-2, Y, X): det = -1, so flip winding by mirroring Z first
  const mirror = new THREE.Matrix4().makeScale(1, 1, -1).setPosition(0, 0, 4.0);
  put(body, 'hullExt', V(0, 0, 0), new THREE.Euler(), remap.multiply(mirror));
  // cockpit glazing
  put(new THREE.BoxGeometry(3.6, 0.08, 3.05), 'blackGlass', V(0, 4.05, 8.85), new THREE.Euler(0.448, 0, 0));
  for (const s of [-1, 1]) {
    put(new THREE.BoxGeometry(0.06, 0.45, 2.6), 'blackGlass', V(s * 2.42, 4.05, 5.6), new THREE.Euler(0, 0, 0));
    put(new THREE.BoxGeometry(0.05, 0.22, 19), 'accent-spine', V(s * 2.42, 2.75, -0.5));
    put(new THREE.BoxGeometry(0.05, 0.05, 19), 'paintDark', V(s * 2.42, 2.5, -0.5));
  }
  // wings (shape X = local z, shape Y = local x, extrusion = local y)
  for (const s of [-1, 1]) {
    const w = new THREE.Shape();
    const wp: [number, number][] = [[-9, 2.2 * s], [-2, 2.2 * s], [-6.4, 7.0 * s], [-9.6, 7.0 * s]];
    w.moveTo(wp[0][0], wp[0][1]);
    for (const [a, b] of wp.slice(1)) w.lineTo(a, b);
    w.closePath();
    const wing = new THREE.ExtrudeGeometry(w, { depth: 0.32, bevelEnabled: true, bevelThickness: 0.06, bevelSize: 0.06, bevelSegments: 2 });
    const perm = new THREE.Matrix4().set(0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1);
    put(wing, 'hullExt', V(0, 2.25, 0), new THREE.Euler(), perm);
    // nacelle
    const nac = new THREE.CylinderGeometry(0.85, 0.85, 5.6, 24);
    put(nac, 'hullDark', V(s * 7.2, 2.45, -7.6), new THREE.Euler(Math.PI / 2, 0, 0));
    put(new THREE.CylinderGeometry(0.62, 0.8, 0.5, 24, 1, true), 'metal', V(s * 7.2, 2.45, -10.6), new THREE.Euler(Math.PI / 2, 0, 0));
    put(new THREE.CircleGeometry(0.6, 24), 'paintDark', V(s * 7.2, 2.45, -10.5), new THREE.Euler(0, Math.PI, 0));
    put(new THREE.SphereGeometry(0.85, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), 'hullDark', V(s * 7.2, 2.45, -4.8), new THREE.Euler(Math.PI / 2, 0, 0));
    // tail fin
    put(new THREE.BoxGeometry(0.18, 2.4, 3.2), 'hullExt', V(s * 1.5, 6.3, -8.6), new THREE.Euler(-0.35, 0, s * 0.3));
  }
  // main engines
  for (const s of [-1, 1]) {
    put(new THREE.CylinderGeometry(0.75, 0.9, 0.9, 24, 1, true), 'metal', V(s * 1.2, 3.2, -11.5), new THREE.Euler(Math.PI / 2, 0, 0));
    put(new THREE.CircleGeometry(0.72, 24), 'paintDark', V(s * 1.2, 3.2, -11.3), new THREE.Euler(0, Math.PI, 0));
  }
  // landing gear
  const gear: [number, number][] = [[0, 8], [-1.8, -6], [1.8, -6]];
  for (const [gx, gz] of gear) {
    k.b.cyl(L(p, gx, 0.2, gz), L(p, gx, 1.4, gz), 0.13, 'steel');
    k.b.cyl(L(p, gx, 0.6, gz), L(p, gx, 1.35, gz + 0.6), 0.07, 'metal');
    k.b.pbox(p, gx - 0.45, 0, gz - 0.45, gx + 0.45, 0.2, gz + 0.45, 'paintDark', false, 0.04);
  }
  // cradle
  k.b.pbox(p, -3.2, 0, -9, -2.6, 0.5, 9, 'accent-aft', false, 0.03);
  k.b.pbox(p, 2.6, 0, -9, 3.2, 0.5, 9, 'accent-aft', false, 0.03);
  // ramp outline
  put(new THREE.BoxGeometry(3.0, 0.05, 0.05), 'paintDark', V(0, 4.2, -11.4));
  for (const s of [-1, 1]) {
    k.stencil('KESTREL', 'aft', L(p, s * 2.47, 4.5, 0.5), faceYaw(p, s, 0), 0.55, 30 + s);
  }
  k.stencil('LND-01', 'aft', L(p, 2.47, 3.4, -6.5), faceYaw(p, 1, 0), 0.32, 33);
  solid(k, p, -2.6, 0, -11.6, 2.6, 5.6, 11.1);
  for (const s of [-1, 1]) solid(k, p, s * 7.2 - 0.9, 0, -10.8, s * 7.2 + 0.9, 3.3, -4.0);
  k.pitem(p, -2.2, 0, -12.6, 2.2, 3.6, -11.0, 'Board the Kestrel', 'kestrel', undefined, 3.0);
  k.pitem(p, 2.5, 1.0, 6.0, 3.6, 3.0, 9.5, 'Kestrel · pre-flight status', 'kestrel', undefined, 3.0);
}

/** CL-01 Mule: heavy cargo lifter with a crane. */
export function buildMule(k: Kit, p: Place): void {
  const put = placer(k, p);
  const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
  k.b.pbox(p, -3, 1.6, -6.5, 3, 2.25, 6, 'hullDark', false, 0.1);
  k.b.pbox(p, -3.02, 2.25, -6.5, 3.02, 2.28, -6.1, 'hazard', false);
  k.b.pbox(p, -3.02, 2.25, -6.5, -2.7, 2.28, 6, 'hazard', false);
  k.b.pbox(p, 2.7, 2.25, -6.5, 3.02, 2.28, 6, 'hazard', false);
  k.b.pbox(p, -1.5, 2.25, 4.4, 1.5, 4.7, 7.1, 'hullExt', false, 0.3);
  put(new THREE.BoxGeometry(2.6, 0.06, 1.3), 'blackGlass', V(0, 4.1, 7.0), new THREE.Euler(0.6, 0, 0));
  for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]] as const) {
    const c = V(sx * 3.75, 2.2, sz * 4.6);
    put(new THREE.CylinderGeometry(0.9, 0.9, 2.4, 24), 'hullExt', c);
    put(new THREE.CylinderGeometry(0.7, 0.85, 0.4, 24, 1, true), 'metal', V(c.x, 0.85, c.z));
    k.b.pbox(p, Math.min(sx * 2.9, sx * 3.0), 1.9, sz * 4.6 - 0.3, Math.max(sx * 2.9, sx * 3.0) + (sx > 0 ? 0 : 0), 2.1, sz * 4.6 + 0.3, 'metal', false);
    k.b.cyl(L(p, sx * 2.6, 0, sz * 3.2), L(p, sx * 2.6, 1.6, sz * 3.2), 0.12, 'steel');
  }
  // crane
  k.b.cyl(L(p, 0, 2.25, -4.6), L(p, 0, 3.0, -4.6), 0.45, 'accent-aft', 20);
  put(new THREE.BoxGeometry(0.45, 0.45, 6.5), 'accent-aft', V(0, 4.2, -2.0), new THREE.Euler(-0.38, 0, 0));
  k.b.cyl(L(p, 0, 5.4, 1.0), L(p, 0, 3.0, 1.0), 0.02, 'steel', 6);
  k.b.pbox(p, -0.25, 2.75, 0.75, 0.25, 3.0, 1.25, 'paintDark', false, 0.03);
  for (const s of [-1, 1]) k.stencil('MULE · CL-01', 'aft', L(p, s * 1.51, 3.6, 5.6), faceYaw(p, s, 0), 0.32, 40 + s);
  solid(k, p, -4.7, 0, -7.0, 4.7, 4.7, 7.2);
  k.pitem(p, -3.2, 1.0, -7.2, 3.2, 3.5, 7.4, 'Mule · heavy cargo lifter', 'mule', undefined, 3.2);
}
