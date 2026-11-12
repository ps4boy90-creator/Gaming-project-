/**
 * The little linear algebra the farm scene needs. Matrices are column-major
 * Float32Arrays, as WebGL wants them; vectors are plain 3-element arrays.
 *
 * One convention is worth stating once because the mesh builder, the camera
 * and the collision code all lean on it: a positive rotation about Y turns
 * +Z toward +X. `siteToWorld` / `worldToSite` are the same rotation written
 * out for the 2D ground plane, so a wall placed with rotY(a) and a collider
 * placed with siteToWorld(..., a) always land on top of each other.
 */
export const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const scale = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
export const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross = (a, b) => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
export const length = (a) => Math.hypot(a[0], a[1], a[2]);
export const normalize = (a) => {
  const l = length(a) || 1;
  return [a[0] / l, a[1] / l, a[2] / l];
};
export const mix = (a, b, t) => a + (b - a) * t;
export const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);
export const smoothstep = (a, b, x) => {
  const t = clamp((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};

export const IDENT = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);

/** a * b: apply b first, then a. */
export function mul(a, b) {
  const o = new Float32Array(16);
  for (let c = 0; c < 4; c++) {
    for (let r = 0; r < 4; r++) {
      o[c * 4 + r] =
        a[r] * b[c * 4] + a[4 + r] * b[c * 4 + 1] + a[8 + r] * b[c * 4 + 2] + a[12 + r] * b[c * 4 + 3];
    }
  }
  return o;
}
export const translate = (x, y, z) =>
  new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1]);
export function rotY(a) {
  const c = Math.cos(a), s = Math.sin(a);
  return new Float32Array([c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1]);
}
export function rotX(a) {
  const c = Math.cos(a), s = Math.sin(a);
  return new Float32Array([1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1]);
}
export function rotZ(a) {
  const c = Math.cos(a), s = Math.sin(a);
  return new Float32Array([c, s, 0, 0, -s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
}
/** Chain transforms left to right: the last one is applied to the point first. */
export const chain = (...ms) => ms.reduce((a, b) => mul(a, b));

export const xformPoint = (m, p) => [
  m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
  m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
  m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14],
];
export const xformDir = (m, d) => [
  m[0] * d[0] + m[4] * d[1] + m[8] * d[2],
  m[1] * d[0] + m[5] * d[1] + m[9] * d[2],
  m[2] * d[0] + m[6] * d[1] + m[10] * d[2],
];

export function perspective(fovY, aspect, near, far) {
  const f = 1 / Math.tan(fovY / 2);
  const o = new Float32Array(16);
  o[0] = f / aspect;
  o[5] = f;
  o[10] = (far + near) / (near - far);
  o[11] = -1;
  o[14] = (2 * far * near) / (near - far);
  return o;
}

/** Yaw 0 looks down -Z (north); positive yaw turns left. Pitch up is positive. */
export function cameraBasis(yaw, pitch) {
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  const fwd = [-Math.sin(yaw) * cp, sp, -Math.cos(yaw) * cp];
  const right = [Math.cos(yaw), 0, -Math.sin(yaw)];
  const up = cross(right, fwd);
  return { fwd, right, up };
}
export const viewMatrix = (pos, yaw, pitch) =>
  chain(rotX(-pitch), rotY(-yaw), translate(-pos[0], -pos[1], -pos[2]));

/** Ground-plane version of rotY(yaw) followed by a move to (cx, cz). */
export function siteToWorld(site, lx, lz) {
  const c = Math.cos(site.yaw), s = Math.sin(site.yaw);
  return [site.x + lx * c + lz * s, site.z - lx * s + lz * c];
}
export function worldToSite(site, wx, wz) {
  const c = Math.cos(site.yaw), s = Math.sin(site.yaw);
  const dx = wx - site.x, dz = wz - site.z;
  return [dx * c - dz * s, dx * s + dz * c];
}
