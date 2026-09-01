import { clamp } from '../core/rng.js';
import { wrap, drawParagraph, lineHeight, measure } from '../gfx/text.js';
import { INK, ACCENT } from './ui.js';

/**
 * Plays a scripted sequence over a single full-screen still.
 *
 * The facility arrival is the reason this exists: the establishing artwork is
 * an isometric view that gameplay never uses, so it is shown as a slow pan
 * with a title card before the side-scrolling scene begins.
 *
 * A step may set several things at once (pan while a card is up). `duration`
 * is how long the step holds; 0 applies it and moves straight on.
 *
 *   { view: {x,y,w,h}, duration: 6 }   pan/zoom the window over the still
 *   { text: 'LINE', style: 'title' }   show a card; text: null clears it
 *   { fadeTo: 0, duration: 2 }         fade from black
 *   { sound: 'door' } { ambience: 'forest_night' }
 *   { waitForKey: true }               hold until the player presses a key
 */
export class Cutscene {
  constructor(assets, audio, postfx) {
    this.assets = assets;
    this.audio = audio;
    this.postfx = postfx;
    this.active = false;
    this.def = null;
    this.image = null;
    this.step = 0;
    this.time = 0;
    this.view = null;
    this.viewFrom = null;
    this.text = null;
    this.textStyle = 'card';
    this.textTime = 0;
    this.fadeFrom = 0;
    this.fadeTo = 0;
    this.onDone = null;
    this.skippable = true;
  }

  play(def, onDone = null) {
    this.def = def;
    // A cutscene is fired from inside a trigger, so there is nowhere to await a
    // load and nothing useful to do with a throw. Play it over black instead.
    this.image = null;
    if (def.image) {
      if (this.assets.images.has(def.image)) {
        this.image = this.assets.image(def.image);
      } else {
        console.warn(`Cutscene "${def.id}" still not preloaded: ${def.image}`);
      }
    }
    this.active = true;
    this.step = -1;
    this.time = 0;
    this.text = null;
    this.textTime = 0;
    this.onDone = onDone;
    this.skippable = def.skippable !== false;

    const startView = def.view || (this.image
      ? { x: 0, y: 0, w: this.image.width, h: this.image.height }
      : { x: 0, y: 0, w: 384, h: 216 });
    this.view = { ...startView };
    this.viewFrom = { ...startView };

    this.fadeFrom = def.fadeFrom === undefined ? 1 : def.fadeFrom;
    this.fadeTo = this.fadeFrom;
    if (this.postfx) this.postfx.setFade(def.fadeColor || '#000000', this.fadeFrom);
    if (def.ambience && this.audio) this.audio.setAmbience(def.ambience);

    this._advance();
  }

  stop() {
    this.active = false;
    if (this.postfx) this.postfx.setFade('#000000', 0);
    const cb = this.onDone;
    this.onDone = null;
    if (cb) cb();
  }

  _advance() {
    this.step++;
    this.time = 0;
    const steps = (this.def && this.def.steps) || [];
    if (this.step >= steps.length) {
      this.stop();
      return;
    }

    const s = steps[this.step];
    this.viewFrom = { ...this.view };
    this.fadeFrom = this.fadeTo;

    if (s.text !== undefined) {
      this.text = s.text;
      this.textStyle = s.style || 'card';
      this.textTime = 0;
    }
    if (s.fadeTo !== undefined) this.fadeTo = s.fadeTo;
    if (s.sound && this.audio) this.audio.play(s.sound);
    if (s.ambience && this.audio) this.audio.setAmbience(s.ambience);
    if (s.shake && this.onShake) this.onShake(s.shake);

    // An instant step with nothing to wait for should not cost a frame.
    if (!s.duration && !s.waitForKey) this._advance();
  }

  update(dt, input) {
    if (!this.active) return;
    const steps = this.def.steps || [];
    const s = steps[this.step];
    if (!s) { this.stop(); return; }

    this.time += dt;
    this.textTime += dt;

    const duration = s.duration || 0;
    const t = duration > 0 ? clamp(this.time / duration, 0, 1) : 1;
    const eased = t * t * (3 - 2 * t);

    if (s.view) {
      for (const k of ['x', 'y', 'w', 'h']) {
        const from = this.viewFrom[k];
        const to = s.view[k] === undefined ? from : s.view[k];
        this.view[k] = from + (to - from) * eased;
      }
    }
    if (this.postfx && s.fadeTo !== undefined) {
      this.postfx.setFade(s.fadeColor || this.def.fadeColor || '#000000',
        this.fadeFrom + (this.fadeTo - this.fadeFrom) * t);
    }

    if (this.skippable && input.justPressed('cancel')) {
      this.stop();
      return;
    }

    const keyDone = s.waitForKey ? input.justPressed('advance') : true;
    if (t >= 1 && keyDone) this._advance();
  }

  draw(ctx, w, h) {
    if (!this.active) return;

    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, w, h);

    if (this.image && this.view) {
      // Round the source rect: a fractional source on a scaled draw makes the
      // pixel art crawl during a slow pan.
      const sx = Math.round(this.view.x);
      const sy = Math.round(this.view.y);
      const sw = Math.round(this.view.w);
      const sh = Math.round(this.view.h);
      ctx.drawImage(this.image, sx, sy, sw, sh, 0, 0, w, h);
    }

    if (this.text) {
      const reveal = Math.min(1, this.textTime / 0.9);
      const prev = ctx.globalAlpha;
      ctx.globalAlpha = prev * reveal;

      if (this.textStyle === 'narration') {
        // Centred in the frame, in the narrator's voice rather than Hale's.
        // Deliberately not the gold used for titles and prompts: this sits
        // above the story, not inside its interface.
        const lines = wrap(this.text, w - 72);
        const blockH = lines.length * lineHeight();
        const top = Math.round(h / 2 - blockH / 2);
        lines.forEach((line, i) => {
          drawParagraph(ctx, [line], Math.round((w - measure(line)) / 2),
            top + i * lineHeight(), { color: INK });
        });
      } else if (this.textStyle === 'title') {
        const lines = wrap(this.text, w - 40);
        const blockH = lines.length * lineHeight();
        const top = Math.round(h / 2 - blockH / 2);
        ctx.fillStyle = 'rgba(4,5,9,0.55)';
        ctx.fillRect(0, top - 10, w, blockH + 20);
        lines.forEach((line, i) => {
          drawParagraph(ctx, [line], Math.round((w - measure(line)) / 2), top + i * lineHeight(), { color: ACCENT });
        });
      } else {
        const lines = wrap(this.text, w - 48);
        const top = h - 22 - lines.length * lineHeight();
        ctx.fillStyle = 'rgba(4,5,9,0.62)';
        ctx.fillRect(0, top - 6, w, lines.length * lineHeight() + 12);
        lines.forEach((line, i) => {
          drawParagraph(ctx, [line], Math.round((w - measure(line)) / 2), top + i * lineHeight(), { color: INK });
        });
      }
      ctx.globalAlpha = prev;
    }
  }
}
