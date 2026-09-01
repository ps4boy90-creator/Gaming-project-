// The native pixel grid the whole game is authored against. The painted
// references are 7x upscales of exactly this resolution, and it multiplies to
// 1920x1080 at 5x, so the game is pixel-exact on a 1080p display.
export const NATIVE_W = 384;
export const NATIVE_H = 216;

/** An offscreen drawing surface with smoothing already disabled. */
export function createSurface(w, h) {
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;
  return { canvas, ctx, w, h };
}

/**
 * Owns the low-resolution backbuffer everything draws into, and blits it to
 * the visible canvas at an integer scale. Drawing at native size and scaling
 * once at the end is what keeps the pixel grid intact -- scaling individual
 * sprites instead would leave uneven pixels wherever a sprite landed on a
 * fractional coordinate.
 */
export class Screen {
  constructor(hostCanvas, w = NATIVE_W, h = NATIVE_H) {
    this.host = hostCanvas;
    this.hostCtx = hostCanvas.getContext('2d');
    this.w = w;
    this.h = h;

    const surface = createSurface(w, h);
    this.canvas = surface.canvas;
    this.ctx = surface.ctx;

    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;

    this._onResize = () => this.resize();
    window.addEventListener('resize', this._onResize);
    this.resize();
  }

  resize() {
    const rect = this.host.getBoundingClientRect();
    const availW = Math.max(1, Math.round(rect.width));
    const availH = Math.max(1, Math.round(rect.height));

    if (this.host.width !== availW || this.host.height !== availH) {
      this.host.width = availW;
      this.host.height = availH;
    }
    this.hostCtx.imageSmoothingEnabled = false;

    // Integer scale only. Fractional scaling is what makes pixel art shimmer.
    this.scale = Math.max(1, Math.floor(Math.min(availW / this.w, availH / this.h)));
    this.offsetX = Math.floor((availW - this.w * this.scale) / 2);
    this.offsetY = Math.floor((availH - this.h * this.scale) / 2);
  }

  /** Blit the backbuffer to the visible canvas, letterboxed and centred. */
  present() {
    const ctx = this.hostCtx;
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, this.host.width, this.host.height);
    ctx.drawImage(
      this.canvas,
      this.offsetX, this.offsetY,
      this.w * this.scale, this.h * this.scale,
    );
  }

  /** Map a DOM mouse/touch position to a native-resolution coordinate. */
  toNative(clientX, clientY) {
    const rect = this.host.getBoundingClientRect();
    return {
      x: (clientX - rect.left - this.offsetX) / this.scale,
      y: (clientY - rect.top - this.offsetY) / this.scale,
    };
  }

  destroy() {
    window.removeEventListener('resize', this._onResize);
  }
}
