/**
 * Walking. Slow on purpose -- the reference games move at a stroll, and the
 * unease comes from how long it takes to cross a dark yard.
 *
 * Collision is a circle against oriented boxes (walls, fences, the truck) and
 * other circles (tree trunks, posts). The same site transforms that placed the
 * geometry place the colliders, so they agree by construction.
 */
import { siteToWorld, worldToSite, clamp } from './math.js';
import { floorHeight, surfaceAt, inBounds, LEVEL_SPLIT } from './world.js';

const RADIUS = 0.32, EYE = 1.62, WALK = 1.9, RUN = 4.0, STRIDE = 0.74;

/**
 * `level` is the storey the player is on: 0 on the ground, 1 upstairs. A
 * collider marked with a level only exists there -- the dining table is not
 * in the way of somebody walking about the bedroom above it.
 */
export function resolve(x, z, world, level = 0) {
  for (let pass = 0; pass < 2; pass++) {
    for (const b of world.boxes) {
      if (b.level !== undefined && b.level !== level) continue;
      let [lx, lz] = worldToSite(b, x, z);
      if (Math.abs(lx) > b.hx + RADIUS || Math.abs(lz) > b.hz + RADIUS) continue;
      const cx = clamp(lx, -b.hx, b.hx), cz = clamp(lz, -b.hz, b.hz);
      const dx = lx - cx, dz = lz - cz, d = Math.hypot(dx, dz);
      if (d >= RADIUS) continue;
      if (d < 1e-6) {                 // centre is inside: leave by the nearest face
        if (b.hx - Math.abs(lx) < b.hz - Math.abs(lz)) lx = Math.sign(lx || 1) * (b.hx + RADIUS);
        else lz = Math.sign(lz || 1) * (b.hz + RADIUS);
      } else {
        lx = cx + (dx / d) * RADIUS;
        lz = cz + (dz / d) * RADIUS;
      }
      [x, z] = siteToWorld(b, lx, lz);
    }
    for (const [tx, tz, tr] of world.trunks) {
      const dx = x - tx, dz = z - tz, r = tr + RADIUS;
      if (Math.abs(dx) > r || Math.abs(dz) > r) continue;
      const d = Math.hypot(dx, dz);
      if (d < r && d > 1e-6) { x = tx + (dx / d) * r; z = tz + (dz / d) * r; }
    }
  }
  return [x, z];
}

export class Player {
  constructor(spawn) {
    Object.assign(this, { x: spawn.x, z: spawn.z, yaw: spawn.yaw, pitch: spawn.pitch });
    this.vx = 0; this.vz = 0;
    this.floor = floorHeight(this.x, this.z, 0);
    this.bob = 0; this.travel = 0; this.speed = 0;
    this.onStep = null;
  }
  get eye() {
    return [this.x, this.floor + EYE + Math.sin(this.bob * Math.PI * 2) * 0.028 * Math.min(1, this.speed / WALK), this.z];
  }
  look(dyaw, dpitch) {
    this.yaw += dyaw;
    this.pitch = clamp(this.pitch + dpitch, -1.35, 1.35);
  }
  /** `move` is { fwd, strafe } in -1..1 and `run` a boolean. */
  update(dt, move, run, world) {
    const top = run ? RUN : WALK;
    // Never scale a small input up: a thumbstick held halfway should walk slowly.
    const len = Math.max(1, Math.hypot(move.fwd, move.strafe));
    const f = (move.fwd / len) * top, s = (move.strafe / len) * top;
    const sin = Math.sin(this.yaw), cos = Math.cos(this.yaw);
    const k = 1 - Math.exp(-9 * dt);
    this.vx += ((-sin * f + cos * s) - this.vx) * k;
    this.vz += ((-cos * f - sin * s) - this.vz) * k;

    const level = this.floor > LEVEL_SPLIT ? 1 : 0;
    let [nx, nz] = resolve(this.x + this.vx * dt, this.z + this.vz * dt, world, level);
    // The edge of the map is just the forest getting too thick: slide along it.
    if (!inBounds(nx, nz)) {
      if (inBounds(nx, this.z)) nz = this.z; else if (inBounds(this.x, nz)) nx = this.x; else { nx = this.x; nz = this.z; }
    }
    const moved = Math.hypot(nx - this.x, nz - this.z);
    this.x = nx; this.z = nz;
    this.speed = moved / Math.max(dt, 1e-4);
    this.floor += (floorHeight(nx, nz, this.floor) - this.floor) * (1 - Math.exp(-14 * dt));

    this.travel += moved;
    this.bob = this.travel / (STRIDE * 2);
    if (this.travel - (this.lastStep || 0) > STRIDE) {
      this.lastStep = this.travel;
      if (this.onStep) this.onStep(surfaceAt(nx, nz), run);
    }
  }
}
