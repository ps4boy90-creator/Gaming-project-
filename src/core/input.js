/**
 * Keyboard input mapped through named actions rather than raw key codes, so
 * rebinding is a change to one table and every call site keeps working.
 */
export const DEFAULT_BINDINGS = {
  left: ['ArrowLeft', 'KeyA'],
  right: ['ArrowRight', 'KeyD'],
  up: ['ArrowUp', 'KeyW'],
  down: ['ArrowDown', 'KeyS'],
  run: ['ShiftLeft', 'ShiftRight'],
  crouch: ['ControlLeft', 'KeyC'],
  jump: ['Space'],
  interact: ['KeyE', 'Enter'],
  journal: ['Tab'],
  options: ['KeyO'],
  cancel: ['Escape'],
  advance: ['KeyE', 'Enter', 'Space'],
  backspace: ['Backspace'],
  // Digits are bound so the keypad can read them and so the browser does not
  // treat them as page shortcuts while the overlay is up.
  digits: ['Digit0', 'Digit1', 'Digit2', 'Digit3', 'Digit4',
    'Digit5', 'Digit6', 'Digit7', 'Digit8', 'Digit9'],
};

export class Input {
  constructor(target = window, bindings = DEFAULT_BINDINGS) {
    this.bindings = bindings;
    this.down = new Set();
    this.pressed = new Set();
    this.released = new Set();
    this.anyPressedThisTick = false;

    this._onDown = (e) => {
      // Tab and Space scroll or move focus by default, which fights the game.
      if (this._isBound(e.code)) e.preventDefault();
      if (e.repeat) return;
      this.down.add(e.code);
      this.pressed.add(e.code);
    };
    this._onUp = (e) => {
      if (this._isBound(e.code)) e.preventDefault();
      this.down.delete(e.code);
      this.released.add(e.code);
    };
    // Keys held while the window loses focus would otherwise stay stuck down.
    this._onBlur = () => this.down.clear();

    this.target = target;
    target.addEventListener('keydown', this._onDown);
    target.addEventListener('keyup', this._onUp);
    window.addEventListener('blur', this._onBlur);
  }

  _isBound(code) {
    for (const codes of Object.values(this.bindings)) {
      if (codes.includes(code)) return true;
    }
    return false;
  }

  held(action) {
    const codes = this.bindings[action];
    return !!codes && codes.some((c) => this.down.has(c));
  }

  justPressed(action) {
    const codes = this.bindings[action];
    return !!codes && codes.some((c) => this.pressed.has(c));
  }

  justReleased(action) {
    const codes = this.bindings[action];
    return !!codes && codes.some((c) => this.released.has(c));
  }

  /** -1, 0 or 1 for a two-key axis. */
  axis(negative, positive) {
    return (this.held(positive) ? 1 : 0) - (this.held(negative) ? 1 : 0);
  }

  /** Call once at the end of every fixed update, after all reads. */
  endFrame() {
    this.anyPressedThisTick = this.pressed.size > 0;
    this.pressed.clear();
    this.released.clear();
  }

  destroy() {
    this.target.removeEventListener('keydown', this._onDown);
    this.target.removeEventListener('keyup', this._onUp);
    window.removeEventListener('blur', this._onBlur);
  }
}
