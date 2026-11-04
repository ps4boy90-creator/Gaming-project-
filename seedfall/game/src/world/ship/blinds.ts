import * as THREE from 'three';
import { Materials } from './materials';

export interface BlindSpec {
  axis: 'x' | 'z'; // wall runs along this axis
  c: number; // inner face coordinate of the wall
  dir: 1 | -1; // into the room along the wall normal
  at: number;
  w: number;
  y: number; // deck floor
  y0: number;
  y1: number;
}

/** Window "blinders": louvred slats that rotate open to let the sunlight in. */
export class Blinds {
  group = new THREE.Group();
  open = 0;
  target = 0;
  private slats: { mesh: THREE.Mesh; axis: 'x' | 'z'; dir: number }[] = [];

  constructor(parent: THREE.Object3D, mats: Materials, specs: BlindSpec[]) {
    const mat = mats.get('ribDark').mat;
    for (const s of specs) {
      const n = Math.max(4, Math.round((s.y1 - s.y0) / 0.16));
      const sh = (s.y1 - s.y0) / n;
      for (let i = 0; i < n; i++) {
        const g = s.axis === 'z' ? new THREE.BoxGeometry(s.w, sh * 1.06, 0.02) : new THREE.BoxGeometry(0.02, sh * 1.06, s.w);
        const m = new THREE.Mesh(g, mat);
        const yy = s.y + s.y0 + (i + 0.5) * sh;
        if (s.axis === 'z') m.position.set(s.at, yy, s.c + s.dir * 0.09);
        else m.position.set(s.c + s.dir * 0.09, yy, s.at);
        m.castShadow = true;
        m.receiveShadow = true;
        this.group.add(m);
        this.slats.push({ mesh: m, axis: s.axis, dir: s.dir });
      }
    }
    parent.add(this.group);
  }

  update(dt: number): boolean {
    if (this.open === this.target) return false;
    this.open += Math.sign(this.target - this.open) * Math.min(Math.abs(this.target - this.open), dt * 0.35);
    const a = this.open * (Math.PI / 2 - 0.12);
    for (const s of this.slats) {
      if (s.axis === 'z') s.mesh.rotation.x = a * s.dir;
      else s.mesh.rotation.z = -a * s.dir;
    }
    return true;
  }
}
