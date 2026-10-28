// First-person controller: mouse/keyboard with pointer lock (drag-to-look
// fallback), twin-stick touch controls, and circle-vs-box collision.
import { clamp, damp } from './util.js';

export class Player {
  constructor(camera, dom, colliders, hud) {
    this.camera = camera;
    this.dom = dom;
    this.colliders = colliders;
    this.hud = hud;
    this.x = 0; this.z = 0;
    this.vx = 0; this.vz = 0;
    this.yaw = 0; this.pitch = 0;
    this.eye = 1.65;
    this.crouch = false;
    this.radius = 0.27;
    this.sens = 0.0022;
    this.keys = new Set();
    this.stick = { x: 0, y: 0 };
    this.bob = 0;
    this.enabled = false;
    this.locked = false;
    this.reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.handlers = {};
    camera.rotation.order = 'YXZ';
  }

  on(name, fn) { this.handlers[name] = fn; }
  emit(name, ...a) { this.handlers[name]?.(...a); }

  attach() {
    const keyMap = { KeyE: 'interact', KeyR: 'breach', KeyF: 'torch', KeyL: 'lights', KeyM: 'mute', KeyH: 'help' };
    addEventListener('keydown', (e) => {
      if (!this.enabled) return;
      if (e.code === 'KeyC') { this.crouch = !this.crouch; return; }
      if (keyMap[e.code] && !e.repeat) { this.emit(keyMap[e.code]); return; }
      this.keys.add(e.code);
      if (e.code.startsWith('Arrow') || e.code === 'Space') e.preventDefault();
    });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());

    // mouse look: pointer lock when available, otherwise drag
    let dragging = false;
    this.dom.addEventListener('mousedown', (e) => {
      if (!this.enabled) return;
      if (!this.locked) {
        dragging = true;
        try {
          const p = this.dom.requestPointerLock?.();
          if (p && p.catch) p.catch(() => {});
        } catch { /* pointer lock unavailable: keep drag-to-look */ }
      } else if (e.button === 0) this.emit('interact');
    });
    addEventListener('mouseup', () => { dragging = false; });
    document.addEventListener('pointerlockerror', () => this.emit('lockerror'));
    document.addEventListener('pointerlockchange', () => {
      this.locked = document.pointerLockElement === this.dom;
      this.emit('lock', this.locked);
    });
    addEventListener('mousemove', (e) => {
      if (!this.enabled || !(this.locked || dragging)) return;
      this.look(e.movementX, e.movementY);
    });

    // touch: left thumb = move stick, right thumb = look, tap = interact
    let stickId = null, lookId = null, sx = 0, sy = 0, lx = 0, ly = 0, lookStart = 0, lookTravel = 0;
    const R = 56;
    const opts = { passive: false };
    this.dom.addEventListener('touchstart', (e) => {
      if (!this.enabled) return;
      e.preventDefault();
      for (const t of e.changedTouches) {
        if (t.clientX < innerWidth * 0.45 && stickId === null) {
          stickId = t.identifier; sx = t.clientX; sy = t.clientY;
          this.hud.stick(true, sx, sy, 0, 0);
        } else if (lookId === null) {
          lookId = t.identifier; lx = t.clientX; ly = t.clientY;
          lookStart = performance.now(); lookTravel = 0;
        }
      }
    }, opts);
    this.dom.addEventListener('touchmove', (e) => {
      if (!this.enabled) return;
      e.preventDefault();
      for (const t of e.changedTouches) {
        if (t.identifier === stickId) {
          let dx = t.clientX - sx, dy = t.clientY - sy;
          const d = Math.hypot(dx, dy);
          if (d > R) { dx *= R / d; dy *= R / d; }
          this.stick.x = dx / R; this.stick.y = -dy / R;
          this.hud.stick(true, sx, sy, dx, dy);
        } else if (t.identifier === lookId) {
          const dx = t.clientX - lx, dy = t.clientY - ly;
          lookTravel += Math.abs(dx) + Math.abs(dy);
          this.look(dx * 1.6, dy * 1.6);
          lx = t.clientX; ly = t.clientY;
        }
      }
    }, opts);
    const end = (e) => {
      for (const t of e.changedTouches) {
        if (t.identifier === stickId) {
          stickId = null; this.stick.x = this.stick.y = 0;
          this.hud.stick(false);
        } else if (t.identifier === lookId) {
          if (lookTravel < 12 && performance.now() - lookStart < 300) this.emit('interact');
          lookId = null;
        }
      }
    };
    this.dom.addEventListener('touchend', end);
    this.dom.addEventListener('touchcancel', end);
  }

  look(dx, dy) {
    this.yaw -= dx * this.sens;
    this.pitch = clamp(this.pitch - dy * this.sens, -1.45, 1.45);
  }

  place(x, z, yaw = 0, pitch = 0) {
    this.x = x; this.z = z; this.yaw = yaw; this.pitch = pitch;
    this.vx = this.vz = 0;
    this.sync(0);
  }

  update(dt) {
    const k = this.keys;
    let f = 0, s = 0;
    if (this.enabled) {
      f = (k.has('KeyW') || k.has('ArrowUp') ? 1 : 0) - (k.has('KeyS') || k.has('ArrowDown') ? 1 : 0) + this.stick.y;
      s = (k.has('KeyD') || k.has('ArrowRight') ? 1 : 0) - (k.has('KeyA') || k.has('ArrowLeft') ? 1 : 0) + this.stick.x;
    }
    const mag = Math.hypot(f, s);
    if (mag > 1) { f /= mag; s /= mag; }
    const run = k.has('ShiftLeft') || k.has('ShiftRight') || Math.hypot(this.stick.x, this.stick.y) > 0.95;
    const speed = (run ? 3.0 : 1.45) * (this.crouch ? 0.5 : 1);
    const sn = Math.sin(this.yaw), cs = Math.cos(this.yaw);
    const tx = (-sn * f + cs * s) * speed, tz = (-cs * f - sn * s) * speed;
    this.vx = damp(this.vx, tx, 9, dt);
    this.vz = damp(this.vz, tz, 9, dt);
    this.x += this.vx * dt;
    this.z += this.vz * dt;
    this.collide();
    const sp = Math.hypot(this.vx, this.vz);
    this.bob += dt * sp * 4.6;
    this.eye = damp(this.eye, this.fixedEye ?? (this.crouch ? 1.05 : 1.65), 8, dt);
    this.sync(sp);
  }

  sync(sp) {
    const amp = this.reducedMotion ? 0 : Math.min(1, sp / 1.45);
    this.camera.position.set(this.x, this.eye + Math.abs(Math.sin(this.bob)) * 0.022 * amp - 0.011 * amp, this.z);
    this.camera.rotation.set(this.pitch, this.yaw, Math.sin(this.bob) * 0.0025 * amp);
  }

  collide() {
    const r = this.radius;
    for (let it = 0; it < 3; it++) {
      for (const b of this.colliders) {
        if (b.active === false) continue;
        const cx = clamp(this.x, b.minX, b.maxX), cz = clamp(this.z, b.minZ, b.maxZ);
        const dx = this.x - cx, dz = this.z - cz;
        const d2 = dx * dx + dz * dz;
        if (d2 >= r * r) continue;
        if (d2 > 1e-10) {
          const d = Math.sqrt(d2);
          this.x = cx + (dx / d) * r;
          this.z = cz + (dz / d) * r;
        } else {
          const l = this.x - b.minX, rr = b.maxX - this.x, t = this.z - b.minZ, bt = b.maxZ - this.z;
          const m = Math.min(l, rr, t, bt);
          if (m === l) this.x = b.minX - r;
          else if (m === rr) this.x = b.maxX + r;
          else if (m === t) this.z = b.minZ - r;
          else this.z = b.maxZ + r;
        }
      }
    }
  }
}
