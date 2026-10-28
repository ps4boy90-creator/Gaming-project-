// Batches thousands of cables into one vertex-coloured tube mesh.
import * as THREE from 'three';

class Grow {
  constructor(Type, n = 1 << 16) { this.Type = Type; this.a = new Type(n); this.n = 0; }
  push3(x, y, z) {
    if (this.n + 3 > this.a.length) { const b = new this.Type(this.a.length * 2); b.set(this.a); this.a = b; }
    this.a[this.n++] = x; this.a[this.n++] = y; this.a[this.n++] = z;
  }
  view() { return this.a.subarray(0, this.n); }
}

const _t = new THREE.Vector3(), _n = new THREE.Vector3(), _b = new THREE.Vector3(), _tmp = new THREE.Vector3();
const _col = new THREE.Color();

export class CableBatch {
  constructor() {
    this.pos = new Grow(Float32Array);
    this.nrm = new Grow(Float32Array);
    this.col = new Grow(Float32Array);
    this.idx = new Grow(Uint32Array);
    this.verts = 0;
    this.count = 0;
  }

  // points: Vector3[] in world space; radius in metres; color: hex/string
  add(points, radius, color, { radial = 5, segLen = 0.03, maxSegs = 64 } = {}) {
    const curve = new THREE.CatmullRomCurve3(points, false, 'centripetal');
    const len = curve.getLength();
    const segs = Math.max(4, Math.min(maxSegs, Math.ceil(len / segLen)));
    const pts = curve.getSpacedPoints(segs);
    _col.set(color);
    const base = this.verts;
    // parallel-transport frames
    _t.subVectors(pts[1], pts[0]).normalize();
    _n.set(0, 1, 0);
    if (Math.abs(_t.y) > 0.9) _n.set(1, 0, 0);
    _n.sub(_tmp.copy(_t).multiplyScalar(_n.dot(_t))).normalize();
    for (let i = 0; i <= segs; i++) {
      const p = pts[i];
      const a = pts[Math.max(0, i - 1)], c = pts[Math.min(segs, i + 1)];
      _t.subVectors(c, a).normalize();
      _n.sub(_tmp.copy(_t).multiplyScalar(_n.dot(_t))).normalize();
      _b.crossVectors(_t, _n);
      for (let k = 0; k < radial; k++) {
        const ang = (k / radial) * Math.PI * 2;
        const cs = Math.cos(ang), sn = Math.sin(ang);
        const nx = _n.x * cs + _b.x * sn, ny = _n.y * cs + _b.y * sn, nz = _n.z * cs + _b.z * sn;
        this.pos.push3(p.x + nx * radius, p.y + ny * radius, p.z + nz * radius);
        this.nrm.push3(nx, ny, nz);
        this.col.push3(_col.r, _col.g, _col.b);
      }
    }
    for (let i = 0; i < segs; i++) {
      for (let k = 0; k < radial; k++) {
        const a = base + i * radial + k;
        const b = base + i * radial + ((k + 1) % radial);
        const c = a + radial, d = b + radial;
        this.idx.push3(a, c, b);
        this.idx.push3(b, c, d);
      }
    }
    this.verts += (segs + 1) * radial;
    this.count++;
  }

  build(material) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.pos.view().slice(), 3));
    g.setAttribute('normal', new THREE.BufferAttribute(this.nrm.view().slice(), 3));
    g.setAttribute('color', new THREE.BufferAttribute(this.col.view().slice(), 3));
    g.setIndex(new THREE.BufferAttribute(this.idx.view().slice(), 1));
    g.computeBoundingSphere();
    const mesh = new THREE.Mesh(g, material);
    mesh.matrixAutoUpdate = false;
    return mesh;
  }
}

export const CABLE = {
  blue: '#2457b8',
  yellow: '#d9b51e',
  red: '#b3262a',
  green: '#2f8a45',
  grey: '#8c9096',
  white: '#d8d8d2',
  black: '#141414',
  aqua: '#2fb3b8',
  orange: '#d66a1f',
  purple: '#6a3fa0',
  powerA: '#161616',
  powerB: '#5d6168',
};
