import { aabb, SOLID_TYPES } from './collision.js';

export const GRAVITY = 900;          // px/s^2
export const TERMINAL_VELOCITY = 620;
export const STEP_UP = 6;            // how tall a lip the walk can climb unaided

/**
 * A moving box. Position is the character's feet: x is the horizontal centre
 * and y is the bottom edge, which matches the sprite origin so a frame of a
 * different height never makes the character appear to sink into the floor.
 */
export function makeBody(x, y, w, h) {
  return { x, y, w, h, vx: 0, vy: 0, onGround: false, onLadder: false, climbing: false };
}

export const boxOf = (body) => ({ x: body.x - body.w / 2, y: body.y - body.h, w: body.w, h: body.h });

/**
 * Move on one axis at a time and resolve against the world. Separating the
 * axes is what stops a character from catching on the seam between two
 * adjoining floor rectangles -- a diagonal sweep would report a corner hit
 * there and stop the walk dead.
 */
export function moveAndCollide(body, world, dt) {
  const result = { hitX: false, hitY: false, landed: false };
  const wasOnGround = body.onGround;
  body.onGround = false;

  // ---- horizontal
  const dx = body.vx * dt;
  if (dx !== 0) {
    body.x += dx;
    const box = boxOf(body);
    for (const r of world.rects) {
      if (!SOLID_TYPES.has(r.type) || !aabb(box, r)) continue;

      // A low lip is stepped over rather than blocking, so door sills and
      // rug edges do not stop a walk.
      const lip = box.y + box.h - r.y;
      if (wasOnGround && lip > 0 && lip <= STEP_UP && body.vy >= 0) {
        body.y = r.y;
        box.y = body.y - body.h;
        continue;
      }

      body.x = dx > 0 ? r.x - body.w / 2 : r.x + r.w + body.w / 2;
      body.vx = 0;
      result.hitX = true;
      box.x = body.x - body.w / 2;
    }
  }

  // ---- vertical
  const dy = body.vy * dt;
  body.y += dy;
  const box = boxOf(body);
  for (const r of world.rects) {
    const solid = SOLID_TYPES.has(r.type);
    const oneway = r.type === 'oneway';
    if (!solid && !oneway) continue;
    if (!aabb(box, r)) continue;

    if (oneway) {
      // Only catches a downward move whose feet started above the surface.
      const previousFeet = body.y - dy;
      if (body.vy < 0 || previousFeet > r.y + 1) continue;
    }

    if (dy > 0 || oneway) {
      body.y = r.y;
      body.vy = 0;
      body.onGround = true;
      if (!wasOnGround) result.landed = true;
    } else if (dy < 0) {
      body.y = r.y + r.h + body.h;
      body.vy = 0;
    }
    result.hitY = true;
    box.y = body.y - body.h;
  }

  // ---- scene bounds
  if (world.bounds) {
    const half = body.w / 2;
    if (body.x - half < 0) { body.x = half; body.vx = 0; }
    if (body.x + half > world.bounds.w) { body.x = world.bounds.w - half; body.vx = 0; }
    if (body.y > world.bounds.h) {
      body.y = world.bounds.h;
      body.vy = 0;
      body.onGround = true;
    }
  }

  return result;
}

export function applyGravity(body, dt, scale = 1) {
  body.vy = Math.min(TERMINAL_VELOCITY, body.vy + GRAVITY * scale * dt);
}
