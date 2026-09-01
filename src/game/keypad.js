import { drawText, measure } from '../gfx/text.js';
import { panel, INK, INK_DIM, ACCENT } from './ui.js';

const DIGIT_CODES = ['Digit0', 'Digit1', 'Digit2', 'Digit3', 'Digit4',
  'Digit5', 'Digit6', 'Digit7', 'Digit8', 'Digit9'];

/**
 * A four-digit lock.
 *
 * This exists so the central clue can *be* the key: the only way to know the
 * code is to have worked out when everything stopped. Typing 0614 yourself is
 * a different feeling from walking into a door that silently opens because a
 * flag was set.
 */
export class Keypad {
  constructor(audio) {
    this.audio = audio;
    this.open = false;
    this.entity = null;
    this.entry = '';
    this.message = '';
    this.messageTime = 0;
    this.shake = 0;
    this.onResult = null;
  }

  show(entity, onResult = null) {
    this.open = true;
    this.entity = entity;
    this.entry = '';
    this.message = '';
    this.messageTime = 0;
    this.shake = 0;
    this.onResult = onResult;
  }

  close() {
    this.open = false;
    this.entity = null;
    this.onResult = null;
  }

  get codeLength() {
    return this.entity ? String(this.entity.props.code || '').length : 4;
  }

  update(dt, input, api) {
    if (!this.open) return;

    this.messageTime = Math.max(0, this.messageTime - dt);
    this.shake = Math.max(0, this.shake - dt * 26);

    if (input.justPressed('cancel')) {
      this.close();
      return;
    }

    if (input.justPressed('backspace')) {
      this.entry = this.entry.slice(0, -1);
      if (this.audio) this.audio.play('blip');
      return;
    }

    for (let d = 0; d < 10; d++) {
      // Only the just-pressed set: a quick tap can have its keyup processed in
      // the same tick as its keydown, which clears `down` before this runs.
      if (!input.pressed.has(DIGIT_CODES[d])) continue;
      if (this.entry.length >= this.codeLength) break;
      this.entry += String(d);
      if (this.audio) this.audio.play('blip');
      // Submit on the last digit rather than making the player find Enter.
      if (this.entry.length === this.codeLength) this._submit(api);
      break;
    }

    if (input.justPressed('advance') && this.entry.length === this.codeLength) {
      this._submit(api);
    }
  }

  _submit(api) {
    const p = this.entity.props;
    if (this.entry === String(p.code)) {
      if (this.audio) this.audio.play('save');
      if (p.setsFlag) api.flags.set(p.setsFlag);
      this.message = 'ACCEPTED';
      const text = p.successText;
      this.close();
      api.dialogue.say(text || 'The bolt draws back.', { portrait: 'resolute' });
      return;
    }
    if (this.audio) this.audio.play('locked');
    this.entry = '';
    this.message = p.wrongText || 'Three short beeps. Not that.';
    this.messageTime = 2.4;
    this.shake = 4;
  }

  draw(ctx, w, h) {
    if (!this.open) return;

    ctx.fillStyle = 'rgba(4,5,9,0.78)';
    ctx.fillRect(0, 0, w, h);

    const boxW = 150;
    const boxH = 92;
    const x = Math.round((w - boxW) / 2 + (this.shake ? (Math.random() * 2 - 1) * this.shake : 0));
    const y = Math.round((h - boxH) / 2);
    panel(ctx, x, y, boxW, boxH, { bg: 'rgba(12,14,20,0.98)' });

    const title = this.entity.props.prompt || 'Keypad';
    drawText(ctx, title, x + Math.round((boxW - measure(title)) / 2), y + 9, { color: ACCENT });

    // The entry field: one lit cell per digit, so the code's length is obvious.
    const cells = this.codeLength;
    const cellW = 20;
    const gap = 5;
    const totalW = cells * cellW + (cells - 1) * gap;
    const cx = x + Math.round((boxW - totalW) / 2);
    const cy = y + 28;
    for (let i = 0; i < cells; i++) {
      const filled = i < this.entry.length;
      const px = cx + i * (cellW + gap);
      ctx.fillStyle = filled ? 'rgba(201,164,76,0.22)' : 'rgba(255,255,255,0.05)';
      ctx.fillRect(px, cy, cellW, 22);
      ctx.strokeStyle = filled ? ACCENT : '#3a3c48';
      ctx.lineWidth = 1;
      ctx.strokeRect(px + 0.5, cy + 0.5, cellW - 1, 21);
      if (filled) {
        const ch = this.entry[i];
        drawText(ctx, ch, px + Math.round((cellW - measure(ch)) / 2), cy + 8, { color: INK });
      }
    }

    if (this.messageTime > 0 && this.message) {
      const mw = measure(this.message);
      drawText(ctx, this.message, x + Math.round((boxW - mw) / 2), cy + 30, { color: '#d0674a' });
    } else {
      const hint = 'type digits   ESC to step back';
      drawText(ctx, hint, x + Math.round((boxW - measure(hint)) / 2), cy + 30, { color: INK_DIM });
    }
  }
}
