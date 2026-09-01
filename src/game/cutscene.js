import { clamp } from '../core/rng.js';
import { wrap, drawParagraph, drawTextShadowed, lineHeight, measure } from '../gfx/text.js';
import { INK, ACCENT } from './ui.js';
import { SCENE_FX } from './cutscene_fx.js';
import { CUTSCENE_W, CUTSCENE_H } from '../core/screen.js';

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
 *   { fx: 'wake', phase: 'sit' }       run an animated painter (cutscene_fx.js)
 *
 * A step with `fx` repaints the frame every tick instead of showing a still,
 * and `phase` names which beat of that animation it is. The pan, the letterbox
 * and the text all work exactly the same over it -- an animated beat and a
 * painted one are the same kind of thing to everything else.
 */
export class Cutscene {
  constructor(assets, audio, postfx) {
    this.assets = assets;
    this.audio = audio;
    this.postfx = postfx;
    this.active = false;
    this.def = null;
    this.image = null;
    this.prevImage = null;
    this.crossfade = 0;      // 1 fully on the previous still, 0 fully on the new
    this.crossfadeFor = 0;
    this.letterbox = true;
    this.step = 0;
    this.time = 0;
    /** Seconds since the cutscene started, for animation that spans steps. */
    this.clock = 0;
    this.fx = null;
    this.fxPhase = null;
    this.fxCache = {};
    this.fxSurface = null;
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
    this.clock = 0;
    // A painter's cached layers belong to one playing of one cutscene: the
    // forest strips are built for the frame size and the scratch surface holds
    // the last figure drawn.
    this.fxCache = {};
    this.fx = def.fx ? SCENE_FX[def.fx] || null : null;
    this.fxPhase = def.phase || null;
    this.text = null;
    this.textTime = 0;
    this.prevImage = null;
    this.crossfade = 0;
    this.letterbox = def.letterbox !== false;
    this.onDone = onDone;
    this.skippable = def.skippable !== false;

    const startView = def.view || (this.image
      ? { x: 0, y: 0, w: this.image.width, h: this.image.height }
      : { x: 0, y: 0, w: CUTSCENE_W, h: CUTSCENE_H });
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

    if (s.image !== undefined) {
      // Cutting to a new still cross-fades from the old one rather than
      // snapping, so a beat can be built from several images.
      const next = s.image && this.assets.images.has(s.image)
        ? this.assets.image(s.image) : null;
      if (next !== this.image) {
        this.prevImage = this.image;
        this.image = next;
        this.crossfadeFor = s.duration || 0.8;
        this.crossfade = this.prevImage ? 1 : 0;
      }
      if (s.view) {
        this.view = { ...s.view };
        this.viewFrom = { ...s.view };
      }
    }
    if (s.fx !== undefined) {
      this.fx = s.fx ? SCENE_FX[s.fx] || null : null;
      if (!this.fx && s.fx) console.warn(`Cutscene "${this.def.id}": no painter "${s.fx}"`);
    }
    if (s.phase !== undefined) this.fxPhase = s.phase;
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
    this.clock += dt;
    this.textTime += dt;
    if (this.crossfade > 0) {
      this.crossfade = Math.max(0, this.crossfade - dt / Math.max(0.05, this.crossfadeFor));
      if (this.crossfade === 0) this.prevImage = null;
    }

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

  /**
   * Run the active painter into an offscreen frame the size of the still it is
   * standing in for. Returns the canvas, or null when this beat is a still.
   */
  _paintFx(w, h) {
    if (!this.fx) return null;
    const size = this.view && this.view.w
      ? { w: Math.max(w, Math.round(this.view.w)), h: Math.max(h, Math.round(this.view.h)) }
      : { w, h };
    if (!this.fxSurface || this.fxSurface.canvas.width !== size.w
      || this.fxSurface.canvas.height !== size.h) {
      const canvas = document.createElement('canvas');
      canvas.width = size.w;
      canvas.height = size.h;
      const ctx = canvas.getContext('2d');
      ctx.imageSmoothingEnabled = false;
      this.fxSurface = { canvas, ctx };
      this.fxCache = {};        // layers are built for a size
    }
    const steps = (this.def && this.def.steps) || [];
    const s = steps[this.step] || {};
    const T = s.duration || 0;
    const t = this.time;
    const raw = T > 0 ? clamp(t / T, 0, 1) : 1;
    this.fx.draw(this.fxSurface.ctx, {
      w: size.w,
      h: size.h,
      phase: this.fxPhase,
      t,
      T,
      k: raw * raw * (3 - 2 * raw),
      clock: this.clock,
      assets: this.assets,
      audio: this.audio,
      cache: this.fxCache,
    });
    return this.fxSurface.canvas;
  }

  draw(ctx, w, h) {
    if (!this.active) return;

    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, w, h);

    const blit = (image, alpha) => {
      if (!image || !this.view || alpha <= 0) return;
      // Round the source rect: a fractional source on a scaled draw makes the
      // pixel art crawl during a slow pan.
      const sx = Math.round(this.view.x);
      const sy = Math.round(this.view.y);
      const sw = Math.round(this.view.w);
      const sh = Math.round(this.view.h);
      const prev = ctx.globalAlpha;
      ctx.globalAlpha = prev * alpha;
      ctx.drawImage(image, sx, sy, sw, sh, 0, 0, w, h);
      ctx.globalAlpha = prev;
    };
    // An animated beat paints a full frame of its own, which is then shown
    // through the same view window as a still -- so a painter never has to know
    // anything about panning, and a pan works over animation for free.
    const painted = this._paintFx(w, h);
    blit(painted, 1);
    blit(this.image, painted ? 0 : 1);
    blit(this.prevImage, this.crossfade);

    if (this.letterbox) {
      // 2.39:1 bars. Cutscenes are the only place the frame changes shape,
      // which is most of what tells the player they are not in control.
      const bar = Math.round((h - w / 2.39) / 2);
      if (bar > 0) {
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, w, bar);
        ctx.fillRect(0, h - bar, w, bar);
      }
    }

    if (this.text) {
      const reveal = Math.min(1, this.textTime / 0.9);
      const prev = ctx.globalAlpha;
      ctx.globalAlpha = prev * reveal;

      // The bitmap font draws at a fixed pixel size, so on the higher-resolution
      // cutscene surface it would come out half as large relative to the frame.
      // Scale the transform and work in logical units, which also keeps the
      // glyphs on whole pixels instead of resampling them.
      const k = Math.max(1, Math.round(w / 384));
      ctx.save();
      if (k > 1) ctx.scale(k, k);
      w = Math.round(w / k);
      h = Math.round(h / k);

      if (this.textStyle === 'narration') {
        // Centred in the frame, in the narrator's voice rather than Hale's.
        // Deliberately not the gold used for titles and prompts: this sits
        // above the story, not inside its interface.
        const lines = wrap(this.text, w - 72);
        const blockH = lines.length * lineHeight();
        const top = Math.round(h / 2 - blockH / 2);

        // A scrim behind the block, fading out sideways. Narration is centred
        // in the frame and the frame is often brightest in the middle -- the
        // aperture is a white arch right where the words go. Feathered darkness
        // reads as a shadow falling across the picture; a rectangle would read
        // as a dialogue box.
        const scrimTop = top - 14;
        const scrimH = blockH + 28;
        const scrim = ctx.createLinearGradient(0, 0, w, 0);
        scrim.addColorStop(0, 'rgba(4,5,9,0)');
        scrim.addColorStop(0.5, 'rgba(4,5,9,1)');
        scrim.addColorStop(1, 'rgba(4,5,9,0)');
        ctx.fillStyle = scrim;
        const alpha = ctx.globalAlpha;
        for (let row = 0; row < scrimH; row++) {
          // Feathered on the vertical too, by modulating alpha per row: a band
          // with hard top and bottom edges is a letterbox, not a shadow.
          const t = row / (scrimH - 1);
          ctx.globalAlpha = alpha * 0.82 * Math.sin(Math.PI * t) ** 0.7;
          ctx.fillRect(0, scrimTop + row, w, 1);
        }
        ctx.globalAlpha = alpha;

        lines.forEach((line, i) => {
          // Shadowed rather than plated: narration sits in the picture, and a
          // panel behind it would make it part of the interface. It still has
          // to survive landing on the brightest thing in the frame.
          drawTextShadowed(ctx, line, Math.round((w - measure(line)) / 2),
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
        // Sit above the letterbox bar rather than behind it.
        const bar = this.letterbox ? Math.max(0, Math.round((h - w / 2.39) / 2)) : 0;
        const top = h - bar - 14 - lines.length * lineHeight();
        ctx.fillStyle = 'rgba(4,5,9,0.62)';
        ctx.fillRect(0, top - 6, w, lines.length * lineHeight() + 12);
        lines.forEach((line, i) => {
          drawParagraph(ctx, [line], Math.round((w - measure(line)) / 2), top + i * lineHeight(), { color: INK });
        });
      }
      ctx.restore();
      ctx.globalAlpha = prev;
    }
  }
}
