/**
 * Scene collision is a list of axis-aligned rectangles drawn over the painted
 * art in the editor, rather than a tile grid. Painted scenes have furniture and
 * floors that do not sit on any grid, and boxes let the collision follow the
 * artwork exactly.
 *
 * Types:
 *   solid   -- blocks from every direction
 *   oneway  -- blocks only a fall from above (ledges, stair landings)
 *   ladder  -- not solid; enables climbing while overlapped
 *   block   -- solid, but the editor tints it differently (invisible walls)
 */
export const SOLID_TYPES = new Set(['solid', 'block']);

export const aabb = (a, b) =>
  a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;

export class CollisionWorld {
  constructor(rects = [], bounds = null) {
    this.rects = rects.map((r) => ({ type: 'solid', ...r }));
    this.bounds = bounds;
  }

  solids() {
    return this.rects.filter((r) => SOLID_TYPES.has(r.type));
  }

  oneways() {
    return this.rects.filter((r) => r.type === 'oneway');
    }

  ladders() {
    return this.rects.filter((r) => r.type === 'ladder');
  }

  overlapping(box, type) {
    return this.rects.filter((r) => r.type === type && aabb(box, r));
  }

  anyOverlap(box, type) {
    return this.rects.some((r) => r.type === type && aabb(box, r));
  }
}
