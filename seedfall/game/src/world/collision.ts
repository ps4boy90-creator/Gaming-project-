/** Axis-aligned collision world with a uniform XZ grid. The ship is built on a right-angle grid,
 *  so boxes are exact for walls, floors and furniture. */
export interface Box {
  minX: number;
  minY: number;
  minZ: number;
  maxX: number;
  maxY: number;
  maxZ: number;
  solid: boolean;
  /** 'wall' boxes block interaction rays; others only block movement. */
  tag: string;
  stamp: number;
}

export class CollisionWorld {
  boxes: Box[] = [];
  private grid = new Map<number, Box[]>();
  private cell = 4;
  private stamp = 0;

  private key(ix: number, iz: number): number {
    return (ix + 4096) * 8192 + (iz + 4096);
  }

  add(minX: number, minY: number, minZ: number, maxX: number, maxY: number, maxZ: number, tag = 'solid'): Box {
    const b: Box = {
      minX: Math.min(minX, maxX),
      minY: Math.min(minY, maxY),
      minZ: Math.min(minZ, maxZ),
      maxX: Math.max(minX, maxX),
      maxY: Math.max(minY, maxY),
      maxZ: Math.max(minZ, maxZ),
      solid: true,
      tag,
      stamp: 0,
    };
    this.boxes.push(b);
    const c = this.cell;
    for (let ix = Math.floor(b.minX / c); ix <= Math.floor(b.maxX / c); ix++) {
      for (let iz = Math.floor(b.minZ / c); iz <= Math.floor(b.maxZ / c); iz++) {
        const k = this.key(ix, iz);
        let list = this.grid.get(k);
        if (!list) {
          list = [];
          this.grid.set(k, list);
        }
        list.push(b);
      }
    }
    return b;
  }

  /** All boxes whose cells touch the XZ rectangle (deduplicated). */
  query(minX: number, minZ: number, maxX: number, maxZ: number, out: Box[] = []): Box[] {
    out.length = 0;
    const s = ++this.stamp;
    const c = this.cell;
    for (let ix = Math.floor(minX / c); ix <= Math.floor(maxX / c); ix++) {
      for (let iz = Math.floor(minZ / c); iz <= Math.floor(maxZ / c); iz++) {
        const list = this.grid.get(this.key(ix, iz));
        if (!list) continue;
        for (const b of list) {
          if (b.stamp === s) continue;
          b.stamp = s;
          out.push(b);
        }
      }
    }
    return out;
  }

  private tmp: Box[] = [];

  private circleOverlaps(b: Box, x: number, z: number, r: number): boolean {
    const cx = Math.max(b.minX, Math.min(x, b.maxX));
    const cz = Math.max(b.minZ, Math.min(z, b.maxZ));
    return (x - cx) ** 2 + (z - cz) ** 2 < r * r;
  }

  /** Highest box top under the circle that is at or below maxY. */
  groundAt(x: number, z: number, r: number, maxY: number): number {
    let best = -Infinity;
    for (const b of this.query(x - r, z - r, x + r, z + r, this.tmp)) {
      if (!b.solid || b.maxY > maxY + 1e-4 || b.maxY <= best) continue;
      if (this.circleOverlaps(b, x, z, r)) best = b.maxY;
    }
    return best;
  }

  /** Lowest box bottom above minY over the circle. */
  ceilingAt(x: number, z: number, r: number, minY: number): number {
    let best = Infinity;
    for (const b of this.query(x - r, z - r, x + r, z + r, this.tmp)) {
      if (!b.solid || b.minY < minY - 1e-4 || b.minY >= best) continue;
      if (this.circleOverlaps(b, x, z, r)) best = b.minY;
    }
    return best;
  }

  /** Push a vertical cylinder (circle in XZ spanning y0..y1) out of solid boxes. */
  pushOut(pos: { x: number; z: number }, r: number, y0: number, y1: number): boolean {
    let hit = false;
    for (let iter = 0; iter < 3; iter++) {
      let moved = false;
      for (const b of this.query(pos.x - r, pos.z - r, pos.x + r, pos.z + r, this.tmp)) {
        if (!b.solid || b.maxY <= y0 || b.minY >= y1) continue;
        const cx = Math.max(b.minX, Math.min(pos.x, b.maxX));
        const cz = Math.max(b.minZ, Math.min(pos.z, b.maxZ));
        let dx = pos.x - cx;
        let dz = pos.z - cz;
        const d2 = dx * dx + dz * dz;
        if (d2 >= r * r) continue;
        if (d2 > 1e-10) {
          const d = Math.sqrt(d2);
          const push = r - d;
          pos.x += (dx / d) * push;
          pos.z += (dz / d) * push;
        } else {
          // Centre inside the box: leave along the shallowest axis.
          const pl = pos.x - b.minX + r;
          const pr = b.maxX - pos.x + r;
          const pb = pos.z - b.minZ + r;
          const pf = b.maxZ - pos.z + r;
          const m = Math.min(pl, pr, pb, pf);
          if (m === pl) pos.x -= pl;
          else if (m === pr) pos.x += pr;
          else if (m === pb) pos.z -= pb;
          else pos.z += pf;
          dx = dz = 0;
        }
        moved = hit = true;
      }
      if (!moved) break;
    }
    return hit;
  }

  /** Distance along a ray to the first box (optionally only those with a given tag). */
  raycast(
    ox: number, oy: number, oz: number,
    dx: number, dy: number, dz: number,
    maxDist: number, tag?: string,
  ): number {
    const ex = ox + dx * maxDist;
    const ez = oz + dz * maxDist;
    let best = maxDist;
    const list = this.query(Math.min(ox, ex), Math.min(oz, ez), Math.max(ox, ex), Math.max(oz, ez), this.tmp);
    for (const b of list) {
      if (!b.solid || (tag && b.tag !== tag)) continue;
      const t = rayBox(ox, oy, oz, dx, dy, dz, b.minX, b.minY, b.minZ, b.maxX, b.maxY, b.maxZ);
      if (t >= 0 && t < best) best = t;
    }
    return best;
  }
}

/** Slab test. Returns entry distance, or -1 for a miss. A ray starting inside returns 0. */
export function rayBox(
  ox: number, oy: number, oz: number,
  dx: number, dy: number, dz: number,
  minX: number, minY: number, minZ: number,
  maxX: number, maxY: number, maxZ: number,
): number {
  let tmin = -Infinity;
  let tmax = Infinity;
  const axes: [number, number, number, number][] = [
    [ox, dx, minX, maxX],
    [oy, dy, minY, maxY],
    [oz, dz, minZ, maxZ],
  ];
  for (const [o, d, mn, mx] of axes) {
    if (Math.abs(d) < 1e-9) {
      if (o < mn || o > mx) return -1;
    } else {
      let t1 = (mn - o) / d;
      let t2 = (mx - o) / d;
      if (t1 > t2) [t1, t2] = [t2, t1];
      tmin = Math.max(tmin, t1);
      tmax = Math.min(tmax, t2);
      if (tmin > tmax) return -1;
    }
  }
  if (tmax < 0) return -1;
  return Math.max(0, tmin);
}
