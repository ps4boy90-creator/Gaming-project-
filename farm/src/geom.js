/**
 * Mesh builder: everything in the scene is boxes, quads, triangles and
 * cylinders pushed into one interleaved vertex array, drawn in one call.
 *
 * The look this is after puts all its detail in textures and lighting and
 * almost none in geometry -- boxy forms, hard edges, no bevels -- so the
 * builder is deliberately primitive. What it does do carefully is texture
 * mapping: every face gets UVs from its own plane in *metres*, with U running
 * horizontally and V running up the slope. That keeps texel density constant
 * across the whole farm (a clapboard is the same height on the house as on the
 * porch gable) without anybody having to unwrap anything.
 *
 * Vertex layout, 16 floats:
 *   position 3 | normal 3 | uv 2 | texture layer 1 | tint 3 |
 *   sky occlusion 1 | emission 1 | wind sway 1 | kind 1
 * `kind`: 0 solid, 1 ground (blends grass into dirt tracks), 2 foliage card.
 */
import { IDENT, mul, xformPoint, xformDir, cross, sub, normalize, dot, chain, translate, rotY, rotZ } from './math.js';

export const STRIDE = 16;
export const KIND = { SOLID: 0, GROUND: 1, FOLIAGE: 2 };

const pick = (v, i, d) => (v === undefined ? d : Array.isArray(v) ? v[i] : v);

/** A square-section stick between two points: rails, wires, braces, trim. */
export function stick(m, a, b, w, h, o) {
  const dx = b[0] - a[0], dy = b[1] - a[1], dz = b[2] - a[2];
  const flat = Math.hypot(dx, dz), len = Math.hypot(flat, dy);
  m.at(chain(
    translate((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2),
    rotY(Math.atan2(-dz, dx)), rotZ(Math.atan2(dy, flat)),
  ), () => m.box(0, 0, 0, len, h, w, o));
}

export class Mesh {
  constructor(tiles) {
    this.data = [];
    this.count = 0;
    this.stack = [IDENT];
    /** metres covered by one repeat of each texture layer */
    this.tiles = tiles;
  }
  get m() { return this.stack[this.stack.length - 1]; }
  push(m) { this.stack.push(mul(this.m, m)); return this; }
  pop() { this.stack.pop(); return this; }
  /** Run `fn` with a transform pushed, so nesting reads like the object does. */
  at(m, fn) { this.push(m); fn(); this.pop(); }

  _vert(p, n, u, v, o, i) {
    const w = xformPoint(this.m, p);
    const c = o.col || [1, 1, 1];
    this.data.push(
      w[0], w[1], w[2], n[0], n[1], n[2], u, v, o.layer || 0, c[0], c[1], c[2],
      pick(o.occ, i, 1), o.emit || 0, pick(o.sway, i, 0), o.kind || 0,
    );
    this.count++;
  }

  /** Plane-space UV axes: U horizontal, V up the slope. Flat faces use X / -Z. */
  _basis(n) {
    if (Math.abs(n[1]) > 0.999) return [[1, 0, 0], [0, 0, -Math.sign(n[1]) || -1]];
    const u = normalize(cross([0, 1, 0], n));
    return [u, cross(n, u)];
  }

  _poly(pts, o, fitUV) {
    const nLocal = normalize(cross(sub(pts[1], pts[0]), sub(pts[pts.length - 1], pts[0])));
    const n = o.normal || normalize(xformDir(this.m, nLocal));
    let uvs;
    if (fitUV) {
      uvs = fitUV;
    } else {
      const [ua, va] = this._basis(nLocal);
      const t = 1 / (o.tile || this.tiles[o.layer || 0] || 1);
      const off = o.uvOff || [0, 0];
      uvs = pts.map((p) => {
        const u = dot(p, ua) * t + off[0], v = dot(p, va) * t + off[1];
        return o.uvRot ? [v, u] : [u, v];
      });
    }
    for (let i = 1; i < pts.length - 1; i++) {
      for (const k of [0, i, i + 1]) this._vert(pts[k], n, uvs[k][0], uvs[k][1], o, k);
    }
  }

  /** Counter-clockwise seen from the front. `fit` stretches the texture once across it. */
  quad(a, b, c, d, o = {}) {
    let fit = null;
    if (o.fit) {
      const [u0, v0, u1, v1] = o.fit === true ? [0, 0, 1, 1] : o.fit;
      fit = [[u0, v0], [u1, v0], [u1, v1], [u0, v1]];
    }
    this._poly([a, b, c, d], o, fit);
  }
  tri(a, b, c, o = {}) { this._poly([a, b, c], o, null); }
  /** Convex polygon, counter-clockwise. */
  poly(pts, o = {}) { this._poly(pts, o, null); }

  /** Axis-aligned (in the current transform) box. `skip` drops faces: any of "xXyYzZ". */
  box(cx, cy, cz, sx, sy, sz, o = {}) {
    const x0 = cx - sx / 2, x1 = cx + sx / 2, y0 = cy - sy / 2, y1 = cy + sy / 2;
    const z0 = cz - sz / 2, z1 = cz + sz / 2;
    const skip = o.skip || '';
    const f = (id, a, b, c, d) => { if (!skip.includes(id)) this.quad(a, b, c, d, o); };
    f('Z', [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]);
    f('z', [x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0]);
    f('X', [x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1]);
    f('x', [x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]);
    f('Y', [x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0]);
    f('y', [x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]);
  }

  /** Box given by its minimum corner and size -- handier for framing lumber. */
  beam(x, y, z, sx, sy, sz, o) { this.box(x + sx / 2, y + sy / 2, z + sz / 2, sx, sy, sz, o); }

  /**
   * A planar quad given thickness: roof planes, porch decks, loft floors.
   * The top keeps the quad's winding; the underside and edges take their own
   * options because a roof's underside is bare wood in deep shade.
   */
  slab(a, b, c, d, th, top, under, edge) {
    const n = normalize(cross(sub(b, a), sub(d, a)));
    const dn = (p) => [p[0] - n[0] * th, p[1] - n[1] * th, p[2] - n[2] * th];
    const [a2, b2, c2, d2] = [a, b, c, d].map(dn);
    this.quad(a, b, c, d, top);
    this.quad(d2, c2, b2, a2, under || top);
    const e = edge || under || top;
    this.quad(a2, b2, b, a, e);
    this.quad(b2, c2, c, b, e);
    this.quad(c2, d2, d, c, e);
    this.quad(d2, a2, a, d, e);
  }

  /** Cylinder (or cone, with r1 = 0) standing on the local origin along +Y. */
  cyl(r0, r1, h, sides, o = {}, cap = true) {
    const ring = (r, y) => Array.from({ length: sides }, (_, i) => {
      const a = (i / sides) * Math.PI * 2;
      return [Math.sin(a) * r, y, Math.cos(a) * r];
    });
    const lo = ring(r0, 0), hi = ring(r1, h);
    for (let i = 0; i < sides; i++) {
      const j = (i + 1) % sides;
      if (r1 > 0) this.quad(lo[i], lo[j], hi[j], hi[i], o);
      else this.tri(lo[i], lo[j], [0, h, 0], o);
    }
    if (cap && r1 > 0) this.poly(hi, o.cap || o);
    if (cap && o.capBottom) this.poly(lo.slice().reverse(), o.cap || o);
  }

  finish() { return new Float32Array(this.data); }
}
