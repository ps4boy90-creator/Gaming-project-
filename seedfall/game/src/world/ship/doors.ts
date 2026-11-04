import * as THREE from 'three';
import { Materials } from './materials';
import { Box, CollisionWorld } from '../collision';
import { bus } from '../../core/events';

export interface DoorOpts {
  axis: 'x' | 'z'; // the wall runs along this axis; leaves slide along it
  x: number;
  y: number; // floor height
  z: number;
  width: number;
  height: number;
  locked?: boolean;
  label?: string;
  heavy?: boolean;
}

/** Twin-leaf sliding pressure door. Opens automatically for anyone nearby unless locked. */
export class Door {
  group = new THREE.Group();
  leaves: THREE.Mesh[] = [];
  lights: THREE.Mesh[] = [];
  open = 0;
  target = 0;
  locked: boolean;
  label: string;
  /** Forced state (lift doors, lockdowns). null = automatic. */
  override: number | null = null;
  collider: Box;
  private lastTarget = 0;
  private lightState = '';

  constructor(parent: THREE.Object3D, private mats: Materials, world: CollisionWorld, public o: DoorOpts) {
    this.locked = !!o.locked;
    this.label = o.label ?? '';
    const t = o.heavy ? 0.12 : 0.07;
    const lw = o.width / 2 + 0.03;
    for (const side of [-1, 1]) {
      const g = new THREE.BoxGeometry(lw, o.height, t);
      const m = new THREE.Mesh(g, mats.get('door').mat);
      m.castShadow = true;
      m.receiveShadow = true;
      if (side > 0) m.scale.x = -1;
      this.leaves.push(m);
      this.group.add(m);
    }
    if (o.axis === 'z') this.group.rotation.y = Math.PI / 2;
    this.group.position.set(o.x, o.y, o.z);
    for (const side of [-1, 1]) {
      const l = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.05, 0.03), mats.get('statusGreen').mat);
      l.position.set(0, o.height + 0.12, side * 0.13);
      this.lights.push(l);
      this.group.add(l);
    }
    parent.add(this.group);
    const hw = o.width / 2;
    const ht = 0.1;
    this.collider =
      o.axis === 'x'
        ? world.add(o.x - hw, o.y, o.z - ht, o.x + hw, o.y + o.height, o.z + ht, 'wall')
        : world.add(o.x - ht, o.y, o.z - hw, o.x + ht, o.y + o.height, o.z + hw, 'wall');
    this.layout();
    this.setLight();
  }

  private layout(): void {
    const lw = this.o.width / 2 + 0.03;
    const slide = this.open * (this.o.width / 2 + 0.02);
    this.leaves[0].position.set(-lw / 2 + 0.015 - slide, this.o.height / 2, 0);
    this.leaves[1].position.set(lw / 2 - 0.015 + slide, this.o.height / 2, 0);
  }

  private setLight(): void {
    const state = this.locked ? 'statusRed' : this.open > 0.02 && this.open < 0.98 ? 'statusAmber' : 'statusGreen';
    if (state === this.lightState) return;
    this.lightState = state;
    for (const l of this.lights) l.material = this.mats.get(state).mat;
  }

  /** Distance from a point to the door centre (ignores height). */
  distanceTo(x: number, y: number, z: number): number {
    if (Math.abs(y - this.o.y) > 2.2) return Infinity;
    return Math.hypot(x - this.o.x, z - this.o.z);
  }

  update(dt: number, px: number, py: number, pz: number): void {
    if (this.override !== null) this.target = this.override;
    else this.target = !this.locked && this.distanceTo(px, py, pz) < 2.3 ? 1 : 0;
    if (this.target !== this.lastTarget) {
      this.lastTarget = this.target;
      bus.emit('sfx', { kind: this.target ? 'door-open' : 'door-close', x: this.o.x, y: this.o.y + 1.2, z: this.o.z, heavy: !!this.o.heavy });
    }
    const speed = this.o.heavy ? 1.3 : 2.4;
    const prev = this.open;
    this.open += Math.sign(this.target - this.open) * Math.min(Math.abs(this.target - this.open), dt * speed);
    if (prev !== this.open) this.layout();
    this.collider.solid = this.open < 0.75;
    this.setLight();
  }

  isClosed(): boolean {
    return this.open <= 0.001;
  }

  isOpen(): boolean {
    return this.open >= 0.999;
  }
}
