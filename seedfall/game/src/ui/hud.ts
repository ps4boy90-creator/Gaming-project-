import { Input, Action } from '../core/input';

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;

interface Line {
  speaker: string;
  text: string;
  ms: number;
}

/** DOM overlay: prompts, subtitles, location toasts, objectives, notices, fades, menus. */
export class Hud {
  private subQueue: Line[] = [];
  private subTimer = 0;
  private toastTimer = 0;
  private noticeTimer = 0;
  private lastPrompt = '';
  onReaderClose: (() => void) | null = null;

  setLoading(text: string, fraction: number): void {
    $('loading-text').textContent = text;
    $('loading-bar').style.width = `${Math.round(fraction * 100)}%`;
  }

  show(id: string, on: boolean): void {
    $(id).hidden = !on;
  }

  isOpen(id: string): boolean {
    return !$(id).hidden;
  }

  prompt(text: string | null, key = 'F'): void {
    const t = text ?? '';
    if (t === this.lastPrompt) return;
    this.lastPrompt = t;
    $('prompt').hidden = !text;
    $('crosshair').classList.toggle('active', !!text);
    if (text) {
      $('prompt-text').textContent = text;
      $('prompt-key').textContent = key;
    }
  }

  say(speaker: string, text: string, ms?: number): void {
    const dur = ms ?? Math.max(2600, 900 + text.length * 55);
    this.subQueue.push({ speaker, text, ms: dur });
    if (this.subTimer <= 0) this.nextSub();
  }

  clearSubs(): void {
    this.subQueue = [];
    this.subTimer = 0;
    $('subtitle').hidden = true;
  }

  private nextSub(): void {
    const l = this.subQueue.shift();
    if (!l) {
      $('subtitle').hidden = true;
      return;
    }
    $('sub-speaker').textContent = l.speaker;
    $('sub-text').textContent = l.text;
    $('subtitle').hidden = false;
    this.subTimer = l.ms;
  }

  toast(title: string, sub: string, color = '#e8a23a'): void {
    $('toast-title').textContent = title;
    $('toast-sub').textContent = sub;
    $('toast').style.borderLeftColor = color;
    $('toast').hidden = false;
    $('toast').style.opacity = '1';
    this.toastTimer = 3800;
  }

  objective(text: string | null): void {
    $('objective').hidden = !text;
    if (text) $('objective-text').textContent = text;
  }

  notice(text: string, ms = 4200): void {
    $('notice').textContent = text;
    $('notice').hidden = false;
    this.noticeTimer = ms;
  }

  fade(to: number, ms = 800): Promise<void> {
    const f = $('fade');
    f.style.transitionDuration = `${ms}ms`;
    f.style.opacity = String(to);
    return new Promise((r) => setTimeout(r, ms));
  }

  scope(on: boolean, status = '', progress = 0, title = 'SURFACE SURVEY'): void {
    $('scope').hidden = !on;
    $('crosshair').style.visibility = on ? 'hidden' : 'visible';
    if (on) {
      $('scope-title').textContent = title;
      $('scope-status').textContent = status;
      $('scope-bar').style.width = `${Math.round(progress * 100)}%`;
    }
  }

  openReader(title: string, body: HTMLElement | string, onClose?: () => void): HTMLElement {
    $('reader-title').textContent = title;
    const b = $('reader-body');
    b.innerHTML = '';
    if (typeof body === 'string') b.innerHTML = body;
    else b.appendChild(body);
    $('reader').hidden = false;
    this.onReaderClose = onClose ?? null;
    ($('reader-close') as HTMLButtonElement).focus({ preventScroll: true });
    return b;
  }

  closeReader(): void {
    if ($('reader').hidden) return;
    $('reader').hidden = true;
    const cb = this.onReaderClose;
    this.onReaderClose = null;
    cb?.();
  }

  update(dtMs: number): void {
    if (this.subTimer > 0) {
      this.subTimer -= dtMs;
      if (this.subTimer <= 0) this.nextSub();
    }
    if (this.toastTimer > 0) {
      this.toastTimer -= dtMs;
      if (this.toastTimer < 600) $('toast').style.opacity = String(Math.max(0, this.toastTimer / 600));
      if (this.toastTimer <= 0) $('toast').hidden = true;
    }
    if (this.noticeTimer > 0) {
      this.noticeTimer -= dtMs;
      if (this.noticeTimer <= 0) $('notice').hidden = true;
    }
  }
}

/** Virtual stick + drag-to-look + buttons for touchscreens. */
export class TouchControls {
  active = false;
  private stickId: number | null = null;
  private lookId: number | null = null;
  private stickOrigin = { x: 0, y: 0 };
  private lastLook = { x: 0, y: 0 };

  constructor(private input: Input) {
    const coarse = window.matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window;
    if (!coarse) return;
    this.active = true;
    const zone = $('stick-zone');
    const knob = $('stick-knob');
    const base = $('stick-base');
    zone.addEventListener('pointerdown', (e) => {
      this.stickId = e.pointerId;
      const r = base.getBoundingClientRect();
      this.stickOrigin = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
      zone.setPointerCapture(e.pointerId);
      this.moveStick(e, knob);
    });
    zone.addEventListener('pointermove', (e) => {
      if (e.pointerId === this.stickId) this.moveStick(e, knob);
    });
    const endStick = (e: PointerEvent) => {
      if (e.pointerId !== this.stickId) return;
      this.stickId = null;
      this.input.touchMove.x = this.input.touchMove.y = 0;
      knob.style.transform = '';
    };
    zone.addEventListener('pointerup', endStick);
    zone.addEventListener('pointercancel', endStick);

    const look = $('look-zone');
    look.addEventListener('pointerdown', (e) => {
      this.lookId = e.pointerId;
      this.lastLook = { x: e.clientX, y: e.clientY };
      look.setPointerCapture(e.pointerId);
    });
    look.addEventListener('pointermove', (e) => {
      if (e.pointerId !== this.lookId) return;
      this.input.addLook((e.clientX - this.lastLook.x) * 1.6, (e.clientY - this.lastLook.y) * 1.6);
      this.lastLook = { x: e.clientX, y: e.clientY };
    });
    const endLook = (e: PointerEvent) => {
      if (e.pointerId === this.lookId) this.lookId = null;
    };
    look.addEventListener('pointerup', endLook);
    look.addEventListener('pointercancel', endLook);

    document.querySelectorAll<HTMLButtonElement>('#touch-buttons .tbtn').forEach((b) => {
      const act = b.dataset.act as Action;
      const hold = b.dataset.hold === '1';
      b.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        if (hold) {
          if (this.input.touchHeld.has(act)) {
            this.input.touchHeld.delete(act);
            b.classList.remove('on');
          } else {
            this.input.touchHeld.add(act);
            b.classList.add('on');
          }
        } else this.input.touchPressed.add(act);
      });
    });
  }

  private moveStick(e: PointerEvent, knob: HTMLElement): void {
    const dx = e.clientX - this.stickOrigin.x;
    const dy = e.clientY - this.stickOrigin.y;
    const max = 50;
    const len = Math.hypot(dx, dy);
    const k = len > max ? max / len : 1;
    knob.style.transform = `translate(${dx * k}px, ${dy * k}px)`;
    this.input.touchMove.x = (dx * k) / max;
    this.input.touchMove.y = (-dy * k) / max;
  }

  show(on: boolean): void {
    if (this.active) $('touch').hidden = !on;
  }
}
