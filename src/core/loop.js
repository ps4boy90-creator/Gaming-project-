export const TICK_HZ = 60;
export const TICK_MS = 1000 / TICK_HZ;

/**
 * Fixed-timestep loop with an interpolated render pass.
 *
 * Physics run at exactly 60 Hz regardless of the display's refresh rate, so
 * walking speed and collision behave identically on a 60 Hz laptop and a
 * 144 Hz monitor. The render callback receives `alpha`, the fraction of a tick
 * elapsed, so drawing can interpolate and still look smooth between ticks.
 */
export class Loop {
  constructor({ update, render, maxCatchUp = 5 }) {
    this.update = update;
    this.render = render;
    this.maxCatchUp = maxCatchUp;
    this.running = false;
    this.accumulator = 0;
    this.last = 0;
    this.fps = 0;
    this._frames = 0;
    this._fpsClock = 0;
    this._frame = (t) => this._step(t);
  }

  start() {
    if (this.running) return;
    this.running = true;
    this.last = performance.now();
    this.accumulator = 0;
    requestAnimationFrame(this._frame);
  }

  stop() {
    this.running = false;
  }

  _step(now) {
    if (!this.running) return;
    let delta = now - this.last;
    this.last = now;

    // A backgrounded tab returns a huge delta. Clamping stops the game from
    // simulating minutes of movement in one frame when the tab regains focus.
    if (delta > TICK_MS * this.maxCatchUp) delta = TICK_MS * this.maxCatchUp;
    this.accumulator += delta;

    while (this.accumulator >= TICK_MS) {
      this.update(TICK_MS / 1000);
      this.accumulator -= TICK_MS;
    }

    this.render(this.accumulator / TICK_MS);

    this._frames++;
    this._fpsClock += delta;
    if (this._fpsClock >= 500) {
      this.fps = Math.round((this._frames * 1000) / this._fpsClock);
      this._frames = 0;
      this._fpsClock = 0;
    }

    requestAnimationFrame(this._frame);
  }
}
