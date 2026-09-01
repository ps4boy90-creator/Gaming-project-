import { wrap, drawParagraph, lineHeight, totalChars } from '../gfx/text.js';
import { panel, INK, INK_DIM, ACCENT } from './ui.js';

const CHARS_PER_SECOND = 42;
const HOLD_AFTER_COMPLETE = 1.6;

/**
 * The protagonist's inner monologue: a queue of short lines along the bottom
 * of the screen, revealed a character at a time. Lines can carry a portrait
 * name, which is what the reference sheet's five expressions are for.
 *
 * Lines advance on their own so walking is never interrupted, but pressing the
 * advance key skips ahead for players who read faster.
 */
export class Dialogue {
  constructor(portraits = {}) {
    this.portraits = portraits;
    this.queue = [];
    this.current = null;
    this.revealed = 0;
    this.holding = 0;
  }

  get active() {
    return !!this.current;
  }

  say(text, { portrait = '', speaker = '' } = {}) {
    if (!text) return;
    this.queue.push({ text: String(text), portrait, speaker });
    if (!this.current) this._next();
  }

  clear() {
    this.queue.length = 0;
    this.current = null;
  }

  _next() {
    this.current = this.queue.shift() || null;
    this.revealed = 0;
    this.holding = 0;
  }

  update(dt, input) {
    if (!this.current) return;

    const chars = this.current.text.length;
    if (this.revealed < chars) {
      this.revealed = Math.min(chars, this.revealed + CHARS_PER_SECOND * dt);
      // First press completes the line, second moves on.
      if (input && input.justPressed('advance')) this.revealed = chars;
    } else {
      this.holding += dt;
      const done = this.holding >= HOLD_AFTER_COMPLETE || (input && input.justPressed('advance'));
      if (done) this._next();
    }
  }

  draw(ctx, w, h) {
    if (!this.current) return;

    const portrait = this.current.portrait && this.portraits[this.current.portrait];
    const boxH = 40;
    const y = h - boxH - 6;
    const x = 8;
    const boxW = w - 16;
    panel(ctx, x, y, boxW, boxH);

    let textX = x + 7;
    let textW = boxW - 14;
    if (portrait) {
      // The portrait overhangs the top of the box so the face is not boxed in.
      const px = x + 5;
      const py = y + boxH - 3 - portrait.height;
      ctx.drawImage(portrait, px, py);
      textX = px + portrait.width + 7;
      textW = x + boxW - textX - 7;
    }

    let top = y + 7;
    if (this.current.speaker) {
      drawParagraph(ctx, [this.current.speaker], textX, top, { color: ACCENT });
      top += lineHeight();
    }

    const lines = wrap(this.current.text, textW);
    drawParagraph(ctx, lines, textX, top, { color: INK, limit: Math.floor(this.revealed) });

    if (this.revealed >= this.current.text.length) {
      const blink = Math.floor(performance.now() / 400) % 2 === 0;
      if (blink) {
        drawParagraph(ctx, ['>'], x + boxW - 12, y + boxH - lineHeight() - 5, { color: INK_DIM });
      }
    }
  }

  static charsIn(text, width) {
    return totalChars(wrap(text, width));
  }
}
