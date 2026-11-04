import * as THREE from 'three';

export interface LightAnchor {
  x: number;
  y: number;
  z: number;
  color: THREE.Color;
  intensity: number;
  distance: number;
}

interface Slot {
  light: THREE.PointLight;
  anchor: LightAnchor | null;
  fade: number;
}

/** A fixed pool of point lights reassigned to the nearest fixtures. The light count never
 *  changes, so shaders never recompile while the player walks the ship. */
export class LightPool {
  anchors: LightAnchor[] = [];
  private slots: Slot[] = [];
  private timer = 0;
  private wanted = new Set<LightAnchor>();

  constructor(parent: THREE.Object3D, count = 10) {
    for (let i = 0; i < count; i++) {
      const light = new THREE.PointLight(0xffffff, 0, 10, 2);
      light.position.set(0, -1000, 0);
      parent.add(light);
      this.slots.push({ light, anchor: null, fade: 0 });
    }
  }

  add(a: LightAnchor): void {
    this.anchors.push(a);
  }

  update(dt: number, cam: THREE.Vector3, shiftScale: number, shiftTint: THREE.Color): void {
    this.timer -= dt;
    if (this.timer <= 0) {
      this.timer = 0.2;
      const scored = this.anchors
        .map((a) => ({ a, d: Math.hypot(a.x - cam.x, (a.y - cam.y) * 3.5, a.z - cam.z) }))
        .filter((s) => s.d < s.a.distance * 1.6 + 6)
        .sort((p, q) => p.d - q.d)
        .slice(0, this.slots.length);
      this.wanted = new Set(scored.map((s) => s.a));
    }
    const assigned = new Set(this.slots.map((s) => s.anchor));
    const pending = [...this.wanted].filter((a) => !assigned.has(a));
    for (const s of this.slots) {
      const keep = s.anchor && this.wanted.has(s.anchor);
      if (keep) s.fade = Math.min(1, s.fade + dt * 3);
      else {
        s.fade = Math.max(0, s.fade - dt * 4);
        if (s.fade === 0) {
          s.anchor = pending.shift() ?? null;
          if (s.anchor) {
            s.light.position.set(s.anchor.x, s.anchor.y, s.anchor.z);
            s.light.distance = s.anchor.distance;
          } else s.light.position.set(0, -1000, 0);
        }
      }
      if (s.anchor) {
        s.light.color.copy(s.anchor.color).multiply(shiftTint);
        s.light.intensity = s.anchor.intensity * s.fade * shiftScale;
      } else s.light.intensity = 0;
    }
  }
}
