// Bakes a floor-space mask at load time:
//   G = fraction of ceiling-luminaire light that reaches each floor point
//       (so racks cast proper light pools and shadows onto the aisles)
//   R = short-range ambient occlusion (contact darkening at rack bases/walls)
// Occluders are axis-aligned boxes, so this is a fast analytic ray test.
import * as THREE from 'three';
import { ROOM, LIGHT_LINES } from './room.js';

function segBlocked(px, py, pz, dx, dy, dz, tMax, boxes) {
  for (let b = 0; b < boxes.length; b += 6) {
    let t0 = 0, t1 = tMax;
    // x slab
    if (Math.abs(dx) < 1e-9) { if (px < boxes[b] || px > boxes[b + 3]) continue; }
    else {
      let a = (boxes[b] - px) / dx, c = (boxes[b + 3] - px) / dx;
      if (a > c) { const t = a; a = c; c = t; }
      if (a > t0) t0 = a; if (c < t1) t1 = c;
      if (t0 > t1) continue;
    }
    if (Math.abs(dy) < 1e-9) { if (py < boxes[b + 1] || py > boxes[b + 4]) continue; }
    else {
      let a = (boxes[b + 1] - py) / dy, c = (boxes[b + 4] - py) / dy;
      if (a > c) { const t = a; a = c; c = t; }
      if (a > t0) t0 = a; if (c < t1) t1 = c;
      if (t0 > t1) continue;
    }
    if (Math.abs(dz) < 1e-9) { if (pz < boxes[b + 2] || pz > boxes[b + 5]) continue; }
    else {
      let a = (boxes[b + 2] - pz) / dz, c = (boxes[b + 5] - pz) / dz;
      if (a > c) { const t = a; a = c; c = t; }
      if (a > t0) t0 = a; if (c < t1) t1 = c;
      if (t0 > t1) continue;
    }
    return true;
  }
  return false;
}

export function bakeFloorMask(occluders, { res = 0.1, aoRays = 20, aoDist = 1.1 } = {}) {
  const W = ROOM.maxX - ROOM.minX, D = ROOM.maxZ - ROOM.minZ;
  const nx = Math.ceil(W / res), nz = Math.ceil(D / res);
  const boxes = new Float32Array(occluders.length * 6);
  occluders.forEach((b, i) => boxes.set([b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z], i * 6));
  // walls only matter for AO
  const t = 0.2;
  const walls = new Float32Array([
    ...boxes,
    ROOM.minX - t, 0, ROOM.minZ - t, ROOM.maxX + t, ROOM.h, ROOM.minZ,
    ROOM.minX - t, 0, ROOM.maxZ, ROOM.maxX + t, ROOM.h, ROOM.maxZ + t,
    ROOM.minX - t, 0, ROOM.minZ - t, ROOM.minX, ROOM.h, ROOM.maxZ + t,
    ROOM.maxX, 0, ROOM.minZ - t, ROOM.maxX + t, ROOM.h, ROOM.maxZ + t,
  ]);

  // luminaire samples: 2 across the diffuser, spaced along the run
  const S = [];
  for (const L of LIGHT_LINES) {
    const n = Math.ceil((L.b - L.a) / 0.4);
    for (let k = 0; k < n; k++) {
      const s = L.a + ((k + 0.5) * (L.b - L.a)) / n;
      for (const w of [-0.05, 0.05]) {
        if (L.axis === 'x') S.push(s, ROOM.h - 0.06, L.c + w);
        else S.push(L.c + w, ROOM.h - 0.06, s);
      }
    }
  }
  const ns = S.length / 3;

  // fixed low-discrepancy cosine hemisphere directions for AO
  const dirs = [];
  for (let i = 0; i < aoRays; i++) {
    const u = (i + 0.5) / aoRays, v = (i * 0.618034) % 1;
    const r = Math.sqrt(u), phi = v * Math.PI * 2;
    dirs.push(r * Math.cos(phi), Math.sqrt(1 - u), r * Math.sin(phi));
  }

  const vis = new Float32Array(nx * nz), ao = new Float32Array(nx * nz);
  for (let j = 0; j < nz; j++) {
    const z = ROOM.minZ + (1 - (j + 0.5) / nz) * D;
    for (let i = 0; i < nx; i++) {
      const x = ROOM.minX + ((i + 0.5) / nx) * W;
      const y = 0.01;
      let tot = 0, lit = 0;
      for (let s = 0; s < ns; s++) {
        const dx = S[s * 3] - x, dy = S[s * 3 + 1] - y, dz = S[s * 3 + 2] - z;
        const h2 = dx * dx + dz * dz;
        if (h2 > 36) continue;
        const d2 = h2 + dy * dy;
        const w = (dy * dy) / (d2 * d2); // cosθ_floor · cosθ_light / d²
        tot += w;
        if (!segBlocked(x, y, z, dx, dy, dz, 1, boxes)) lit += w;
      }
      vis[j * nx + i] = tot > 0 ? lit / tot : 1;
      let occ = 0;
      for (let k = 0; k < aoRays; k++) {
        if (segBlocked(x, y, z, dirs[k * 3] * aoDist, dirs[k * 3 + 1] * aoDist, dirs[k * 3 + 2] * aoDist, 1, walls)) occ++;
      }
      ao[j * nx + i] = 1 - 0.85 * (occ / aoRays);
    }
  }

  const blur = (src) => {
    const out = new Float32Array(src.length);
    for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
      let s = 0, c = 0;
      for (let b = -1; b <= 1; b++) for (let a = -1; a <= 1; a++) {
        const ii = i + a, jj = j + b;
        if (ii < 0 || jj < 0 || ii >= nx || jj >= nz) continue;
        s += src[jj * nx + ii]; c++;
      }
      out[j * nx + i] = s / c;
    }
    return out;
  };
  const v2 = blur(blur(vis)), a2 = blur(ao);

  const data = new Uint8Array(nx * nz * 4);
  for (let k = 0; k < nx * nz; k++) {
    data[k * 4] = Math.round(a2[k] * 255);
    data[k * 4 + 1] = Math.round(Math.min(1, 0.06 + v2[k] * 0.94) * 255);
    data[k * 4 + 2] = 0;
    data[k * 4 + 3] = 255;
  }
  const tex = new THREE.DataTexture(data, nx, nz, THREE.RGBAFormat);
  tex.magFilter = THREE.LinearFilter;
  tex.minFilter = THREE.LinearFilter;
  tex.colorSpace = THREE.NoColorSpace;
  tex.needsUpdate = true;
  return tex;
}
