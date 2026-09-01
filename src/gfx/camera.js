import { clamp, damp } from '../core/rng.js';
import { makeRng } from '../core/rng.js';

const shakeRng = makeRng(1337);

/**
 * Follows a target within a deadzone, smoothed, and clamped to the scene
 * bounds. The deadzone stops the view sliding under small movements, which is
 * what makes a walking character feel calm rather than seasick.
 */
export class Camera {
  constructor(viewW, viewH) {
    this.viewW = viewW;
    this.viewH = viewH;
    this.x = 0;
    this.y = 0;
    this.bounds = { w: viewW, h: viewH };
    this.deadzone = { w: 64, h: 40 };
    this.smoothing = 8;
    this.shakeAmount = 0;
    this.shakeDecay = 3;
    this.shakeX = 0;
    this.shakeY = 0;
    this.pan = null;
  }

  setBounds(w, h) {
    this.bounds = { w, h };
  }

  /** Jump straight to the target, for scene entry with no visible slide. */
  snapTo(tx, ty) {
    this.x = tx - this.viewW / 2;
    this.y = ty - this.viewH / 2;
    this._clamp();
  }

  shake(amount, decay = 3) {
    this.shakeAmount = Math.max(this.shakeAmount, amount);
    this.shakeDecay = decay;
  }

  /** A scripted move from the current position, used by cutscenes. */
  panTo(x, y, duration) {
    this.pan = { fromX: this.x, fromY: this.y, toX: x, toY: y, t: 0, duration };
  }

  follow(tx, ty, dt) {
    if (this.pan) return;
    const cx = this.x + this.viewW / 2;
    const cy = this.y + this.viewH / 2;
    const dx = tx - cx;
    const dy = ty - cy;
    const hw = this.deadzone.w / 2;
    const hh = this.deadzone.h / 2;

    let goalX = this.x;
    let goalY = this.y;
    if (dx > hw) goalX = this.x + (dx - hw);
    else if (dx < -hw) goalX = this.x + (dx + hw);
    if (dy > hh) goalY = this.y + (dy - hh);
    else if (dy < -hh) goalY = this.y + (dy + hh);

    this.x = damp(this.x, goalX, this.smoothing, dt);
    this.y = damp(this.y, goalY, this.smoothing, dt);
    this._clamp();
  }

  update(dt) {
    if (this.pan) {
      this.pan.t += dt;
      // Smoothstep: a linear pan starts and stops with a visible jolt.
      const raw = clamp(this.pan.t / this.pan.duration, 0, 1);
      const e = raw * raw * (3 - 2 * raw);
      this.x = this.pan.fromX + (this.pan.toX - this.pan.fromX) * e;
      this.y = this.pan.fromY + (this.pan.toY - this.pan.fromY) * e;
      if (raw >= 1) this.pan = null;
    }

    if (this.shakeAmount > 0.01) {
      this.shakeX = (shakeRng() * 2 - 1) * this.shakeAmount;
      this.shakeY = (shakeRng() * 2 - 1) * this.shakeAmount;
      this.shakeAmount = Math.max(0, this.shakeAmount - this.shakeDecay * dt * this.shakeAmount);
      if (this.shakeAmount < 0.05) this.shakeAmount = 0;
    } else {
      this.shakeX = 0;
      this.shakeY = 0;
    }
  }

  _clamp() {
    // A scene smaller than the view is centred rather than pinned to a corner.
    this.x = this.bounds.w <= this.viewW
      ? (this.bounds.w - this.viewW) / 2
      : clamp(this.x, 0, this.bounds.w - this.viewW);
    this.y = this.bounds.h <= this.viewH
      ? (this.bounds.h - this.viewH) / 2
      : clamp(this.y, 0, this.bounds.h - this.viewH);
  }

  /** Integer scroll offset for drawing. Fractional values blur the pixel grid. */
  get drawX() { return Math.round(this.x + this.shakeX); }
  get drawY() { return Math.round(this.y + this.shakeY); }
}
