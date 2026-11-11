import * as THREE from 'three';
import { FLOORS, MAP_H, MAP_W, ROOMS } from '../data/defs';
import type { World } from '../world/world';
import type { Gfx } from './gfx';
import { Batch } from './batch';
import type { LightSpot } from './objects';
import { makeGlowTexture, makeGridTexture, makeLabelTexture } from './textures';

/** Build grid, room tints and labels, drag previews, floor blueprints and night lighting. */
export class Overlays {
  private group = new THREE.Group();
  private grid: THREE.Mesh;
  private zoneMesh: THREE.Mesh | null = null;
  private zoneMat: THREE.MeshBasicMaterial;
  private labels = new THREE.Group();
  private tiles: Batch;
  private boxes: Batch;
  private floorPlan: Batch;
  private pools: Batch;
  private poolMat: THREE.MeshBasicMaterial;
  private indoor: THREE.Mesh | null = null;
  private indoorMat: THREE.MeshBasicMaterial;
  private hover: THREE.Mesh;
  private seenTopo = -1;
  private seenLights = -1;
  private seenPlans = -1;
  showZones = false;
  showGrid = false;
  private col = new THREE.Color();
  private night = 0;

  constructor(private gfx: Gfx, private world: World) {
    this.group.userData.noAO = true;
    gfx.scene.add(this.group);
    this.group.add(this.labels);

    const gt = makeGridTexture();
    gt.repeat.set(MAP_W, MAP_H);
    this.grid = new THREE.Mesh(
      new THREE.PlaneGeometry(MAP_W, MAP_H),
      new THREE.MeshBasicMaterial({ map: gt, transparent: true, opacity: 0.14, depthWrite: false }),
    );
    this.grid.rotation.x = -Math.PI / 2;
    this.grid.position.set(MAP_W / 2, 0.03, MAP_H / 2);
    this.grid.userData.noAO = true;
    this.grid.renderOrder = 3;
    this.grid.visible = false;
    this.group.add(this.grid);

    this.zoneMat = new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.4, depthWrite: false });

    const flat = new THREE.PlaneGeometry(1, 1);
    flat.rotateX(-Math.PI / 2);
    this.tiles = new Batch(flat, new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.45, depthWrite: false, depthTest: false }), this.group, { noAO: true, cap: 256, renderOrder: 8 });
    const box = new THREE.BoxGeometry(1, 1, 1);
    box.translate(0, 0.5, 0);
    this.boxes = new Batch(box, new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.5, depthWrite: false }), this.group, { noAO: true, cap: 256, renderOrder: 9 });
    this.floorPlan = new Batch(flat, new THREE.MeshBasicMaterial({ color: 0x58b7ff, transparent: true, opacity: 0.3, depthWrite: false }), this.group, { noAO: true, cap: 256, colors: false, renderOrder: 4 });

    this.poolMat = new THREE.MeshBasicMaterial({
      map: makeGlowTexture(), color: 0xffd9a0, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false,
    });
    this.pools = new Batch(flat, this.poolMat, this.group, { noAO: true, cap: 64, colors: false, renderOrder: 2 });
    this.indoorMat = new THREE.MeshBasicMaterial({ color: 0xffcf8f, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false });

    const hg = new THREE.RingGeometry(0.56, 0.68, 4, 1);
    hg.rotateZ(Math.PI / 4);
    hg.rotateX(-Math.PI / 2);
    this.hover = new THREE.Mesh(hg, new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.85, depthTest: false }));
    this.hover.renderOrder = 10;
    this.hover.visible = false;
    this.hover.userData.noAO = true;
    this.group.add(this.hover);

    gfx.onNight.push((n) => {
      this.night = n;
      this.poolMat.opacity = n * 0.5;
      this.indoorMat.opacity = n * 0.2;
      this.pools.visible = n > 0.02;
      if (this.indoor) this.indoor.visible = n > 0.02;
    });
  }

  setHover(x: number, y: number, on: boolean) {
    this.hover.visible = on;
    this.hover.position.set(x + 0.5, 0.04, y + 0.5);
  }

  /** flat highlight over a set of tiles */
  setTiles(tiles: number[], color: number) {
    this.tiles.begin();
    this.col.setHex(color);
    const w = this.world.w;
    for (const t of tiles) this.tiles.add((t % w) + 0.5, 0.05, Math.floor(t / w) + 0.5, 1, 1, 1, 0, this.col);
    this.tiles.end();
  }
  /** wall-shaped ghost over a set of tiles */
  setBoxes(tiles: number[], color: number, h = 1.3) {
    this.boxes.begin();
    this.col.setHex(color);
    const w = this.world.w;
    for (const t of tiles) this.boxes.add((t % w) + 0.5, 0, Math.floor(t / w) + 0.5, 0.92, h, 0.92, 0, this.col);
    this.boxes.end();
  }
  clearPreview() {
    this.tiles.begin();
    this.tiles.end();
    this.boxes.begin();
    this.boxes.end();
  }

  private rebuildZones() {
    const w = this.world;
    if (this.zoneMesh) {
      this.group.remove(this.zoneMesh);
      this.zoneMesh.geometry.dispose();
      this.zoneMesh = null;
    }
    let n = 0;
    for (let i = 0; i < w.n; i++) if (w.zone[i]) n++;
    if (n) {
      const pos = new Float32Array(n * 12), col = new Float32Array(n * 12), idx = new Uint32Array(n * 6);
      let k = 0;
      const c = new THREE.Color();
      for (let i = 0; i < w.n; i++) {
        const z = w.zone[i];
        if (!z) continue;
        const x = i % w.w, y = Math.floor(i / w.w);
        const room = w.roomAtTile(i);
        c.setHex(ROOMS[z].color, THREE.SRGBColorSpace);
        if (room && !room.valid) c.multiplyScalar(0.55);
        const p = k * 12, m = 0.04;
        const xs = [x + m, x + m, x + 1 - m, x + 1 - m], zs = [y + m, y + 1 - m, y + 1 - m, y + m];
        for (let j = 0; j < 4; j++) {
          pos[p + j * 3] = xs[j]; pos[p + j * 3 + 1] = 0.035; pos[p + j * 3 + 2] = zs[j];
          col[p + j * 3] = c.r; col[p + j * 3 + 1] = c.g; col[p + j * 3 + 2] = c.b;
        }
        const v = k * 4, q = k * 6;
        idx[q] = v; idx[q + 1] = v + 1; idx[q + 2] = v + 2; idx[q + 3] = v; idx[q + 4] = v + 2; idx[q + 5] = v + 3;
        k++;
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      g.setAttribute('color', new THREE.BufferAttribute(col, 3));
      g.setIndex(new THREE.BufferAttribute(idx, 1));
      this.zoneMesh = new THREE.Mesh(g, this.zoneMat);
      this.zoneMesh.frustumCulled = false;
      this.zoneMesh.renderOrder = 3;
      this.zoneMesh.userData.noAO = true;
      this.group.add(this.zoneMesh);
    }
    // labels
    for (const s of [...this.labels.children]) {
      this.labels.remove(s);
      ((s as THREE.Sprite).material as THREE.SpriteMaterial).dispose();
    }
    for (const r of w.rooms.values()) {
      const def = ROOMS[r.type];
      const tex = makeLabelTexture(r.valid ? def.name : `${def.name}  !`, '#ffffff', r.valid ? 'rgba(20,24,30,0.74)' : 'rgba(176,44,32,0.9)');
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, depthWrite: false, toneMapped: false }));
      const img = tex.image as HTMLCanvasElement;
      sp.userData.aspect = img.width / img.height;
      sp.userData.valid = r.valid;
      sp.position.set(r.cx + 0.5, 1.7, r.cy + 0.5);
      sp.renderOrder = 18;
      this.labels.add(sp);
    }
  }

  private rebuildIndoor() {
    const w = this.world;
    if (this.indoor) {
      this.group.remove(this.indoor);
      this.indoor.geometry.dispose();
      this.indoor = null;
    }
    let n = 0;
    for (let i = 0; i < w.n; i++) if (!FLOORS[w.floor[i]].outdoor && !w.wall[i]) n++;
    if (!n) return;
    const pos = new Float32Array(n * 12), idx = new Uint32Array(n * 6);
    let k = 0;
    for (let i = 0; i < w.n; i++) {
      if (FLOORS[w.floor[i]].outdoor || w.wall[i]) continue;
      const x = i % w.w, y = Math.floor(i / w.w), p = k * 12;
      const xs = [x, x, x + 1, x + 1], zs = [y, y + 1, y + 1, y];
      for (let j = 0; j < 4; j++) {
        pos[p + j * 3] = xs[j]; pos[p + j * 3 + 1] = 0.022; pos[p + j * 3 + 2] = zs[j];
      }
      const v = k * 4, q = k * 6;
      idx[q] = v; idx[q + 1] = v + 1; idx[q + 2] = v + 2; idx[q + 3] = v; idx[q + 4] = v + 2; idx[q + 5] = v + 3;
      k++;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setIndex(new THREE.BufferAttribute(idx, 1));
    this.indoor = new THREE.Mesh(g, this.indoorMat);
    this.indoor.frustumCulled = false;
    this.indoor.userData.noAO = true;
    this.indoor.renderOrder = 1;
    this.indoor.visible = this.night > 0.02;
    this.group.add(this.indoor);
  }

  setLights(lights: LightSpot[], extra: number[][]) {
    this.pools.begin();
    for (const l of lights) this.pools.add(l.x, 0.03, l.z, l.r * 2, 1, l.r * 2);
    for (const [x, z] of extra) this.pools.add(x, 0.03, z, 11, 1, 11);
    this.pools.end();
  }

  update(lights: LightSpot[], lightsVersion: number, streetLights: number[][], planVersion: number) {
    const w = this.world;
    if (w.topoVersion !== this.seenTopo || w.dirtyZones) {
      this.seenTopo = w.topoVersion;
      w.dirtyZones = false;
      this.rebuildZones();
      this.rebuildIndoor();
    }
    if (lightsVersion !== this.seenLights) {
      this.seenLights = lightsVersion;
      this.setLights(lights, streetLights);
    }
    if (planVersion !== this.seenPlans) {
      this.seenPlans = planVersion;
      this.floorPlan.begin();
      for (let i = 0; i < w.n; i++) if (w.planFloor[i]) this.floorPlan.add((i % w.w) + 0.5, 0.03, Math.floor(i / w.w) + 0.5, 0.9, 1, 0.9);
      this.floorPlan.end();
    }
    this.grid.visible = this.showGrid;
    if (this.zoneMesh) this.zoneMesh.visible = this.showZones;
    const k = Math.min(2.4, Math.max(0.75, this.gfx.zoom / 30));
    for (const s of this.labels.children) {
      const sp = s as THREE.Sprite;
      sp.visible = this.showZones || !sp.userData.valid;
      sp.scale.set(0.62 * k * sp.userData.aspect, 0.62 * k, 1);
    }
  }
}
