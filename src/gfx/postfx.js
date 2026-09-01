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
      grain: 0.06,
      vignette: 0.68,
      // The reference is a 1960s anthology broadcast, so the set is on by
      // default now rather than off.
      scanlines: 0.22,
      broadcast: 1,
      chromatic: 0,
    };
    this.fade = { color: '#000000', amount: 0 };

    /**
     * How badly the signal is holding, 0..1. Driven from the same value as the
     * radio, so the picture degrades in step with the sound as the player works
     * more out -- one idea expressed twice rather than two unrelated effects.
     */
    this.tension = 0;

    this._grainFrames = this._buildGrain(4);
    this._grainIndex = 0;
    this._grainClock = 0;
    this._vignette = this._buildVignette();
    this._scanlines = this._buildScanlines();

    this._rng = makeRng(1961);
    this._rollY = 0;
    this._tear = null;
    this._tearIn = 9;
    this._scratch = createSurface(this.w, this.h);
  }

  setTension(t) {
    this.tension = Math.max(0, Math.min(1, t));
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

    // Vertical hold drifting: the band creeps down faster as the signal worsens.
    const rollSpeed = 6 + this.tension * 26;
    this._rollY = (this._rollY + rollSpeed * dt) % (this.h + 60);

    if (this._tear) {
      this._tear.life -= dt;
      if (this._tear.life <= 0) this._tear = null;
    } else {
      this._tearIn -= dt;
      if (this._tearIn <= 0) {
        // Frequent and violent only once he understands what happened.
        this._tear = {
          y: Math.floor(this._rng() * this.h),
          h: 3 + Math.floor(this._rng() * (4 + this.tension * 20)),
          dx: Math.round((this._rng() * 2 - 1) * (2 + this.tension * 14)),
          life: 0.05 + this._rng() * 0.12,
        };
        this._tearIn = (14 - this.tension * 11) * (0.4 + this._rng());
      }
    }
  }

  /** Fade to or from a colour; amount 0 is clear, 1 is fully covered. */
  setFade(color, amount) {
    this.fade.color = color;
    this.fade.amount = amount;
  }

  render(ctx) {
    const s = this.settings;

    // Signal artefacts first, so grain and scanlines land on top of a torn
    // frame rather than being torn along with it.
    if (s.broadcast > 0 && this._tear) {
      const t = this._tear;
      // Copy through a scratch surface: reading and writing the same canvas in
      // one drawImage is well defined but the overlapping case is not worth
      // relying on across browsers.
      const sc = this._scratch.ctx;
      sc.clearRect(0, 0, this.w, this.h);
      sc.drawImage(ctx.canvas, 0, 0);
      ctx.clearRect(0, t.y, this.w, t.h);
      ctx.drawImage(this._scratch.canvas, 0, t.y, this.w, t.h,
        t.dx * s.broadcast, t.y, this.w, t.h);
    }

    if (s.broadcast > 0) {
      // The roll: a soft bright band easing down the frame, the way a set with
      // failing vertical hold behaves.
      const y = this._rollY - 30;
      const grad = ctx.createLinearGradient(0, y, 0, y + 60);
      const a = 0.05 * s.broadcast * (0.6 + this.tension * 0.8);
      grad.addColorStop(0, 'rgba(255,255,255,0)');
      grad.addColorStop(0.5, `rgba(255,255,255,${a.toFixed(4)})`);
      grad.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, y, this.w, 60);
    }

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
