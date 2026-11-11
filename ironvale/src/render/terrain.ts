import * as THREE from 'three';
import { FLOORS, MAP_W, MAP_H } from '../data/defs';
import { RNG } from '../core/util';
import type { World } from '../world/world';
import type { Gfx } from './gfx';
import { makeFloorTextures, type FloorTex } from './textures';
import { buildScenery, type SceneryKind } from './models';

export const ROAD_Z = MAP_H + 6.5;
export const ENTRY_X = Math.floor(MAP_W / 2);

/** Ground, lawn, painted floors, road and decorative scenery. */
export class Terrain {
  private tex: Record<string, FloorTex>;
  private floorMeshes: (THREE.Mesh | null)[] = [];
  private floorMats: THREE.MeshStandardMaterial[] = [];
  group = new THREE.Group();
  solidMat: THREE.MeshStandardMaterial;
  glowMat: THREE.MeshBasicMaterial;

  constructor(private gfx: Gfx, private world: World) {
    this.tex = makeFloorTextures();
    gfx.scene.add(this.group);
    this.solidMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.82, metalness: 0.0 });
    this.glowMat = new THREE.MeshBasicMaterial({ vertexColors: true, toneMapped: false });

    // wild ground far beyond the plot
    const G = 520;
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(G, G), new THREE.MeshStandardMaterial({ map: this.tex.wild.tex, roughness: 1 }));
    this.tex.wild.tex.repeat.set(G / this.tex.wild.span, G / this.tex.wild.span);
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(MAP_W / 2, 0, MAP_H / 2);
    ground.receiveShadow = true;
    this.group.add(ground);

    // mown lawn inside the plot
    const lawnTex = this.tex.grass.tex.clone();
    lawnTex.needsUpdate = true;
    lawnTex.repeat.set(MAP_W / this.tex.grass.span, MAP_H / this.tex.grass.span);
    const lawn = new THREE.Mesh(new THREE.PlaneGeometry(MAP_W, MAP_H), new THREE.MeshStandardMaterial({ map: lawnTex, roughness: 1 }));
    lawn.rotation.x = -Math.PI / 2;
    lawn.position.set(MAP_W / 2, 0.006, MAP_H / 2);
    lawn.receiveShadow = true;
    this.group.add(lawn);

    // plot boundary: a thin pale kerb line
    const kerbMat = new THREE.MeshStandardMaterial({ color: 0xd9d4c4, roughness: 0.9 });
    const kerb = (w: number, d: number, x: number, z: number) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, 0.05, d), kerbMat);
      m.position.set(x, 0.02, z);
      m.receiveShadow = true;
      this.group.add(m);
    };
    kerb(MAP_W + 0.3, 0.15, MAP_W / 2, -0.075);
    kerb(MAP_W + 0.3, 0.15, MAP_W / 2, MAP_H + 0.075);
    kerb(0.15, MAP_H, -0.075, MAP_H / 2);
    kerb(0.15, MAP_H, MAP_W + 0.075, MAP_H / 2);

    for (const f of FLOORS) {
      const t = this.tex[f.key];
      const mat = new THREE.MeshStandardMaterial({ map: t.tex, roughness: t.rough, metalness: 0 });
      this.floorMats[f.id] = mat;
      this.floorMeshes[f.id] = null;
    }
    this.buildRoad();
    this.buildScenery();
  }

  /** Rebuild the painted floor meshes (cheap: a few thousand quads). */
  rebuildFloors() {
    const w = this.world;
    const counts = new Array(FLOORS.length).fill(0);
    for (let i = 0; i < w.n; i++) counts[w.floor[i]]++;
    for (const f of FLOORS) {
      const old = this.floorMeshes[f.id];
      if (old) {
        this.group.remove(old);
        old.geometry.dispose();
        this.floorMeshes[f.id] = null;
      }
      if (f.id === 0 || counts[f.id] === 0) continue;
      const n = counts[f.id];
      const pos = new Float32Array(n * 12), uv = new Float32Array(n * 8), nor = new Float32Array(n * 12);
      const idx = new Uint32Array(n * 6);
      const span = this.tex[f.key].span;
      let k = 0;
      for (let i = 0; i < w.n; i++) {
        if (w.floor[i] !== f.id) continue;
        const x = i % w.w, z = (i / w.w) | 0;
        const p = k * 12, u = k * 8, q = k * 6, v = k * 4;
        pos[p] = x; pos[p + 1] = 0; pos[p + 2] = z;
        pos[p + 3] = x; pos[p + 4] = 0; pos[p + 5] = z + 1;
        pos[p + 6] = x + 1; pos[p + 7] = 0; pos[p + 8] = z + 1;
        pos[p + 9] = x + 1; pos[p + 10] = 0; pos[p + 11] = z;
        for (let j = 0; j < 4; j++) nor[p + j * 3 + 1] = 1;
        uv[u] = x / span; uv[u + 1] = -z / span;
        uv[u + 2] = x / span; uv[u + 3] = -(z + 1) / span;
        uv[u + 4] = (x + 1) / span; uv[u + 5] = -(z + 1) / span;
        uv[u + 6] = (x + 1) / span; uv[u + 7] = -z / span;
        idx[q] = v; idx[q + 1] = v + 1; idx[q + 2] = v + 2; idx[q + 3] = v; idx[q + 4] = v + 2; idx[q + 5] = v + 3;
        k++;
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
      g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
      g.setIndex(new THREE.BufferAttribute(idx, 1));
      const m = new THREE.Mesh(g, this.floorMats[f.id]);
      m.position.y = 0.014;
      m.receiveShadow = true;
      m.frustumCulled = false;
      this.group.add(m);
      this.floorMeshes[f.id] = m;
    }
  }

  private buildRoad() {
    const len = 520;
    const rt = this.tex.road.tex;
    const g = new THREE.PlaneGeometry(len, 4.6);
    const uv = g.attributes.uv;
    for (let i = 0; i < uv.count; i++) uv.setX(i, uv.getX(i) * (len / this.tex.road.span));
    const road = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ map: rt, roughness: 0.92 }));
    road.rotation.x = -Math.PI / 2;
    road.position.set(MAP_W / 2, 0.012, ROAD_Z);
    road.receiveShadow = true;
    this.group.add(road);

    // pavements
    const paveTex = this.tex.paving.tex.clone();
    paveTex.needsUpdate = true;
    paveTex.repeat.set(len / 4, 0.25);
    const paveMat = new THREE.MeshStandardMaterial({ map: paveTex, roughness: 0.9 });
    for (const dz of [-2.8, 2.8]) {
      const p = new THREE.Mesh(new THREE.BoxGeometry(len, 0.07, 1.0), paveMat);
      p.position.set(MAP_W / 2, 0.035, ROAD_Z + dz);
      p.receiveShadow = true;
      this.group.add(p);
    }
    // entrance apron joining the road to the plot
    const apTex = this.tex.asphalt.tex.clone();
    apTex.needsUpdate = true;
    apTex.repeat.set(14 / 6, 4 / 6);
    const apron = new THREE.Mesh(new THREE.PlaneGeometry(14, 3.25), new THREE.MeshStandardMaterial({ map: apTex, roughness: 0.95 }));
    apron.rotation.x = -Math.PI / 2;
    apron.position.set(ENTRY_X + 0.5, 0.011, MAP_H + 1.72);
    apron.receiveShadow = true;
    this.group.add(apron);
    // parking bay lines
    const lineMat = new THREE.MeshBasicMaterial({ color: 0xdedbd0 });
    for (let i = 0; i <= 4; i++) {
      for (const side of [-1, 1]) {
        const l = new THREE.Mesh(new THREE.PlaneGeometry(0.07, 2.2), lineMat);
        l.rotation.x = -Math.PI / 2;
        l.position.set(ENTRY_X + 0.5 + side * (2.2 + i * 1.15), 0.016, MAP_H + 1.5);
        this.group.add(l);
      }
    }
  }

  private addInstanced(kind: SceneryKind, items: { x: number; z: number; s: number; r: number; tint: number }[]) {
    if (!items.length) return;
    const model = buildScenery(kind);
    const im = new THREE.InstancedMesh(model.solid, this.solidMat, items.length);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3();
    const up = new THREE.Vector3(0, 1, 0), c = new THREE.Color();
    let glow: THREE.InstancedMesh | null = null;
    if (model.glow) glow = new THREE.InstancedMesh(model.glow, this.glowMat, items.length);
    items.forEach((it, i) => {
      q.setFromAxisAngle(up, it.r);
      p.set(it.x, 0, it.z);
      s.set(it.s, it.s, it.s);
      m.compose(p, q, s);
      im.setMatrixAt(i, m);
      im.setColorAt(i, c.setScalar(it.tint));
      glow?.setMatrixAt(i, m);
    });
    im.castShadow = true;
    im.receiveShadow = true;
    im.frustumCulled = false;
    this.group.add(im);
    if (glow) {
      glow.frustumCulled = false;
      this.group.add(glow);
    }
  }

  private buildScenery() {
    const r = new RNG(4242);
    const kinds: SceneryKind[] = ['tree_oak', 'tree_round', 'tree_pine', 'bush', 'rock'];
    const lists: Record<string, { x: number; z: number; s: number; r: number; tint: number }[]> = {};
    for (const k of kinds) lists[k] = [];
    const inPlot = (x: number, z: number, m: number) => x > -m && x < MAP_W + m && z > -m && z < MAP_H + m;
    const nearRoad = (z: number) => Math.abs(z - ROAD_Z) < 4.6;
    const nearEntry = (x: number, z: number) => Math.abs(x - ENTRY_X) < 9 && z > MAP_H - 1 && z < ROAD_Z;
    const placed: [number, number][] = [];
    const tryPlace = (x: number, z: number, minD: number) => {
      for (const [px, pz] of placed) if ((px - x) ** 2 + (pz - z) ** 2 < minD * minD) return false;
      placed.push([x, z]);
      return true;
    };
    // forest belt with clumps: denser further away
    for (let i = 0; i < 2600; i++) {
      const x = r.range(-110, MAP_W + 110), z = r.range(-110, MAP_H + 120);
      if (inPlot(x, z, 2.5) || nearRoad(z) || nearEntry(x, z)) continue;
      const dEdge = Math.max(Math.max(-x, x - MAP_W), Math.max(-z, z - MAP_H));
      const density = 0.18 + Math.min(1, dEdge / 40) * 0.75;
      const clump = 0.5 + 0.5 * Math.sin(x * 0.11 + 1.3) * Math.cos(z * 0.13 + 0.4);
      if (r.next() > density * (0.45 + clump * 0.75)) continue;
      const roll = r.next();
      const kind: SceneryKind = roll < 0.34 ? 'tree_oak' : roll < 0.6 ? 'tree_round' : roll < 0.82 ? 'tree_pine' : roll < 0.95 ? 'bush' : 'rock';
      const big = kind.startsWith('tree');
      if (!tryPlace(x, z, big ? 2.3 : 1.2)) continue;
      lists[kind].push({ x, z, s: big ? r.range(1.0, 1.75) : r.range(0.8, 1.5), r: r.range(0, Math.PI * 2), tint: r.range(0.86, 1.08) });
    }
    for (const k of kinds) this.addInstanced(k, lists[k]);
    // street lights along the road
    const lights: { x: number; z: number; s: number; r: number; tint: number }[] = [];
    for (let x = -96; x <= MAP_W + 96; x += 16) lights.push({ x: x + 4, z: ROAD_Z - 2.75, s: 1, r: 0, tint: 1 });
    this.addInstanced('streetlight', lights);
    this.streetLights = lights.map((l) => [l.x, l.z + 0.6]);
  }
  /** positions of street light pools (x, z) for the night glow layer */
  streetLights: number[][] = [];

  /** small data-URL swatch of a floor texture for the UI */
  floorSwatch(key: string): string {
    try {
      const src = this.tex[key].tex.image as HTMLCanvasElement;
      const c = document.createElement('canvas');
      c.width = c.height = 108;
      const span = this.tex[key].span;
      const px = (src.width / span) * 2;
      c.getContext('2d')!.drawImage(src, 0, 0, px, px, 0, 0, 108, 108);
      return c.toDataURL('image/jpeg', 0.85);
    } catch {
      return '';
    }
  }

  update() {
    if (this.world.dirtyFloor) {
      this.world.dirtyFloor = false;
      this.rebuildFloors();
    }
  }
}
