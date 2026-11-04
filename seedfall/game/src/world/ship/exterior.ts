import * as THREE from 'three';
import { Builder } from './builder';

/** Outside the hull: collector sails, masts, spine trusses and the drive section. */
export function buildExterior(b: Builder): void {
  const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
  // collector sails: two golden wings rising from the stern, the port one torn by the flare
  for (const side of [1, -1]) {
    const torn = side < 0;
    const tip = sail(b, side, torn);
    b.box(-292, 1.2, side > 0 ? 14 : -32, -108, 2.8, side > 0 ? 32 : -14, 'hullDark', false);
    b.cyl(V(-200, 2, side * 30), tip, 1.1, 'hullDark');
    b.cyl(V(-200, 2, side * 12), V(-200, 2, side * 30), 1.6, 'hullDark');
    b.cyl(V(-140, 2, side * 12), V(-140, 2, side * 30), 1.2, 'hullDark');
    b.cyl(V(-260, 2, side * 12), V(-260, 2, side * 30), 1.2, 'hullDark');
  }
  // spine trusses top and bottom
  b.box(-112, 3.3, -1.3, -18, 3.85, 1.3, 'hullDark', false);
  b.box(-112, -0.95, -1.3, -18, -0.3, 1.3, 'hullDark', false);
  for (let x = -110; x <= -20; x += 6) {
    b.box(x - 0.25, 3.25, -2.3, x + 0.25, 4.0, 2.3, 'hullExt', false);
    b.box(x - 0.25, -1.0, -2.3, x + 0.25, -0.25, 2.3, 'hullExt', false);
  }
  // habitat roof clutter
  b.cyl(V(-11, 11.3, -5), V(-11, 13.6, -5), 0.25, 'hullDark');
  b.geo(new THREE.SphereGeometry(2.6, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2.6), 'hullExt', V(-11, 13.2, -5), new THREE.Euler(Math.PI, 0, 0.5));
  b.box(-17.5, 11.25, -8.5, -14.5, 11.6, 8.5, 'hullDark', false);
  // drive section
  b.geo(new THREE.CylinderGeometry(15, 15, 90, 48, 1), 'hullDark', V(-160, 2, 0), new THREE.Euler(0, 0, Math.PI / 2));
  b.geo(new THREE.CylinderGeometry(17, 17, 6, 48, 1), 'hullExt', V(-118, 2, 0), new THREE.Euler(0, 0, Math.PI / 2));
  b.geo(new THREE.CylinderGeometry(11, 15, 8, 48, 1, true), 'hullExt', V(-209, 2, 0), new THREE.Euler(0, 0, Math.PI / 2));
  b.geo(new THREE.CircleGeometry(10.5, 48), 'engineGlow', V(-206, 2, 0), new THREE.Euler(0, -Math.PI / 2, 0));
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2;
    b.box(-200, 2 + Math.sin(a) * 16 - 0.5, Math.cos(a) * 16 - 0.5, -120, 2 + Math.sin(a) * 16 + 0.5, Math.cos(a) * 16 + 0.5, 'hullExt', false);
  }
}

const DIHEDRAL = THREE.MathUtils.degToRad(28);
const SAIL_LEN = 180; // along the ship
const SAIL_SPAN = 600; // outward

/** One collector sail: billowed film hinged at the stern, raised at a dihedral. Returns the tip. */
function sail(b: Builder, side: number, torn: boolean): THREE.Vector3 {
  const g = new THREE.PlaneGeometry(SAIL_LEN, SAIL_SPAN, 16, 48).toNonIndexed();
  const pos = g.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < pos.count; i++) {
    const u = pos.getX(i) / SAIL_LEN + 0.5;
    const v = pos.getY(i) / SAIL_SPAN + 0.5;
    pos.setZ(i, Math.sin(u * Math.PI) * Math.sin(v * Math.PI) * 9);
  }
  let geom: THREE.BufferGeometry = g;
  if (torn) {
    const keep: number[] = [];
    const p = pos.array as Float32Array;
    for (let t = 0; t < pos.count; t += 3) {
      const cu = (p[t * 3] + p[t * 3 + 3] + p[t * 3 + 6]) / 3 / SAIL_LEN + 0.5;
      const cv = (p[t * 3 + 1] + p[t * 3 + 4] + p[t * 3 + 7]) / 3 / SAIL_SPAN + 0.5;
      const n = Math.sin(cv * 41.0) * 0.05 + Math.sin(cu * 23.0 + cv * 17.0) * 0.06;
      const hole = Math.hypot((cu - 0.45) * 0.7, cv - 0.55) < 0.17 + n;
      const edge = cv > 0.82 + n * 1.5;
      if (!hole && !edge) keep.push(t);
    }
    const out = new Float32Array(keep.length * 9);
    keep.forEach((t, i) => out.set(p.subarray(t * 3, t * 3 + 9), i * 9));
    geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(out, 3));
  }
  // local: X along ship, Y outward, Z = billow → world: X, outward = ±z, billow = up
  const m = new THREE.Matrix4()
    .makeTranslation(-200, 2, side * 30)
    .multiply(new THREE.Matrix4().makeRotationX(-side * DIHEDRAL))
    .multiply(new THREE.Matrix4().makeTranslation(0, 0, side * SAIL_SPAN / 2))
    .multiply(new THREE.Matrix4().makeRotationX(-Math.PI / 2));
  if (side < 0) m.multiply(new THREE.Matrix4().makeScale(1, -1, 1));
  geom.computeVertexNormals();
  b.add(geom, 'sail', m);
  return new THREE.Vector3(-200, 2 + Math.sin(DIHEDRAL) * SAIL_SPAN * 0.98, side * (30 + Math.cos(DIHEDRAL) * SAIL_SPAN * 0.98));
}
