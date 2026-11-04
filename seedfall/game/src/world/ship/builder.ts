import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { Materials } from './materials';
import { CollisionWorld } from '../collision';

const _m = new THREE.Matrix4();
const _q = new THREE.Quaternion();
const _s = new THREE.Vector3();
const _p = new THREE.Vector3();

export type Collide = false | 'solid' | 'wall';

/** Rotation in quarter turns around Y, applied around the placement origin. */
export interface Place {
  x: number;
  y: number;
  z: number;
  rot?: number; // quarter turns (0..3), counter-clockwise seen from above
}

/** Rotate a local (x,z) by quarter turns. */
export function rotXZ(x: number, z: number, rot = 0): [number, number] {
  switch (((rot % 4) + 4) % 4) {
    case 1:
      return [z, -x];
    case 2:
      return [-x, -z];
    case 3:
      return [-z, x];
    default:
      return [x, z];
  }
}

/** Accumulates static geometry per material, then merges into a handful of meshes. */
export class Builder {
  private buckets = new Map<string, THREE.BufferGeometry[]>();

  constructor(public mats: Materials, public world: CollisionWorld) {}

  add(geom: THREE.BufferGeometry, key: string, matrix?: THREE.Matrix4): void {
    const g = geom.index ? geom.toNonIndexed() : geom.clone();
    if (matrix) g.applyMatrix4(matrix);
    for (const name of Object.keys(g.attributes)) {
      if (!['position', 'normal', 'uv'].includes(name)) g.deleteAttribute(name);
    }
    if (!g.attributes.uv) {
      g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
    }
    const def = this.mats.get(key);
    if (def.tileU > 0) worldUV(g, def.tileU, def.tileV);
    let list = this.buckets.get(key);
    if (!list) {
      list = [];
      this.buckets.set(key, list);
    }
    list.push(g);
  }

  /** World-space box from min/max corners. */
  box(x0: number, y0: number, z0: number, x1: number, y1: number, z1: number, key: string, collide: Collide = 'solid', round = 0): void {
    const w = Math.abs(x1 - x0);
    const h = Math.abs(y1 - y0);
    const d = Math.abs(z1 - z0);
    if (w < 1e-4 || h < 1e-4 || d < 1e-4) return;
    const r = Math.min(round, w / 2 - 1e-3, h / 2 - 1e-3, d / 2 - 1e-3);
    const g = r > 0.004 ? new RoundedBoxGeometry(w, h, d, 2, r) : new THREE.BoxGeometry(w, h, d);
    _m.makeTranslation((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
    this.add(g, key, _m);
    if (collide) this.world.add(x0, y0, z0, x1, y1, z1, collide);
  }

  /** Box in local coordinates of a placement (quarter-turn rotation). */
  pbox(p: Place, x0: number, y0: number, z0: number, x1: number, y1: number, z1: number, key: string, collide: Collide = 'solid', round = 0): void {
    const [ax, az] = rotXZ(x0, z0, p.rot);
    const [bx, bz] = rotXZ(x1, z1, p.rot);
    this.box(p.x + Math.min(ax, bx), p.y + y0, p.z + Math.min(az, bz), p.x + Math.max(ax, bx), p.y + y1, p.z + Math.max(az, bz), key, collide, round);
  }

  /** Arbitrary geometry placed with position/euler/scale (no collision). */
  geo(g: THREE.BufferGeometry, key: string, pos: THREE.Vector3Like, rot: THREE.Euler = new THREE.Euler(), scale = 1): void {
    _q.setFromEuler(rot);
    _s.set(scale, scale, scale);
    _p.set(pos.x, pos.y, pos.z);
    _m.compose(_p, _q, _s);
    this.add(g, key, _m);
  }

  /** Cylinder between two points. */
  cyl(a: THREE.Vector3, b: THREE.Vector3, radius: number, key: string, seg = 12): void {
    const dir = new THREE.Vector3().subVectors(b, a);
    const len = dir.length();
    const g = new THREE.CylinderGeometry(radius, radius, len, seg, 1);
    _q.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    _p.addVectors(a, b).multiplyScalar(0.5);
    _m.compose(_p, _q, _s.set(1, 1, 1));
    this.add(g, key, _m);
  }

  /** Merge buckets into meshes and add them to the right scene. */
  build(interior: THREE.Object3D, over: THREE.Object3D): THREE.Mesh[] {
    const meshes: THREE.Mesh[] = [];
    for (const [key, list] of this.buckets) {
      const def = this.mats.get(key);
      // merge in chunks to keep index ranges sane
      const merged = mergeGeometries(list, false);
      if (!merged) continue;
      merged.computeBoundingSphere();
      const mesh = new THREE.Mesh(merged, def.mat);
      mesh.name = `ship:${key}`;
      mesh.castShadow = def.cast;
      mesh.receiveShadow = def.receive;
      mesh.matrixAutoUpdate = false;
      mesh.updateMatrix();
      if ((def.mat as THREE.MeshStandardMaterial).transparent) mesh.renderOrder = 2;
      (def.pass === 'over' ? over : interior).add(mesh);
      meshes.push(mesh);
    }
    this.buckets.clear();
    return meshes;
  }
}

/** Box-projected UVs from world positions, so texel density is constant everywhere. */
function worldUV(g: THREE.BufferGeometry, tu: number, tv: number): void {
  const pos = g.attributes.position as THREE.BufferAttribute;
  const nor = g.attributes.normal as THREE.BufferAttribute;
  const uv = g.attributes.uv as THREE.BufferAttribute;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    const nx = nor.getX(i);
    const ny = nor.getY(i);
    const nz = nor.getZ(i);
    const ax = Math.abs(nx);
    const ay = Math.abs(ny);
    const az = Math.abs(nz);
    let u: number;
    let v: number;
    if (ax >= ay && ax >= az) {
      u = (nx > 0 ? -z : z) / tu;
      v = y / tv;
    } else if (ay >= az) {
      u = x / tu;
      v = (ny > 0 ? -z : z) / tv;
    } else {
      u = (nz > 0 ? x : -x) / tu;
      v = y / tv;
    }
    uv.setXY(i, u, v);
  }
  uv.needsUpdate = true;
}
