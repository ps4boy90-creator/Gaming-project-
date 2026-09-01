import { createSurface } from '../core/screen.js';
import { makeRng, clamp } from '../core/rng.js';

/**
 * Named flicker behaviours, so a scene can ask for "fluorescent" instead of
 * hand-tuning numbers, and the editor can offer them in a dropdown.
 * Each returns a multiplier on the light's intensity for the given time.
 */
export const FLICKER = {
  steady: () => 1,
  // Slow, shallow breathing -- an oil lamp or a hearth.
  candle: (t, rng) => 0.86 + 0.14 * Math.sin(t * 5.3) * Math.sin(t * 2.1) + rng * 0.04,
  // Mostly on, with abrupt short dropouts. The signature of a failing tube.
  fluorescent: (t) => {
    const phase = (t * 0.75) % 1;
    if (phase > 0.94) return 0.15;
    if (phase > 0.90) return 0.85;
    if (phase > 0.885) return 0.25;
    return 1;
  },
  // Long dark stretches broken by a struggling flare.
  dying: (t) => {
    const phase = (t * 0.3) % 1;
    if (phase < 0.55) return 0.08;
    if (phase < 0.60) return 0.9;
    if (phase < 0.63) return 0.2;
    if (phase < 0.72) return 0.75;
    return 0.1;
  },
  pulse: (t) => 0.55 + 0.45 * (0.5 + 0.5 * Math.sin(t * 2.4)),
};

function parseColor(hex) {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

/**
 * Two-pass lighting.
 *
 * Pass one builds a darkness sheet tinted with the scene's ambient colour and
 * carves holes in it where lights fall, so lit areas become visible. Pass two
 * adds the lights' own colour back on top, which is what makes a desk lamp read
 * as warm against cold moonlight rather than merely as a brighter patch.
 */
export class Lighting {
  constructor(w, h) {
    this.w = w;
    this.h = h;
    this.dark = createSurface(w, h);
    this.glow = createSurface(w, h);
    this.rng = makeRng(20250901);
    this.time = 0;
    this.enabled = true;
  }

  update(dt) {
    this.time += dt;
  }

  intensityOf(light) {
    const fn = FLICKER[light.flicker] || FLICKER.steady;
    const base = light.intensity === undefined ? 1 : light.intensity;
    // Per-light phase offset so a row of identical tubes doesn't blink in unison.
    const phase = this.time + (light.phase || 0);
    return clamp(base * fn(phase, this.rng()), 0, 4);
  }

  /**
   * @param ctx     the scene's context, already holding the drawn artwork
   * @param ambient {color, strength} -- strength 0 is full daylight, 1 is pitch black
   * @param lights  array of {x, y, radius, color, intensity, flicker, phase, warmth}
   * @param camera  used to convert world positions to screen positions
   */
  render(ctx, ambient, lights, camera) {
    if (!this.enabled) return;

    const strength = ambient && ambient.strength !== undefined ? ambient.strength : 0;
    const tint = parseColor((ambient && ambient.color) || '#000010');

    const d = this.dark.ctx;
    d.globalCompositeOperation = 'source-over';
    d.clearRect(0, 0, this.w, this.h);
    if (strength > 0) {
      d.fillStyle = `rgba(${tint.r},${tint.g},${tint.b},${strength})`;
      d.fillRect(0, 0, this.w, this.h);
    }

    const g = this.glow.ctx;
    g.globalCompositeOperation = 'source-over';
    g.clearRect(0, 0, this.w, this.h);
    g.globalCompositeOperation = 'lighter';

    const camX = camera ? camera.drawX : 0;
    const camY = camera ? camera.drawY : 0;

    for (const light of lights || []) {
      const power = this.intensityOf(light);
      if (power <= 0.01) continue;
      const x = Math.round(light.x - camX);
      const y = Math.round(light.y - camY);
      const r = Math.max(1, light.radius || 64);
      if (x + r < 0 || x - r > this.w || y + r < 0 || y - r > this.h) continue;

      const col = parseColor(light.color || '#ffffff');

      // Carve the darkness. A soft inner plateau keeps the centre from
      // blowing out into a hard white disc.
      d.globalCompositeOperation = 'destination-out';
      const cut = d.createRadialGradient(x, y, 0, x, y, r);
      const cutA = clamp(power, 0, 1);
      cut.addColorStop(0, `rgba(0,0,0,${cutA})`);
      cut.addColorStop(0.45, `rgba(0,0,0,${cutA * 0.72})`);
      cut.addColorStop(1, 'rgba(0,0,0,0)');
      d.fillStyle = cut;
      d.fillRect(x - r, y - r, r * 2, r * 2);

      // Add the light's own colour.
      const warmth = light.warmth === undefined ? 0.5 : light.warmth;
      const glow = g.createRadialGradient(x, y, 0, x, y, r);
      const a = clamp(power * warmth, 0, 1);
      glow.addColorStop(0, `rgba(${col.r},${col.g},${col.b},${a})`);
      glow.addColorStop(0.5, `rgba(${col.r},${col.g},${col.b},${a * 0.35})`);
      glow.addColorStop(1, `rgba(${col.r},${col.g},${col.b},0)`);
      g.fillStyle = glow;
      g.fillRect(x - r, y - r, r * 2, r * 2);
    }

    d.globalCompositeOperation = 'source-over';

    ctx.drawImage(this.dark.canvas, 0, 0);
    const prev = ctx.globalCompositeOperation;
    ctx.globalCompositeOperation = 'lighter';
    ctx.drawImage(this.glow.canvas, 0, 0);
    ctx.globalCompositeOperation = prev;
  }
}
