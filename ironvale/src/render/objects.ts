import * as THREE from 'three';
import { OBJ, OBJECTS } from '../data/defs';
import { footprint, rotYaw, type World } from '../world/world';
import type { Gfx } from './gfx';
import { Batch } from './batch';
import { buildObjectModel } from './models';
import type { ModelResult } from './modelkit';

export interface LightSpot {
  x: number;
  z: number;
  r: number;
}

/** Draws every placed object with one instanced draw call per type. */
export class ObjectRenderer {
  private group = new THREE.Group();
  private models = new Map<string, ModelResult>();
  private solid = new Map<string, Batch>();
  private glow = new Map<string, Batch>();
  private plan = new Map<string, Batch>();
  solidMat: THREE.MeshStandardMaterial;
  glowMat: THREE.MeshBasicMaterial;
  private planMat: THREE.MeshBasicMaterial;
  private cursor: THREE.Mesh;
  private cursorMat: THREE.MeshBasicMaterial;
  /** light-emitting objects, refreshed on rebuild */
  lights: LightSpot[] = [];
  lightsVersion = 0;

  constructor(private gfx: Gfx, private world: World) {
    gfx.scene.add(this.group);
    this.solidMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.78, metalness: 0.02 });
    this.glowMat = new THREE.MeshBasicMaterial({ vertexColors: true, toneMapped: false });
    this.planMat = new THREE.MeshBasicMaterial({ color: 0x58b7ff, transparent: true, opacity: 0.42, depthWrite: false });
    this.cursorMat = new THREE.MeshBasicMaterial({ color: 0x6dff8a, transparent: true, opacity: 0.6, depthWrite: false });
    this.cursor = new THREE.Mesh(new THREE.BufferGeometry(), this.cursorMat);
    this.cursor.visible = false;
    this.cursor.userData.noAO = true;
    this.cursor.renderOrder = 6;
    this.cursor.frustumCulled = false;
    this.group.add(this.cursor);
    gfx.onNight.push((night) => {
      // screens and lamps burn brighter after dark
      this.glowMat.color.setScalar(0.75 + night * 1.6);
    });
  }

  model(type: string): ModelResult {
    let m = this.models.get(type);
    if (!m) {
      m = buildObjectModel(type);
      this.models.set(type, m);
    }
    return m;
  }

  /** build every model up front so the first placement does not hitch */
  warm() {
    for (const o of OBJECTS) this.model(o.id);
  }

  private batch(map: Map<string, Batch>, type: string, geo: THREE.BufferGeometry, mat: THREE.Material, opts: any): Batch {
    let b = map.get(type);
    if (!b) {
      b = new Batch(geo, mat, this.group, { cap: 16, colors: false, ...opts });
      map.set(type, b);
    }
    return b;
  }

  rebuild() {
    for (const b of this.solid.values()) b.begin();
    for (const b of this.glow.values()) b.begin();
    for (const b of this.plan.values()) b.begin();
    this.lights.length = 0;
    for (const o of this.world.objects.values()) {
      const def = OBJ[o.type];
      const m = this.model(o.type);
      const [fw, fd] = footprint(def, o.rot);
      const cx = o.x + fw / 2, cz = o.y + fd / 2, yaw = rotYaw(o.rot);
      if (!o.built) {
        this.batch(this.plan, o.type, m.solid, this.planMat, { noAO: true, renderOrder: 5 }).add(cx, 0, cz, 1, 1, 1, yaw);
        continue;
      }
      this.batch(this.solid, o.type, m.solid, this.solidMat, { cast: true, receive: true }).add(cx, 0, cz, 1, 1, 1, yaw);
      if (m.glow) this.batch(this.glow, o.type, m.glow, this.glowMat, { noAO: true }).add(cx, 0, cz, 1, 1, 1, yaw);
      if (def.light) this.lights.push({ x: cx, z: cz, r: def.light });
    }
    for (const b of this.solid.values()) b.end();
    for (const b of this.glow.values()) b.end();
    for (const b of this.plan.values()) b.end();
    this.lightsVersion++;
  }

  update() {
    if (this.world.dirtyObjects) {
      this.world.dirtyObjects = false;
      this.rebuild();
    }
  }

  /** placement ghost */
  setCursor(type: string | null, x = 0, y = 0, rot = 0, ok = true) {
    if (!type) {
      this.cursor.visible = false;
      return;
    }
    const m = this.model(type);
    if (this.cursor.geometry !== m.solid) this.cursor.geometry = m.solid;
    const [fw, fd] = footprint(OBJ[type], rot);
    this.cursor.position.set(x + fw / 2, 0.02, y + fd / 2);
    this.cursor.rotation.y = rotYaw(rot);
    this.cursorMat.color.setHex(ok ? 0x6dff8a : 0xff5a4a);
    this.cursor.visible = true;
  }
}
