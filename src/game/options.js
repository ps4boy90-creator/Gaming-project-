import { drawText, measure, lineHeight } from '../gfx/text.js';
import { panel, INK, INK_DIM, ACCENT } from './ui.js';
import { clamp } from '../core/rng.js';

const KEY = 'veridian.options.v1';

/**
 * Settings the player needs to be able to reach.
 *
 * Two of these are not preferences but accessibility: music that cannot be
 * muted, and a whole-game band-limit to 300 Hz - 3.5 kHz that some people will
 * find unlistenable rather than atmospheric. The radio row goes to zero and
 * bypasses the chain entirely.
 *
 * Kept in its own localStorage key rather than in the save, so settings survive
 * starting a new game.
 */
export const ROWS = [
  { key: 'volume', label: 'Master volume', min: 0, max: 1, step: 0.05 },
  { key: 'music', label: 'Music', min: 0, max: 1, step: 0.05 },
  { key: 'radio', label: 'Radio', min: 0, max: 1, step: 0.05,
    help: '0 bypasses the 1950s set entirely' },
  { key: 'grain', label: 'Film grain', min: 0, max: 0.2, step: 0.01 },
  { key: 'scanlines', label: 'Scanlines', min: 0, max: 0.5, step: 0.05 },
  { key: 'vignette', label: 'Vignette', min: 0, max: 1, step: 0.05 },
];

export const DEFAULTS = {
  volume: 0.7, music: 0.8, radio: 1, grain: 0.05, scanlines: 0, vignette: 0.55,
};

export class Options {
  constructor(audio, postfx) {
    this.audio = audio;
    this.postfx = postfx;
    this.open = false;
    this.index = 0;
    this.values = { ...DEFAULTS, ...Options.read() };
    this.apply();
  }

  static read() {
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (err) {
      return {};
    }
  }

  save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(this.values));
    } catch (err) {
      console.warn('Could not save options:', err);
    }
  }

  /** Push every value into the systems that own it. */
  apply() {
    this.audio.setVolume(this.values.volume);
    this.audio.setMusicVolume(this.values.music);
    this.audio.setRadioAmount(this.values.radio);
    this.postfx.settings.grain = this.values.grain;
    this.postfx.settings.scanlines = this.values.scanlines;
    this.postfx.settings.vignette = this.values.vignette;
  }

  show() {
    this.open = true;
    this.index = 0;
  }

  close() {
    this.open = false;
    this.save();
  }

  update(dt, input) {
    if (!this.open) return;

    if (input.justPressed('cancel') || input.justPressed('options')) {
      this.close();
      return;
    }
    if (input.justPressed('up')) {
      this.index = (this.index - 1 + ROWS.length) % ROWS.length;
      this.audio.play('blip');
    }
    if (input.justPressed('down')) {
      this.index = (this.index + 1) % ROWS.length;
      this.audio.play('blip');
    }

    // Discrete presses, not held state: a quick tap can have its keyup land in
    // the same tick as its keydown.
    const dir = (input.justPressed('right') ? 1 : 0) - (input.justPressed('left') ? 1 : 0);
    if (dir !== 0) {
      const row = ROWS[this.index];
      this.values[row.key] = clamp(
        Math.round((this.values[row.key] + dir * row.step) / row.step) * row.step,
        row.min, row.max,
      );
      this.apply();
      this.audio.play('blip');
    }
  }

  draw(ctx, w, h) {
    if (!this.open) return;

    ctx.fillStyle = 'rgba(5,6,10,0.90)';
    ctx.fillRect(0, 0, w, h);

    const boxW = 250;
    const boxH = 34 + ROWS.length * (lineHeight() + 4) + 18;
    const x = Math.round((w - boxW) / 2);
    const y = Math.round((h - boxH) / 2);
    panel(ctx, x, y, boxW, boxH);

    drawText(ctx, 'OPTIONS', x + Math.round((boxW - measure('OPTIONS')) / 2), y + 8, { color: ACCENT });
    ctx.fillStyle = 'rgba(201,164,76,0.35)';
    ctx.fillRect(x + 10, y + 8 + lineHeight() + 2, boxW - 20, 1);

    ROWS.forEach((row, i) => {
      const ry = y + 26 + i * (lineHeight() + 4);
      const selected = i === this.index;
      if (selected) {
        ctx.fillStyle = 'rgba(201,164,76,0.16)';
        ctx.fillRect(x + 6, ry - 2, boxW - 12, lineHeight() + 3);
      }
      drawText(ctx, row.label, x + 12, ry, { color: selected ? ACCENT : INK });

      // A ten-cell meter reads faster than a number at this resolution.
      const cells = 10;
      const filled = Math.round(((this.values[row.key] - row.min) / (row.max - row.min)) * cells);
      const mx = x + boxW - 12 - cells * 7;
      for (let c = 0; c < cells; c++) {
        ctx.fillStyle = c < filled ? (selected ? ACCENT : INK) : '#2c2e38';
        ctx.fillRect(mx + c * 7, ry + 1, 5, 5);
      }
    });

    const row = ROWS[this.index];
    const hint = row.help || 'LEFT/RIGHT adjust   ESC close';
    drawText(ctx, hint, x + Math.round((boxW - measure(hint)) / 2), y + boxH - lineHeight() - 6,
      { color: INK_DIM });
  }
}
