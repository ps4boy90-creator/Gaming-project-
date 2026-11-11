import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

/**
 * A model is plain merged geometry with per-vertex colours so that every
 * object type renders as a single instanced draw call.
 *  - solid: lit geometry (MeshStandardMaterial, vertexColors)
 *  - glow:  optional unlit emissive geometry (screens, lamps) drawn additively bright
 */
export interface ModelResult {
  solid: THREE.BufferGeometry;
  glow?: THREE.BufferGeometry;
}

export interface PartOpts {
  /** Euler rotation (radians) applied about the part's own centre. */
  rx?: number;
  ry?: number;
  rz?: number;
  /** Put this part into the emissive (unlit) geometry instead of the lit one. */
  glow?: boolean;
}

const _c = new THREE.Color();
const _m = new THREE.Matrix4();
const _q = new THREE.Quaternion();
const _e = new THREE.Euler();
const _p = new THREE.Vector3();
const _s = new THREE.Vector3(1, 1, 1);

/**
 * ModelBuilder. Units: 1 = one floor tile. +Y is up. A model is centred on its
 * footprint in X/Z with the floor at y = 0, and its "front" faces +Z.
 *
 * For every primitive, (x, y, z) is the centre of the part's BOTTOM face
 * (before rotation); the part extends upwards by its height. Rotation is applied
 * about the part's centre.
 */
export class MB {
  private solid: THREE.BufferGeometry[] = [];
  private glowParts: THREE.BufferGeometry[] = [];

  private push(g: THREE.BufferGeometry, h: number, x: number, y: number, z: number, color: number, o?: PartOpts) {
    if (g.index === null) {
      // keep everything indexed for mergeGeometries
      const n = g.attributes.position.count;
      const idx = new Uint32Array(n);
      for (let i = 0; i < n; i++) idx[i] = i;
      g.setIndex(new THREE.BufferAttribute(idx, 1));
    }
    g.deleteAttribute('uv');
    if (g.attributes.uv1) g.deleteAttribute('uv1');
    _e.set(o?.rx ?? 0, o?.ry ?? 0, o?.rz ?? 0);
    _q.setFromEuler(_e);
    _p.set(x, y + h / 2, z);
    _m.compose(_p, _q, _s);
    g.applyMatrix4(_m);
    _c.setHex(color, THREE.SRGBColorSpace);
    const n = g.attributes.position.count;
    const col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      col[i * 3] = _c.r;
      col[i * 3 + 1] = _c.g;
      col[i * 3 + 2] = _c.b;
    }
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    (o?.glow ? this.glowParts : this.solid).push(g);
    return this;
  }

  /** Sharp-edged box. */
  box(w: number, h: number, d: number, x: number, y: number, z: number, color: number, o?: PartOpts) {
    return this.push(new THREE.BoxGeometry(w, h, d), h, x, y, z, color, o);
  }

  /** Box with rounded edges (radius r). Nicer for furniture, a bit heavier. */
  rbox(w: number, h: number, d: number, x: number, y: number, z: number, color: number, r = 0.03, o?: PartOpts) {
    const rr = Math.min(r, w / 2 - 0.001, h / 2 - 0.001, d / 2 - 0.001);
    return this.push(new RoundedBoxGeometry(w, h, d, 2, Math.max(0.002, rr)), h, x, y, z, color, o);
  }

  /** Cylinder / cone frustum standing on the Y axis. */
  cyl(rTop: number, rBot: number, h: number, x: number, y: number, z: number, color: number, seg = 12, o?: PartOpts) {
    return this.push(new THREE.CylinderGeometry(rTop, rBot, h, seg), h, x, y, z, color, o);
  }

  /** Cone (point up). */
  cone(r: number, h: number, x: number, y: number, z: number, color: number, seg = 10, o?: PartOpts) {
    return this.push(new THREE.ConeGeometry(r, h, seg), h, x, y, z, color, o);
  }

  /** Sphere of radius r, optionally squashed/stretched (sx, sy, sz). (x,y,z) = bottom centre. */
  sphere(r: number, x: number, y: number, z: number, color: number, sx = 1, sy = 1, sz = 1, seg = 12, o?: PartOpts) {
    const g = new THREE.SphereGeometry(r, seg, Math.max(6, Math.round(seg * 0.7)));
    g.scale(sx, sy, sz);
    return this.push(g, 2 * r * sy, x, y, z, color, o);
  }

  /** Low-poly faceted blob (icosahedron), good for foliage and rocks. */
  blob(r: number, x: number, y: number, z: number, color: number, sx = 1, sy = 1, sz = 1, detail = 1, o?: PartOpts) {
    const g = new THREE.IcosahedronGeometry(r, detail);
    g.scale(sx, sy, sz);
    return this.push(g, 2 * r * sy, x, y, z, color, o);
  }

  /** Torus (ring). Lies flat in the XZ plane by default. */
  torus(r: number, tube: number, x: number, y: number, z: number, color: number, seg = 16, o?: PartOpts) {
    const g = new THREE.TorusGeometry(r, tube, 6, seg);
    g.rotateX(Math.PI / 2);
    return this.push(g, tube * 2, x, y, z, color, o);
  }

  build(): ModelResult {
    const solid = this.solid.length
      ? mergeGeometries(this.solid, false)!
      : new THREE.BufferGeometry();
    solid.computeBoundingBox();
    solid.computeBoundingSphere();
    const res: ModelResult = { solid };
    if (this.glowParts.length) {
      res.glow = mergeGeometries(this.glowParts, false)!;
      res.glow.computeBoundingSphere();
    }
    for (const g of this.solid) g.dispose();
    for (const g of this.glowParts) g.dispose();
    return res;
  }
}
