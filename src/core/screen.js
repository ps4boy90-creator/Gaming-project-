// The native pixel grid the whole game is authored against. The painted
// references are 7x upscales of exactly this resolution, and it multiplies to
// 1920x1080 at 5x, so the game is pixel-exact on a 1080p display.
export const NATIVE_W = 384;
export const NATIVE_H = 216;

/**
 * Cutscenes render at twice the linear resolution -- four times the pixels.
 *
 * The gameplay grid exists so a walk cycle stays crisp; a full-screen still has
 * no such constraint, and capping it at 384x216 was throwing away most of the
 * detail in the source art, which is 2688x1520.
 */
export const CUTSCENE_W = NATIVE_W * 2;
export const CUTSCENE_H = NATIVE_H * 2;

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

    // A second, higher-resolution surface used only while a cutscene plays.
    const hi = createSurface(CUTSCENE_W, CUTSCENE_H);
    this.cutsceneCanvas = hi.canvas;
    this.cutsceneCtx = hi.ctx;
    /** Which surface present() blits. Gameplay never touches this. */
    this.useCutsceneSurface = false;
    /**
     * The cutscene surface does not land on an integer multiple of the display
     * (768x432 into 1920x1080 is 2.5x), so it is smoothed on the way out while
     * gameplay stays exact. On a slow pan across a detailed still that reads as
     * film rather than as a mistake -- but it is a real difference, so it can be
     * turned off.
     */
    this.smoothCutscenes = true;
    /**
     * Bilinear, not the browser's 'high' setting. 'high' is a multi-pass
     * resample built for *downscaling*; on a 2.5x upscale it looks the same as
     * bilinear and costs half the frame rate -- a still cutscene ran at 32fps
     * with it on, which is the sort of thing that only shows up if you measure
     * frames during a cutscene rather than during gameplay.
     */
    this.smoothQuality = 'low';

    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    /** A CSS filter string applied to the final blit, or '' for none. */
    this.filter = '';

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

  /**
   * Blit the backbuffer to the visible canvas, letterboxed and centred.
   *
   * `filter` is applied here rather than per-draw so it costs one GPU-side
   * operation on the final image. The art is already monochrome on disk; this
   * catches what the pipeline cannot -- the additive coloured lights, and the
   * UI accent -- so that turning it off genuinely restores colour rather than
   * revealing a half-converted picture.
   */
  present() {
    const ctx = this.hostCtx;
    ctx.imageSmoothingEnabled = false;
    ctx.filter = 'none';
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, this.host.width, this.host.height);
    if (this.filter) ctx.filter = this.filter;

    // Both surfaces occupy the same letterboxed rectangle; only their pixel
    // density differs, so switching between them never moves the picture.
    const source = this.useCutsceneSurface ? this.cutsceneCanvas : this.canvas;
    ctx.imageSmoothingEnabled = this.useCutsceneSurface && this.smoothCutscenes;
    if (ctx.imageSmoothingEnabled) ctx.imageSmoothingQuality = this.smoothQuality;

    ctx.drawImage(
      source,
      this.offsetX, this.offsetY,
      this.w * this.scale, this.h * this.scale,
    );
    ctx.filter = 'none';
    ctx.imageSmoothingEnabled = false;
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
