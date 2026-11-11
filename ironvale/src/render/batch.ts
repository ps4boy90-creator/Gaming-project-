import * as THREE from 'three';

const _m = new THREE.Matrix4();
const _q = new THREE.Quaternion();
const _p = new THREE.Vector3();
const _s = new THREE.Vector3();
const _up = new THREE.Vector3(0, 1, 0);
const _white = new THREE.Color(1, 1, 1);

export interface BatchOpts {
  cast?: boolean;
  receive?: boolean;
  noAO?: boolean;
  cap?: number;
  /** name of an extra per-instance float attribute */
  extra?: string;
  renderOrder?: number;
  colors?: boolean;
}

/** A growable InstancedMesh that is refilled with begin() / add() / end(). */
export class Batch {
  mesh!: THREE.InstancedMesh;
  n = 0;
  private cap: number;
  private extraArr: Float32Array | null = null;

  constructor(private geo: THREE.BufferGeometry, private mat: THREE.Material, private parent: THREE.Object3D, private opts: BatchOpts = {}) {
    this.cap = opts.cap ?? 64;
    if (opts.extra) this.geo = geo.clone();
    this.alloc();
  }

  private alloc(old?: THREE.InstancedMesh) {
    const mesh = new THREE.InstancedMesh(this.geo, this.mat, this.cap);
    mesh.castShadow = !!this.opts.cast;
    mesh.receiveShadow = !!this.opts.receive;
    mesh.frustumCulled = false;
    if (this.opts.noAO) mesh.userData.noAO = true;
    if (this.opts.renderOrder !== undefined) mesh.renderOrder = this.opts.renderOrder;
    if (this.opts.colors !== false) {
      mesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(this.cap * 3).fill(1), 3);
    }
    if (this.opts.extra) {
      const arr = new Float32Array(this.cap);
      if (this.extraArr) arr.set(this.extraArr);
      this.extraArr = arr;
      this.geo.setAttribute(this.opts.extra, new THREE.InstancedBufferAttribute(arr, 1));
    }
    if (old) {
      (mesh.instanceMatrix.array as Float32Array).set(old.instanceMatrix.array as Float32Array);
      if (old.instanceColor && mesh.instanceColor) (mesh.instanceColor.array as Float32Array).set(old.instanceColor.array as Float32Array);
      mesh.visible = old.visible;
      this.parent.remove(old);
      old.dispose();
    }
    mesh.count = this.n;
    this.parent.add(mesh);
    this.mesh = mesh;
  }

  begin() {
    this.n = 0;
  }

  /** add an instance from a matrix */
  addM(m: THREE.Matrix4, color?: THREE.Color, extra = 0): number {
    if (this.n >= this.cap) {
      this.cap *= 2;
      this.alloc(this.mesh);
    }
    const i = this.n++;
    this.mesh.setMatrixAt(i, m);
    if (this.mesh.instanceColor) this.mesh.setColorAt(i, color ?? _white);
    if (this.extraArr) this.extraArr[i] = extra;
    return i;
  }

  /** add an instance from position / scale / yaw */
  add(x: number, y: number, z: number, sx: number, sy: number, sz: number, yaw = 0, color?: THREE.Color, extra = 0): number {
    _q.setFromAxisAngle(_up, yaw);
    _p.set(x, y, z);
    _s.set(sx, sy, sz);
    _m.compose(_p, _q, _s);
    return this.addM(_m, color, extra);
  }

  setMatrix(i: number, m: THREE.Matrix4) {
    this.mesh.setMatrixAt(i, m);
    this.mesh.instanceMatrix.needsUpdate = true;
  }

  end() {
    this.mesh.count = this.n;
    this.mesh.instanceMatrix.needsUpdate = true;
    if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;
    if (this.opts.extra) (this.geo.getAttribute(this.opts.extra) as THREE.BufferAttribute).needsUpdate = true;
  }

  set visible(v: boolean) {
    this.mesh.visible = v;
  }
}
