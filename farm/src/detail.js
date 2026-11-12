/**
 * Curved things.
 *
 * The buildings and the truck are built from flat faces because that is the
 * look. Furniture is different: a room is read from a metre away, and a table
 * leg that is a square post or a lampshade with six sides says "placeholder"
 * however good its texture is. So the inside of the house is modelled with
 * these instead -- lathe-turned profiles, boxes with properly rounded edges,
 * tubes swept along a path, cloth that hangs in folds -- all with a normal at
 * every vertex so they shade as curves.
 *
 * They add geometry freely. A dining chair here is a few thousand triangles,
 * which is nothing to a graphics card and is the difference between a chair
 * and a diagram of one.
 */
import { normalize, cross, sub, dot } from './math.js';

const tileOf = (m, o) => o.tile || m.tiles[o.layer || 0] || 1;

/**
 * Spin a profile of [radius, height] points round the Y axis. Repeat a point
 * to put a hard edge there; otherwise the surface is smooth through it.
 */
export function lathe(m, profile, seg, o = {}) {
  const t = 1 / tileOf(m, o);
  const same = (a, b) => Math.abs(a[0] - b[0]) < 1e-9 && Math.abs(a[1] - b[1]) < 1e-9;
  const n2 = profile.map((p, i) => {
    const a = i > 0 && !same(profile[i - 1], p) ? profile[i - 1] : p;
    const b = i < profile.length - 1 && !same(profile[i + 1], p) ? profile[i + 1] : p;
    const dr = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dr, dy) || 1;
    return [dy / l, -dr / l];
  });
  const circ = Math.max(...profile.map((p) => p[0])) * Math.PI * 2;
  const along = [0];
  for (let i = 1; i < profile.length; i++) along.push(along[i - 1] + Math.hypot(profile[i][0] - profile[i - 1][0], profile[i][1] - profile[i - 1][1]));
  const P = (p, a) => [Math.sin(a) * p[0], p[1], Math.cos(a) * p[0]];
  const N = (n, a) => [Math.sin(a) * n[0], n[1], Math.cos(a) * n[0]];
  for (let j = 0; j < seg; j++) {
    const a0 = (j / seg) * Math.PI * 2, a1 = ((j + 1) / seg) * Math.PI * 2;
    const u0 = (j / seg) * circ * t, u1 = ((j + 1) / seg) * circ * t;
    for (let i = 0; i < profile.length - 1; i++) {
      const p0 = profile[i], p1 = profile[i + 1];
      if (same(p0, p1)) continue;
      m.smooth([P(p0, a0), P(p0, a1), P(p1, a1), P(p1, a0)], [N(n2[i], a0), N(n2[i], a1), N(n2[i + 1], a1), N(n2[i + 1], a0)],
        [[u0, along[i] * t], [u1, along[i] * t], [u1, along[i + 1] * t], [u0, along[i + 1] * t]], o);
    }
  }
}

/** A ball, or with `squash` an egg, an apple, a lampshade's glass. */
export function sphere(m, r, seg, o = {}, squash = 1) {
  const rings = Math.max(4, seg >> 1), prof = [];
  for (let i = 0; i <= rings; i++) {
    const a = (i / rings) * Math.PI;
    prof.push([Math.sin(a) * r, -Math.cos(a) * r * squash]);
  }
  lathe(m, prof, seg, o);
}

/**
 * A box whose edges and corners are rounded to radius `r`. Each face is a
 * grid that is fine where it turns the corner and one cell across the flat.
 */
export function roundBox(m, cx, cy, cz, sx, sy, sz, r, seg = 2, o = {}) {
  const h = [sx / 2, sy / 2, sz / 2], c = [cx, cy, cz];
  r = Math.min(r, h[0], h[1], h[2]);
  const t = 1 / tileOf(m, o);
  const line = (hh) => {
    const out = [];
    for (let k = seg; k >= 0; k--) out.push(-(hh - r) - r * Math.tan((k / seg) * Math.PI / 4));
    for (let k = 0; k <= seg; k++) out.push(hh - r + r * Math.tan((k / seg) * Math.PI / 4));
    return out.filter((v, i) => i === 0 || Math.abs(v - out[i - 1]) > 1e-7);
  };
  for (let A = 0; A < 3; A++) {
    const U = (A + 1) % 3, V = (A + 2) % 3, us = line(h[U]), vs = line(h[V]);
    const hAxis = A === 1 ? 0 : A === 0 ? 2 : 0, vAxis = A === 1 ? 2 : 1;
    for (const sign of [-1, 1]) {
      const vert = (u, v) => {
        const p = [0, 0, 0];
        p[A] = sign * h[A]; p[U] = u; p[V] = v;
        const inner = p.map((x, a) => Math.max(-(h[a] - r), Math.min(h[a] - r, x)));
        const n = normalize(sub(p, inner));
        const q = [c[0] + inner[0] + n[0] * r, c[1] + inner[1] + n[1] * r, c[2] + inner[2] + n[2] * r];
        const uv = [q[hAxis] * t, q[vAxis] * t];
        return { q, n, uv: o.uvRot ? [uv[1], uv[0]] : uv };
      };
      for (let i = 0; i < us.length - 1; i++) for (let j = 0; j < vs.length - 1; j++) {
        const k = [vert(us[i], vs[j]), vert(us[i + 1], vs[j]), vert(us[i + 1], vs[j + 1]), vert(us[i], vs[j + 1])];
        m.smooth(k.map((e) => e.q), k.map((e) => e.n), k.map((e) => e.uv), o);
      }
    }
  }
}

/**
 * A round section swept along a path: chair rails, lamp stems, taps, handles.
 * `r` may be a function of distance along the path from 0 to 1, for tapers.
 */
export function tube(m, pts, r, sides, o = {}, caps = true) {
  const t = 1 / tileOf(m, o), n = pts.length;
  const rad = typeof r === 'function' ? r : () => r;
  const tan = pts.map((p, i) => normalize(sub(pts[Math.min(n - 1, i + 1)], pts[Math.max(0, i - 1)])));
  let nor = Math.abs(tan[0][1]) < 0.9 ? normalize(cross(tan[0], [0, 1, 0])) : [1, 0, 0];
  const rings = [];
  let len = 0;
  for (let i = 0; i < n; i++) {
    if (i) len += Math.hypot(...sub(pts[i], pts[i - 1]));
    const d = dot(nor, tan[i]);
    nor = normalize([nor[0] - tan[i][0] * d, nor[1] - tan[i][1] * d, nor[2] - tan[i][2] * d]);
    const bin = cross(tan[i], nor), rr = rad(i / (n - 1)), ring = [];
    for (let k = 0; k <= sides; k++) {
      const a = (k / sides) * Math.PI * 2, c = Math.cos(a), s = Math.sin(a);
      const dir = [nor[0] * c + bin[0] * s, nor[1] * c + bin[1] * s, nor[2] * c + bin[2] * s];
      ring.push({ p: [pts[i][0] + dir[0] * rr, pts[i][1] + dir[1] * rr, pts[i][2] + dir[2] * rr], n: dir, uv: [(k / sides) * rr * 6.28 * t, len * t] });
    }
    rings.push(ring);
  }
  for (let i = 0; i < n - 1; i++) for (let k = 0; k < sides; k++) {
    const q = [rings[i][k], rings[i][k + 1], rings[i + 1][k + 1], rings[i + 1][k]];
    m.smooth(q.map((e) => e.p), q.map((e) => e.n), q.map((e) => e.uv), o);
  }
  if (caps) {
    m.poly(rings[0].slice(0, sides).map((e) => e.p), o);
    m.poly(rings[n - 1].slice(0, sides).map((e) => e.p), o);
  }
}

/**
 * Hanging cloth: a panel `w` wide and `h` tall with its bottom-left corner at
 * the local origin, gathered into `folds` pleats that open out toward the hem.
 */
export function drape(m, w, h, folds, depth, o = {}) {
  const t = 1 / tileOf(m, o), cols = folds * 6, rows = 4;
  const at = (i, j) => {
    const u = i / cols, v = j / rows, open = 0.55 + 0.45 * (1 - v);
    const ph = u * folds * Math.PI * 2 + (1 - v) * 0.7;
    const z = Math.sin(ph) * depth * open + Math.sin(ph * 2.3 + 1) * depth * 0.18;
    const dz = (Math.cos(ph) * depth * open + Math.cos(ph * 2.3 + 1) * depth * 0.41) * folds * Math.PI * 2 / w;
    return { p: [u * w, v * h, z], n: normalize([-dz, 0, 1]), uv: [u * w * 1.5 * t, v * h * t] };
  };
  for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
    const q = [at(i, j), at(i + 1, j), at(i + 1, j + 1), at(i, j + 1)];
    m.smooth(q.map((e) => e.p), q.map((e) => e.n), q.map((e) => e.uv), o);
  }
}
