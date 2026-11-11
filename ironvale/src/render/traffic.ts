import * as THREE from 'three';
import { MAP_H, MAP_W } from '../data/defs';
import { RNG, smooth } from '../core/util';
import type { Gfx } from './gfx';
import { buildScenery } from './models';
import { ENTRY_X, ROAD_Z } from './terrain';

const TINTS = [0xd94f3d, 0x3d7fd9, 0xe8e8e8, 0x2f3540, 0xe0b23a, 0x5aa86a, 0x9aa3ad, 0x8a5fb5];

/** Ambient road traffic, parked staff cars and the prison bus. */
export class Traffic {
  private group = new THREE.Group();
  private cars: THREE.InstancedMesh;
  private carGlow: THREE.InstancedMesh | null = null;
  private state: { x: number; v: number; lane: number }[] = [];
  private bus: THREE.Group;
  private busPlan: { start: number; arrive: number; leave: number } | null = null;
  private m = new THREE.Matrix4();
  private q = new THREE.Quaternion();
  private p = new THREE.Vector3();
  private s = new THREE.Vector3(1, 1, 1);
  private static PARKED = 5;

  constructor(gfx: Gfx, solidMat: THREE.Material, glowMat: THREE.Material) {
    gfx.scene.add(this.group);
    const r = new RNG(99);
    const car = buildScenery('car');
    const moving = 7;
    const n = moving + Traffic.PARKED;
    this.cars = new THREE.InstancedMesh(car.solid, solidMat, n);
    this.cars.castShadow = true;
    this.cars.receiveShadow = true;
    this.cars.frustumCulled = false;
    if (car.glow) {
      this.carGlow = new THREE.InstancedMesh(car.glow, glowMat, n);
      this.carGlow.frustumCulled = false;
      this.carGlow.userData.noAO = true;
      this.group.add(this.carGlow);
    }
    const c = new THREE.Color();
    for (let i = 0; i < n; i++) {
      this.cars.setColorAt(i, c.setHex(r.pick(TINTS), THREE.SRGBColorSpace));
      if (i < moving) this.state.push({ x: r.range(-140, MAP_W + 140), v: r.range(5.5, 8.5), lane: i % 2 });
    }
    // parked cars on the apron
    const up = new THREE.Vector3(0, 1, 0);
    for (let i = 0; i < Traffic.PARKED; i++) {
      const side = i % 2 ? 1 : -1, slot = Math.floor(i / 2);
      this.q.setFromAxisAngle(up, Math.PI / 2);
      this.p.set(ENTRY_X + 0.5 + side * (2.78 + slot * 1.15), 0, MAP_H + 1.5);
      this.m.compose(this.p, this.q, this.s.set(0.82, 0.82, 0.82));
      this.cars.setMatrixAt(moving + i, this.m);
      this.carGlow?.setMatrixAt(moving + i, this.m.clone().scale(new THREE.Vector3(0, 0, 0)));
    }
    this.s.set(1, 1, 1);
    this.group.add(this.cars);

    const bus = buildScenery('bus');
    this.bus = new THREE.Group();
    const bm = new THREE.Mesh(bus.solid, solidMat);
    bm.castShadow = true;
    bm.receiveShadow = true;
    this.bus.add(bm);
    if (bus.glow) {
      const g = new THREE.Mesh(bus.glow, glowMat);
      g.userData.noAO = true;
      this.bus.add(g);
    }
    this.bus.visible = false;
    this.bus.position.z = ROAD_Z - 1.15;
    this.group.add(this.bus);
  }

  /** the sim announced a bus arriving in `eta` sim minutes with `count` inmates */
  callBus(now: number, eta: number, count: number) {
    this.busPlan = { start: now, arrive: now + eta, leave: now + eta + count * 0.6 + 4 };
  }

  update(dt: number, simTime: number, paused: boolean) {
    const up = THREE.Object3D.DEFAULT_UP;
    if (!paused) {
      for (let i = 0; i < this.state.length; i++) {
        const st = this.state[i];
        const dir = st.lane === 0 ? 1 : -1;
        // queue behind the prison bus in the near lane
        const gap = this.bus.visible && st.lane === 0 ? this.bus.position.x - st.x : 99;
        if (!(gap > 0 && gap < 6.5)) st.x += st.v * dir * dt;
        if (st.x > MAP_W + 150) st.x = -150;
        if (st.x < -150) st.x = MAP_W + 150;
        this.q.setFromAxisAngle(up, dir > 0 ? 0 : Math.PI);
        this.p.set(st.x, 0, ROAD_Z + (st.lane === 0 ? -1.15 : 1.15));
        this.m.compose(this.p, this.q, this.s);
        this.cars.setMatrixAt(i, this.m);
        this.carGlow?.setMatrixAt(i, this.m);
      }
      this.cars.instanceMatrix.needsUpdate = true;
      if (this.carGlow) this.carGlow.instanceMatrix.needsUpdate = true;
    }
    const b = this.busPlan;
    if (b) {
      const stopX = ENTRY_X + 0.5;
      this.bus.visible = true;
      if (simTime < b.arrive) {
        const t = smooth(Math.max(0, (simTime - b.start) / (b.arrive - b.start)));
        this.bus.position.x = -90 + (stopX + 90) * (1 - (1 - t) * (1 - t));
      } else if (simTime < b.leave) this.bus.position.x = stopX;
      else {
        const t = (simTime - b.leave) / 7;
        this.bus.position.x = stopX + t * t * (MAP_W + 150 - stopX);
        if (t >= 1) {
          this.bus.visible = false;
          this.busPlan = null;
        }
      }
    }
  }
}
