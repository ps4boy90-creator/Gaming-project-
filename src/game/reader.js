import { wrap, drawParagraph, drawText, lineHeight, measure } from '../gfx/text.js';
import { panel, INK, INK_DIM, ACCENT } from './ui.js';

const CHARS_PER_SECOND = 90;

/**
 * The full-screen reading overlay for notes and terminals. Gameplay pauses
 * while it is open -- there is nothing to be ambushed by, and forcing the
 * player to read on the move would only make them miss the story.
 */
export class Reader {
  constructor(portraits = {}) {
    this.portraits = portraits;
    this.open = false;
    this.title = '';
    this.pages = [];
    this.page = 0;
    this.revealed = 0;
    this.portrait = '';
    this.onClose = null;
    this._lines = [];
  }

  show({ title, pages, portrait = '' }, onClose = null) {
    this.open = true;
    this.title = title || '';
    this.pages = (Array.isArray(pages) ? pages : [pages]).filter((p) => p !== undefined && p !== null);
    if (this.pages.length === 0) this.pages = [''];
    this.page = 0;
    this.revealed = 0;
    this.portrait = portrait;
    this.onClose = onClose;
    this._lines = null;
  }

  close() {
    if (!this.open) return;
    this.open = false;
    const cb = this.onClose;
    this.onClose = null;
    if (cb) cb();
  }

  get atLastPage() {
    return this.page >= this.pages.length - 1;
  }

  update(dt, input) {
    if (!this.open) return;

    const text = String(this.pages[this.page] || '');
    if (this.revealed < text.length) {
      this.revealed = Math.min(text.length, this.revealed + CHARS_PER_SECOND * dt);
      if (input.justPressed('advance')) this.revealed = text.length;
    } else if (input.justPressed('advance')) {
      if (this.atLastPage) {
        this.close();
        return;
      }
      this.page++;
      this.revealed = 0;
      this._lines = null;
    }

    if (input.justPressed('cancel')) this.close();
  }

  draw(ctx, w, h) {
    if (!this.open) return;

    ctx.fillStyle = 'rgba(4,5,9,0.82)';
    ctx.fillRect(0, 0, w, h);

    const boxW = Math.min(300, w - 32);
    const boxH = Math.min(150, h - 40);
    const x = Math.round((w - boxW) / 2);
    const y = Math.round((h - boxH) / 2);
    panel(ctx, x, y, boxW, boxH, { bg: 'rgba(12,13,20,0.97)' });

    let textX = x + 10;
    let textW = boxW - 20;
    let top = y + 9;

    if (this.title) {
      drawText(ctx, this.title, textX, top, { color: ACCENT });
      ctx.fillStyle = 'rgba(201,164,76,0.35)';
      ctx.fillRect(textX, top + lineHeight(), textW, 1);
      top += lineHeight() + 6;
    }

    const portrait = this.portrait && this.portraits[this.portrait];
    if (portrait) {
      ctx.drawImage(portrait, x + boxW - portrait.width - 8, y + boxH - portrait.height - 8);
      textW -= portrait.width + 6;
    }

    if (!this._lines) this._lines = wrap(String(this.pages[this.page] || ''), textW);
    drawParagraph(ctx, this._lines, textX, top, { color: INK, limit: Math.floor(this.revealed) });

    const hint = this.pages.length > 1
      ? `${this.page + 1}/${this.pages.length}   E next   ESC close`
      : 'E close';
    drawText(ctx, hint, x + boxW - measure(hint) - 9, y + boxH - lineHeight() - 6, { color: INK_DIM });
  }
}
