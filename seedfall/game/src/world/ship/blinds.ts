import * as THREE from 'three';
import { Materials } from './materials';

/** One window's blinders. (x, z) is the window centre on the inner face; `yaw` turns a box whose
 *  local x runs along the window and whose local z points into the room. */
export interface BlindSpec {
  x: number;
  z: number;
  yaw: number;
  w: number;
  y: number; // deck floor
  y0: number;
  y1: number;
}

/** Convert an axis-aligned wall window into a blind spec. */
export function wallBlind(axis: 'x' | 'z', c: number, dir: 1 | -1, at: number, w: number, y: number, y0: number, y1: number): BlindSpec {
  if (axis === 'z') return { x: at, z: c, yaw: dir > 0 ? 0 : Math.PI, w, y, y0, y1 };
  return { x: c, z: at, yaw: dir > 0 ? Math.PI / 2 : -Math.PI / 2, w, y, y0, y1 };
}

/** Window "blinders": louvred slats that swing open to let the sunlight in. */
export class Blinds {
  group = new THREE.Group();
  open = 0;
  target = 0;
  private slats: THREE.Mesh[] = [];

  constructor(parent: THREE.Object3D, mats: Materials, specs: BlindSpec[]) {
    const mat = mats.get('ribDark').mat;
    for (const s of specs) {
      const win = new THREE.Group();
      win.rotation.y = s.yaw;
      win.position.set(s.x, 0, s.z);
      win.translateZ(0.1);
      const n = Math.max(4, Math.round((s.y1 - s.y0) / 0.15));
      const sh = (s.y1 - s.y0) / n;
      const g = new THREE.BoxGeometry(s.w, sh * 1.06, 0.018);
      for (let i = 0; i < n; i++) {
        const m = new THREE.Mesh(g, mat);
        m.position.set(0, s.y + s.y0 + (i + 0.5) * sh, 0);
        m.castShadow = true;
        m.receiveShadow = true;
        win.add(m);
        this.slats.push(m);
      }
      this.group.add(win);
    }
    parent.add(this.group);
  }

  update(dt: number): boolean {
    if (this.open === this.target) return false;
    this.open += Math.sign(this.target - this.open) * Math.min(Math.abs(this.target - this.open), dt * 0.35);
    const a = this.open * (Math.PI / 2 - 0.12);
    for (const s of this.slats) s.rotation.x = a;
    return true;
  }
}
