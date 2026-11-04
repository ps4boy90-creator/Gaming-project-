import { bus } from './events';

export type Action =
  | 'forward' | 'back' | 'left' | 'right'
  | 'sprint' | 'crouch' | 'jump' | 'leanL' | 'leanR'
  | 'use' | 'light' | 'pause';

const BINDINGS: Record<Action, string[]> = {
  forward: ['KeyW', 'ArrowUp'],
  back: ['KeyS', 'ArrowDown'],
  left: ['KeyA', 'ArrowLeft'],
  right: ['KeyD', 'ArrowRight'],
  sprint: ['ShiftLeft', 'ShiftRight'],
  crouch: ['KeyC'],
  jump: ['Space'],
  leanL: ['KeyQ'],
  leanR: ['KeyE'],
  use: ['KeyF'],
  light: ['KeyL'],
  pause: ['Escape', 'KeyP'],
};

/** Keyboard + mouse (pointer lock, or drag-to-look fallback) + touch inputs. */
export class Input {
  private down = new Set<string>();
  private pressedCodes = new Set<string>();
  private lookDX = 0;
  private lookDY = 0;
  private dragging = false;
  touchMove = { x: 0, y: 0 };
  touchHeld = new Set<Action>();
  touchPressed = new Set<Action>();
  pointerLocked = false;
  dragLook = false;
  enabled = true;

  constructor(private el: HTMLElement) {
    window.addEventListener('keydown', (e) => {
      if (e.code === 'Tab') e.preventDefault();
      if (!e.repeat) this.pressedCodes.add(e.code);
      this.down.add(e.code);
      if (['Space', 'ArrowUp', 'ArrowDown'].includes(e.code) && this.enabled) e.preventDefault();
    });
    window.addEventListener('keyup', (e) => this.down.delete(e.code));
    window.addEventListener('blur', () => {
      this.down.clear();
      this.dragging = false;
    });
    window.addEventListener('mousemove', (e) => {
      if (this.pointerLocked || (this.dragLook && this.dragging)) {
        this.lookDX += e.movementX;
        this.lookDY += e.movementY;
      }
    });
    el.addEventListener('mousedown', (e) => {
      if (e.button === 0 && this.dragLook) this.dragging = true;
    });
    window.addEventListener('mouseup', () => (this.dragging = false));
    document.addEventListener('pointerlockchange', () => {
      this.pointerLocked = document.pointerLockElement === this.el;
      bus.emit('pointerlock', this.pointerLocked);
    });
    document.addEventListener('pointerlockerror', () => bus.emit('pointerlock-failed'));
  }

  held(a: Action): boolean {
    if (this.touchHeld.has(a)) return true;
    return BINDINGS[a].some((c) => this.down.has(c));
  }

  pressed(a: Action): boolean {
    if (this.touchPressed.has(a)) return true;
    return BINDINGS[a].some((c) => this.pressedCodes.has(c));
  }

  /** Movement axis: x = strafe right, y = forward. */
  axis(): { x: number; y: number } {
    let x = this.touchMove.x;
    let y = this.touchMove.y;
    if (this.held('forward')) y += 1;
    if (this.held('back')) y -= 1;
    if (this.held('right')) x += 1;
    if (this.held('left')) x -= 1;
    const len = Math.hypot(x, y);
    if (len > 1) {
      x /= len;
      y /= len;
    }
    return { x, y };
  }

  addLook(dx: number, dy: number): void {
    this.lookDX += dx;
    this.lookDY += dy;
  }

  takeLook(): { dx: number; dy: number } {
    const r = { dx: this.lookDX, dy: this.lookDY };
    this.lookDX = 0;
    this.lookDY = 0;
    return r;
  }

  endFrame(): void {
    this.pressedCodes.clear();
    this.touchPressed.clear();
  }

  clear(): void {
    this.down.clear();
    this.pressedCodes.clear();
    this.touchHeld.clear();
    this.touchPressed.clear();
    this.touchMove.x = this.touchMove.y = 0;
    this.lookDX = this.lookDY = 0;
  }

  /** Ask for pointer lock. If it fails after a real click, fall back to drag-to-look for good. */
  async requestPointerLock(fromGesture: boolean): Promise<boolean> {
    if (this.dragLook) return false;
    let ok = true;
    try {
      const anyEl = this.el as HTMLElement & { requestPointerLock: () => Promise<void> | void };
      const r = anyEl.requestPointerLock();
      if (r && typeof (r as Promise<void>).then === 'function') await r;
      else {
        await new Promise((res) => setTimeout(res, 250));
        ok = document.pointerLockElement === this.el;
      }
    } catch {
      ok = false;
    }
    if (!ok && fromGesture) {
      this.dragLook = true;
      bus.emit('drag-look');
    }
    return ok;
  }

  exitPointerLock(): void {
    if (document.pointerLockElement) document.exitPointerLock();
  }
}
