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
 * A solid can also carry a gloss from 0 to 1 -- glazed china, a TV screen, a
 * varnished table -- which rides in the same slot as a fraction below 0.5.
 */
import { IDENT, mul, xformPoint, xformNormal, cross, sub, normalize, dot, chain, translate, rotY, rotZ } from './math.js';

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

/**
 * A wall with holes in it, on the plane z = 0: the outside face looks down
 * +Z and the inside face sits `t` behind it. `holes` are rectangles
 * { x0, x1, y0, y1 }; the wall is cut into a grid along their edges and every
 * cell that is not a hole gets a face on each side, so the texture runs
 * unbroken across the cuts. Each hole gets its reveals -- the thickness of
 * the wall, seen edge-on -- except along a bottom edge that sits on the floor.
 */
export function wall(m, x0, x1, y0, y1, holes, outer, inner, t, reveal) {
  const hs = holes.filter((h) => h.x1 > x0 + 1e-6 && h.x0 < x1 - 1e-6);
  const cuts = (lo, hi, a, b) => [...new Set([lo, hi, ...hs.flatMap((h) => [h[a], h[b]])])].filter((v) => v >= lo && v <= hi).sort((p, q) => p - q);
  const xs = cuts(x0, x1, 'x0', 'x1'), ys = cuts(y0, y1, 'y0', 'y1');
  for (let i = 0; i < xs.length - 1; i++) for (let j = 0; j < ys.length - 1; j++) {
    const cx = (xs[i] + xs[i + 1]) / 2, cy = (ys[j] + ys[j + 1]) / 2;
    if (hs.some((h) => cx > h.x0 && cx < h.x1 && cy > h.y0 && cy < h.y1)) continue;
    if (outer) m.quad([xs[i], ys[j], 0], [xs[i + 1], ys[j], 0], [xs[i + 1], ys[j + 1], 0], [xs[i], ys[j + 1], 0], outer);
    if (inner) m.quad([xs[i + 1], ys[j], -t], [xs[i], ys[j], -t], [xs[i], ys[j + 1], -t], [xs[i + 1], ys[j + 1], -t], inner);
  }
  for (const h of hs) {
    const a = Math.max(h.x0, x0), b = Math.min(h.x1, x1);
    if (h.x0 >= x0) m.quad([a, h.y0, 0], [a, h.y0, -t], [a, h.y1, -t], [a, h.y1, 0], reveal);
    if (h.x1 <= x1) m.quad([b, h.y0, -t], [b, h.y0, 0], [b, h.y1, 0], [b, h.y1, -t], reveal);
    m.quad([a, h.y1, 0], [b, h.y1, 0], [b, h.y1, -t], [a, h.y1, -t], reveal);
    if (h.y0 > y0 + 1e-6) m.quad([a, h.y0, -t], [b, h.y0, -t], [b, h.y0, 0], [a, h.y0, 0], reveal);
  }
}

/**
 * A level slab from (x0, z0) to (x1, z1) at height y, with a rectangular
 * hole [hx0, hz0, hx1, hz1] left in it: a ceiling round a stairwell.
 */
export function plate(m, x0, z0, x1, z1, y, hole, o) {
  const [a, b, c, d] = hole;
  for (const [p, q, r, s] of [[x0, z0, a, z1], [c, z0, x1, z1], [a, z0, c, b], [a, d, c, z1]]) {
    if (r - p > 1e-6 && s - q > 1e-6) m.quad([p, y, s], [r, y, s], [r, y, q], [p, y, q], o);
  }
}

export class Mesh {
  constructor(tiles) {
    // A typed array that doubles when full. The scene is several hundred
    // thousand vertices; as a plain array of numbers it would cost twice the
    // memory and then be copied into one of these anyway.
    this.buf = new Float32Array(1 << 20);
    this.used = 0;
    this.count = 0;
    this.parts = [];
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
    if (this.used + STRIDE > this.buf.length) {
      const bigger = new Float32Array(this.buf.length * 2);
      bigger.set(this.buf);
      this.buf = bigger;
    }
    const b = this.buf, k = this.used;
    b[k] = w[0]; b[k + 1] = w[1]; b[k + 2] = w[2];
    b[k + 3] = n[0]; b[k + 4] = n[1]; b[k + 5] = n[2];
    b[k + 6] = u; b[k + 7] = v; b[k + 8] = o.layer || 0;
    b[k + 9] = c[0]; b[k + 10] = c[1]; b[k + 11] = c[2];
    b[k + 12] = pick(o.occ, i, 1); b[k + 13] = o.emit || 0; b[k + 14] = pick(o.sway, i, 0);
    b[k + 15] = o.kind || (o.gloss ? o.gloss * 0.4 : 0);
    this.used += STRIDE;
    this.count++;
  }

  /**
   * A triangle or quad with a normal at each corner, in local space. This is
   * what lets a lathe-turned leg or a cushion shade as a curve instead of as
   * the facets it is made of.
   */
  smooth(pts, nrms, uvs, o = {}) {
    const wn = nrms.map((n) => xformNormal(this.m, n));
    for (const k of pts.length === 4 ? [0, 1, 2, 0, 2, 3] : [0, 1, 2]) {
      this._vert(pts[k], wn[k], uvs[k][0], uvs[k][1], o, 0);
    }
  }

  /** Plane-space UV axes: U horizontal, V up the slope. Flat faces use X / -Z. */
  _basis(n) {
    if (Math.abs(n[1]) > 0.999) return [[1, 0, 0], [0, 0, -Math.sign(n[1]) || -1]];
    const u = normalize(cross([0, 1, 0], n));
    return [u, cross(n, u)];
  }

  _poly(pts, o, fitUV) {
    const nLocal = normalize(cross(sub(pts[1], pts[0]), sub(pts[pts.length - 1], pts[0])));
    const n = o.normal || xformNormal(this.m, nLocal);
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

  /**
   * Geometry that will move, or switch on and off, after the scene is built:
   * a door leaf, a lampshade, a television screen. `fn` builds it in its own
   * space; the transform in force right now is remembered as its resting
   * place. The vertices go in after everything fixed (see finish), so the
   * fixed scene stays one draw call and each part is one more.
   */
  part(fn) {
    const handle = { base: new Float32Array(this.m), matrix: new Float32Array(this.m), first: 0, count: 0, emit: 1, tint: [1, 1, 1], fn };
    this.parts.push(handle);
    return handle;
  }

  finish() {
    this.fixed = this.count;
    const stack = this.stack;
    for (const p of this.parts) {
      this.stack = [IDENT];
      p.first = this.count;
      p.fn();
      p.count = this.count - p.first;
      delete p.fn;
    }
    this.stack = stack;
    return this.buf.subarray(0, this.used);
  }
}
