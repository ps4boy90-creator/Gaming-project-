import { wrap, drawParagraph, drawText, measure, lineHeight } from '../gfx/text.js';
import { panel, INK, INK_DIM, ACCENT } from './ui.js';

const CHARS_PER_SECOND = 46;
const MIN_HOLD = 0.7;

/**
 * The moment a set of clues becomes a conclusion.
 *
 * Presented as its own card rather than as another line of monologue, because
 * it is the game's only real progression event -- in a story with no combat,
 * understanding something *is* the reward, and it should land differently from
 * an idle remark about a bookshelf.
 */
export class Realization {
  constructor(audio) {
    this.audio = audio;
    this.open = false;
    this.deduction = null;
    this.revealed = 0;
    this.held = 0;
    this.lines = [];
    this.onClose = null;
  }

  show(deduction, onClose = null) {
    this.open = true;
    this.deduction = deduction;
    this.revealed = 0;
    this.held = 0;
    this.lines = null;
    this.onClose = onClose;
    if (this.audio) this.audio.play('save');
  }

  close() {
    if (!this.open) return;
    this.open = false;
    const cb = this.onClose;
    this.deduction = null;
    this.onClose = null;
    if (cb) cb();
  }

  update(dt, input) {
    if (!this.open) return;
    const full = this.deduction.line.length;

    if (this.revealed < full) {
      this.revealed = Math.min(full, this.revealed + CHARS_PER_SECOND * dt);
      if (input.justPressed('advance')) this.revealed = full;
      return;
    }

    // A short hold before input is accepted, so a key pressed while reading
    // does not dismiss the card the instant it completes.
    this.held += dt;
    if (this.held >= MIN_HOLD && (input.justPressed('advance') || input.justPressed('cancel'))) {
      this.close();
    }
  }

  draw(ctx, w, h, portraits) {
    if (!this.open) return;

    ctx.fillStyle = 'rgba(3,4,7,0.88)';
    ctx.fillRect(0, 0, w, h);

    const boxW = Math.min(292, w - 40);
    const portrait = this.deduction.portrait && portraits && portraits[this.deduction.portrait];

    if (!this.lines) {
      const textW = boxW - 24 - (portrait ? portrait.width + 8 : 0);
      this.lines = wrap(this.deduction.line, textW);
    }

    const boxH = 46 + this.lines.length * lineHeight()
      + (portrait ? Math.max(0, portrait.height - this.lines.length * lineHeight() - 6) : 0);
    const x = Math.round((w - boxW) / 2);
    const y = Math.round((h - boxH) / 2);

    panel(ctx, x, y, boxW, boxH, { bg: 'rgba(10,12,18,0.98)', edge: ACCENT });

    const header = 'REALIZATION';
    drawText(ctx, header, x + Math.round((boxW - measure(header)) / 2), y + 8, { color: ACCENT });
    ctx.fillStyle = 'rgba(201,164,76,0.45)';
    ctx.fillRect(x + 12, y + 8 + lineHeight() + 2, boxW - 24, 1);

    let textX = x + 12;
    let top = y + 8 + lineHeight() + 9;
    if (portrait) {
      ctx.drawImage(portrait, x + 10, top);
      textX = x + 10 + portrait.width + 8;
    }

    drawParagraph(ctx, this.lines, textX, top, { color: INK, limit: Math.floor(this.revealed) });

    if (this.revealed >= this.deduction.line.length && this.held >= MIN_HOLD) {
      const hint = 'E to continue';
      drawText(ctx, hint, x + boxW - measure(hint) - 10, y + boxH - lineHeight() - 6, { color: INK_DIM });
    }
  }
}
