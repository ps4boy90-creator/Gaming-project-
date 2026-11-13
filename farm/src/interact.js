/**
 * Things you can do something to: doors, lamps, the television, and a few
 * objects that only answer back.
 *
 * The rule is the one first-person games settled on long ago: whatever is
 * nearest the middle of the screen and within arm's reach is the thing, and a
 * line of text says what will happen if you use it. There is no cursor and
 * nothing to click on precisely -- look, and act.
 *
 * Doors are the only things that move. Each is a piece of geometry kept apart
 * from the rest of the scene so it can be drawn with its own transform, plus
 * a collider that is moved with it, so a shut door stops you and an open one
 * does not.
 */
import { rotY, translate, mul, siteToWorld, xformPoint } from './math.js';

const ease = (t) => t * t * (3 - 2 * t);

class Door {
  constructor(d) {
    Object.assign(this, d);
    this.t = d.start || 0;        // 0 shut, 1 open
    this.goal = this.t;
    this.apply();
  }
  get isOpen() { return (this.goal === this.t ? this.t : this.goal) > 0.4; }
  toggle() { this.goal = this.isOpen ? 0 : 1; }

  /** Returns true on the frame it comes to rest shut. */
  update(dt) {
    if (this.t === this.goal) return false;
    const step = dt / (this.kind === 'slide' ? 1.1 : 0.75);
    this.t = this.goal > this.t ? Math.min(this.goal, this.t + step) : Math.max(this.goal, this.t - step);
    this.apply();
    return this.t === 0;
  }

  apply() {
    const e = ease(this.t), b = this.box;
    if (this.kind === 'slide') {
      const x = this.shutX + (this.openX - this.shutX) * e;
      this.part.matrix = mul(this.part.base, translate(x, this.y, this.z));
      [b.x, b.z] = siteToWorld(this.site, x + this.width / 2, this.z);
      Object.assign(b, { hx: this.width / 2, hz: 0.09, yaw: this.site.yaw });
      this.handle = xformPoint(this.part.matrix, [this.width * 0.5, 1.5, 0.1]);
    } else {
      // The leaf runs along +X from its hinge; a positive turn swings it toward -Z.
      const a = this.shut + (this.open - this.shut) * e;
      this.part.matrix = mul(this.part.base, rotY(a));
      [b.x, b.z] = siteToWorld(this.site, this.hinge[0] + Math.cos(a) * this.width / 2, this.hinge[1] - Math.sin(a) * this.width / 2);
      Object.assign(b, { hx: this.width / 2, hz: 0.04, yaw: this.site.yaw + a });
      this.handle = xformPoint(this.part.matrix, [this.width * 0.55, 1.05, 0]);
    }
  }
}

export class Interactions {
  /** `say` shows a line of text; `audio` makes the noises. */
  constructor(world, audio, say) {
    this.audio = audio;
    this.groups = world.groups;
    this.doors = world.doors.map((d) => new Door(d));
    this.things = [];
    for (const d of this.doors) {
      this.things.push({
        door: d, reach: d.reach || 2.3,
        get pos() { return d.handle; },
        label: () => (d.isOpen ? 'Close' : 'Open') + ' ' + d.noun,
        use: () => { d.toggle(); audio.door(d.kind, d.isOpen); },
      });
    }
    for (const name of Object.keys(this.groups)) if (!this.groups[name].on) this.setGroup(name, false);
    for (const t of world.things) {
      if (t.group) {
        const g = this.groups[t.group];
        this.things.push({ ...t, label: () => `Switch ${g.on ? 'off' : 'on'} ${t.noun}`, use: () => { this.setGroup(t.group, !g.on); audio.click(); } });
      } else if (t.locked) {
        this.things.push({ ...t, label: () => `Open ${t.noun}`, use: () => { say(t.say || 'Locked.'); audio.rattle(); } });
      } else {
        this.things.push({ ...t, label: () => t.label, use: () => { say(t.say); audio.click(); } });
      }
    }
  }

  /** A switch works a whole group at once: the lamp, its glow, the light it throws outside. */
  setGroup(name, on) {
    const g = this.groups[name];
    g.on = on;
    for (const l of g.lights) l.on = on;
    for (const p of g.parts) { p.emit = on ? 1 : 0; if (p.offTint) p.tint = on ? [1, 1, 1] : p.offTint; }
  }

  update(dt) {
    for (const d of this.doors) if (d.update(dt)) this.audio.latch();
  }

  /** The thing being looked at, or null: nearest the view's centre, within reach. */
  target(eye, fwd) {
    let best = null, score = -1;
    for (const t of this.things) {
      const p = t.pos, dx = p[0] - eye[0], dy = p[1] - eye[1], dz = p[2] - eye[2];
      const dist = Math.hypot(dx, dy, dz);
      if (dist > t.reach || dist < 1e-3) continue;
      const cos = (dx * fwd[0] + dy * fwd[1] + dz * fwd[2]) / dist;
      // A wide cone up close, where a door fills the view; a narrow one at arm's length.
      if (cos < (dist < 1.0 ? 0.55 : 0.83)) continue;
      const s = cos - dist * 0.04;
      if (s > score) { score = s; best = t; }
    }
    return best;
  }
}
