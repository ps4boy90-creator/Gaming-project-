import { createSurface } from '../core/screen.js';
import { makeRng } from '../core/rng.js';

/**
 * Screen-space finishing passes. Every one is individually switchable because
 * grain and scanlines are exactly the kind of effect that looks like mood to
 * one player and like eye strain to another.
 */
export class PostFX {
  constructor(w, h) {
    this.w = w;
    this.h = h;
    this.settings = {
      grain: 0.05,
      vignette: 0.55,
      scanlines: 0,
      chromatic: 0,
    };
    this.fade = { color: '#000000', amount: 0 };

    this._grainFrames = this._buildGrain(4);
    this._grainIndex = 0;
    this._grainClock = 0;
    this._vignette = this._buildVignette();
    this._scanlines = this._buildScanlines();
  }

  _buildGrain(count) {
    // Pre-rendered noise tiles cycled at a fixed rate. Generating noise per
    // frame would cost a full-screen putImageData every tick for no visual gain.
    const rng = makeRng(99);
    const frames = [];
    for (let i = 0; i < count; i++) {
      const s = createSurface(this.w, this.h);
      const img = s.ctx.createImageData(this.w, this.h);
      for (let p = 0; p < img.data.length; p += 4) {
        const v = rng() * 255;
        img.data[p] = img.data[p + 1] = img.data[p + 2] = v;
        img.data[p + 3] = 255;
      }
      s.ctx.putImageData(img, 0, 0);
      frames.push(s.canvas);
    }
    return frames;
  }

  _buildVignette() {
    const s = createSurface(this.w, this.h);
    const cx = this.w / 2;
    const cy = this.h / 2;
    const grad = s.ctx.createRadialGradient(cx, cy, Math.min(cx, cy) * 0.35, cx, cy, Math.max(cx, cy) * 1.15);
    grad.addColorStop(0, 'rgba(0,0,0,0)');
    grad.addColorStop(0.6, 'rgba(0,0,0,0.28)');
    grad.addColorStop(1, 'rgba(0,0,0,1)');
    s.ctx.fillStyle = grad;
    s.ctx.fillRect(0, 0, this.w, this.h);
    return s.canvas;
  }

  _buildScanlines() {
    const s = createSurface(this.w, this.h);
    s.ctx.fillStyle = 'rgba(0,0,0,1)';
    for (let y = 0; y < this.h; y += 2) s.ctx.fillRect(0, y, this.w, 1);
    return s.canvas;
  }

  update(dt) {
    this._grainClock += dt;
    if (this._grainClock >= 1 / 12) {
      this._grainClock = 0;
      this._grainIndex = (this._grainIndex + 1) % this._grainFrames.length;
    }
  }

  /** Fade to or from a colour; amount 0 is clear, 1 is fully covered. */
  setFade(color, amount) {
    this.fade.color = color;
    this.fade.amount = amount;
  }

  render(ctx) {
    const s = this.settings;

    if (s.grain > 0) {
      const prev = ctx.globalCompositeOperation;
      ctx.globalCompositeOperation = 'overlay';
      ctx.globalAlpha = s.grain;
      ctx.drawImage(this._grainFrames[this._grainIndex], 0, 0);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = prev;
    }

    if (s.vignette > 0) {
      ctx.globalAlpha = s.vignette;
      ctx.drawImage(this._vignette, 0, 0);
      ctx.globalAlpha = 1;
    }

    if (s.scanlines > 0) {
      ctx.globalAlpha = s.scanlines;
      ctx.drawImage(this._scanlines, 0, 0);
      ctx.globalAlpha = 1;
    }

    if (this.fade.amount > 0) {
      ctx.globalAlpha = Math.min(1, this.fade.amount);
      ctx.fillStyle = this.fade.color;
      ctx.fillRect(0, 0, this.w, this.h);
      ctx.globalAlpha = 1;
    }
  }
}
