import { createSurface } from '../core/screen.js';

const flipCache = new WeakMap();

/**
 * A horizontally mirrored copy of an image, built once and cached. Mirroring
 * with ctx.scale(-1,1) every frame forces the canvas onto a slower path and
 * can land sprites a half-pixel off the grid; a pre-flipped copy stays exact.
 */
export function flipped(image) {
  let cached = flipCache.get(image);
  if (cached) return cached;
  const s = createSurface(image.width, image.height);
  s.ctx.translate(image.width, 0);
  s.ctx.scale(-1, 1);
  s.ctx.drawImage(image, 0, 0);
  cached = s.canvas;
  flipCache.set(image, cached);
  return cached;
}

/**
 * A sprite sheet plus its JSON description: named frame rectangles and named
 * animation clips. Hand-drawn sheets drop in by replacing the png and json
 * together, with no code change, as long as the clip names survive.
 */
export class Sprite {
  constructor(image, spec) {
    this.image = image;
    this.spec = spec;
    this.frames = spec.frames || {};
    this.clips = spec.clips || {};
    this.origin = spec.origin || 'bottom-center';
    this.placeholder = !!spec.placeholder;
  }

  frame(name) {
    const f = this.frames[name];
    if (!f) throw new Error(`Unknown frame "${name}" (have: ${Object.keys(this.frames).join(', ')})`);
    return f;
  }

  clip(name) {
    return this.clips[name] || null;
  }

  /**
   * Draw a frame with the sprite's origin applied, so callers position by the
   * character's feet rather than by a corner that moves between frames.
   */
  draw(ctx, frameName, x, y, { flip = false, offsetX = 0, offsetY = 0, alpha = 1 } = {}) {
    const f = this.frame(frameName);
    const src = flip ? flipped(this.image) : this.image;
    const sx = flip ? this.image.width - f.x - f.w : f.x;

    let dx = Math.round(x + offsetX);
    let dy = Math.round(y + offsetY);
    if (this.origin === 'bottom-center') {
      dx -= Math.round(f.w / 2);
      dy -= f.h;
    } else if (this.origin === 'center') {
      dx -= Math.round(f.w / 2);
      dy -= Math.round(f.h / 2);
    }

    const prevAlpha = ctx.globalAlpha;
    if (alpha !== 1) ctx.globalAlpha = prevAlpha * alpha;
    ctx.drawImage(src, sx, f.y, f.w, f.h, dx, dy, f.w, f.h);
    if (alpha !== 1) ctx.globalAlpha = prevAlpha;

    return { x: dx, y: dy, w: f.w, h: f.h };
  }
}
