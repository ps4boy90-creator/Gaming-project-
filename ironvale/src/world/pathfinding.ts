import type { World } from './world';

/** A* over the tile grid, 8-directional without corner cutting. */
export class Pathfinder {
  private g: Float32Array;
  private f: Float32Array;
  private from: Int32Array;
  private mark: Uint32Array;
  private closed: Uint32Array;
  private gen = 0;
  private heap: number[] = [];

  constructor(private world: World) {
    const n = world.n;
    this.g = new Float32Array(n);
    this.f = new Float32Array(n);
    this.from = new Int32Array(n);
    this.mark = new Uint32Array(n);
    this.closed = new Uint32Array(n);
  }

  private push(i: number) {
    const h = this.heap, f = this.f;
    h.push(i);
    let c = h.length - 1;
    while (c > 0) {
      const p = (c - 1) >> 1;
      if (f[h[p]] <= f[h[c]]) break;
      const t = h[p]; h[p] = h[c]; h[c] = t;
      c = p;
    }
  }
  private pop(): number {
    const h = this.heap, f = this.f;
    const top = h[0];
    const last = h.pop()!;
    if (h.length) {
      h[0] = last;
      let p = 0;
      const n = h.length;
      for (;;) {
        const l = p * 2 + 1, r = l + 1;
        let m = p;
        if (l < n && f[h[l]] < f[h[m]]) m = l;
        if (r < n && f[h[r]] < f[h[m]]) m = r;
        if (m === p) break;
        const t = h[p]; h[p] = h[m]; h[m] = t;
        p = m;
      }
    }
    return top;
  }

  /**
   * Returns the path as tile indices from start (exclusive) to goal (inclusive),
   * or null when unreachable. The goal tile is always allowed even when it carries
   * an object penalty.
   */
  find(start: number, goal: number, pass: number): number[] | null {
    const w = this.world.w, h = this.world.h;
    const cost = this.world.cost[pass];
    if (start === goal) return [];
    if (!cost[goal]) return null;
    const gen = ++this.gen;
    const g = this.g, f = this.f, from = this.from, mark = this.mark, closed = this.closed;
    this.heap.length = 0;
    const gx = goal % w, gy = (goal / w) | 0;
    g[start] = 0;
    f[start] = 0;
    mark[start] = gen;
    from[start] = -1;
    this.push(start);
    let iter = 0;
    while (this.heap.length) {
      const cur = this.pop();
      if (cur === goal) {
        const out: number[] = [];
        let c = cur;
        while (c !== start) {
          out.push(c);
          c = from[c];
        }
        out.reverse();
        return out;
      }
      if (closed[cur] === gen) continue;
      closed[cur] = gen;
      if (++iter > 12000) return null;
      const cx = cur % w, cy = (cur / w) | 0;
      for (let dy = -1; dy <= 1; dy++) {
        const ny = cy + dy;
        if (ny < 0 || ny >= h) continue;
        for (let dx = -1; dx <= 1; dx++) {
          if (!dx && !dy) continue;
          const nx = cx + dx;
          if (nx < 0 || nx >= w) continue;
          const ni = ny * w + nx;
          let c = cost[ni];
          if (!c || closed[ni] === gen) continue;
          if (ni === goal) c = 2;
          let step: number;
          if (dx && dy) {
            // no corner cutting, and never squeeze diagonally past doors
            const a = cost[cy * w + nx], b = cost[ny * w + cx];
            if (!a || !b || a === 4 || b === 4 || c === 4 || cost[cur] === 4) continue;
            step = c * 0.7071;
          } else step = c * 0.5;
          const ng = g[cur] + step;
          if (mark[ni] === gen && ng >= g[ni]) continue;
          g[ni] = ng;
          mark[ni] = gen;
          from[ni] = cur;
          const hx = Math.abs(nx - gx), hy = Math.abs(ny - gy);
          f[ni] = ng + (hx + hy - 0.5858 * Math.min(hx, hy));
          this.push(ni);
        }
      }
    }
    return null;
  }
}
