// Standalone dev preview for the procedural models (see models-preview.html).
import * as THREE from 'three';
import { OBJECTS } from './data/defs';
import type { ModelResult } from './render/modelkit';
import { buildObjectModel, buildScenery, type SceneryKind } from './render/models';

const SCENERY: SceneryKind[] = ['tree_oak', 'tree_round', 'tree_pine', 'bush', 'rock', 'streetlight', 'car', 'truck', 'bus'];

const q = new URLSearchParams(location.search);
const only = q.get('only')?.split(',').map((s) => s.trim()).filter(Boolean) ?? null;
const az = THREE.MathUtils.degToRad(Number(q.get('az') ?? 45));
const el = THREE.MathUtils.degToRad(Number(q.get('el') ?? 38));
const ppu = Number(q.get('ppu') ?? 110);
const rowWidth = Number(q.get('width') ?? 22);
const showPeople = q.get('people') === '1';
const showLabels = q.get('labels') !== '0';

interface Item {
  id: string;
  w: number;
  d: number;
  scenery: boolean;
  model: ModelResult;
  /** screen-space extents relative to the item's origin */
  sx0: number; sx1: number; sy0: number; sy1: number;
  dummyAt: number;
  pos: THREE.Vector3;
}

// camera basis --------------------------------------------------------------
const camDir = new THREE.Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az)); // towards camera
const right = new THREE.Vector3(Math.cos(az), 0, -Math.sin(az));
const up = new THREE.Vector3().crossVectors(camDir, right).normalize();
const fwdGround = new THREE.Vector3(-Math.sin(az), 0, -Math.cos(az)); // away from camera on the ground

// build items ---------------------------------------------------------------
const items: Item[] = [];
const stats: Record<string, unknown>[] = [];
const missing: string[] = [];
(window as any).__missing = missing;
function addItem(id: string, w: number, d: number, scenery: boolean) {
  if (only && !only.includes(id) && !only.includes((scenery ? 's:' : 'o:') + id)) return;
  let model: ModelResult;
  try {
    model = scenery ? buildScenery(id as SceneryKind) : buildObjectModel(id);
  } catch (e) {
    console.warn(String(e));
    missing.push(id);
    return;
  }
  const bb = new THREE.Box3();
  model.solid.computeBoundingBox();
  bb.copy(model.solid.boundingBox!);
  if (model.glow) {
    model.glow.computeBoundingBox();
    bb.union(model.glow.boundingBox!);
  }
  const tris = (g?: THREE.BufferGeometry) => (g ? (g.index ? g.index.count : g.attributes.position.count) / 3 : 0);
  const m = 0.02;
  stats.push({
    id,
    scenery,
    tris: tris(model.solid),
    glowTris: tris(model.glow),
    min: bb.min.toArray().map((v) => +v.toFixed(3)),
    max: bb.max.toArray().map((v) => +v.toFixed(3)),
    inFootprint: scenery || (bb.min.x >= -w / 2 + m && bb.max.x <= w / 2 - m && bb.min.z >= -d / 2 + m && bb.max.z <= d / 2 - m),
    belowFloor: bb.min.y < -1e-4,
  });
  // screen extents, including the floor patch and the scale dummy
  const ext = new THREE.Box3().copy(bb);
  ext.expandByPoint(new THREE.Vector3(-w / 2 - 0.1, 0, -d / 2 - 0.1));
  ext.expandByPoint(new THREE.Vector3(w / 2 + 0.1, 1, d / 2 + 0.1));
  let sx0 = Infinity, sx1 = -Infinity, sy0 = Infinity, sy1 = -Infinity;
  const p = new THREE.Vector3();
  for (let i = 0; i < 8; i++) {
    p.set(i & 1 ? ext.max.x : ext.min.x, i & 2 ? ext.max.y : ext.min.y, i & 4 ? ext.max.z : ext.min.z);
    const x = p.dot(right), y = p.dot(up);
    sx0 = Math.min(sx0, x); sx1 = Math.max(sx1, x); sy0 = Math.min(sy0, y); sy1 = Math.max(sy1, y);
  }
  // the scale dummy stands to the screen-right of the object so it never hides it
  const dummyAt = sx1 + 0.3;
  sx1 += 0.55;
  items.push({ id, w, d, scenery, model, sx0, sx1, sy0, sy1, dummyAt, pos: new THREE.Vector3() });
}
for (const o of OBJECTS) addItem(o.id, o.w, o.d, false);
for (const k of SCENERY) {
  const sz: Record<string, [number, number]> = { bus: [5, 2], truck: [4, 2], car: [3, 2], tree_oak: [2, 2] };
  const [w, d] = sz[k] ?? [1, 1];
  addItem(k, w, d, true);
}

// flow layout in screen space ----------------------------------------------
const PAD = 0.35;
let cx = 0, cy = 0, rowH = 0;
let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
const LABEL_H = 0.42;
for (const it of items) {
  const w = it.sx1 - it.sx0 + PAD;
  const h = it.sy1 - it.sy0 + PAD + LABEL_H;
  if (cx > 0 && cx + w > rowWidth) {
    cx = 0;
    cy -= rowH;
    rowH = 0;
  }
  // origin of the item in screen coordinates
  const ox = cx - it.sx0 + PAD / 2;
  const oy = cy - h - it.sy0 + PAD / 2 + LABEL_H;
  it.pos.copy(right).multiplyScalar(ox).addScaledVector(fwdGround, oy / Math.sin(el));
  minX = Math.min(minX, cx); maxX = Math.max(maxX, cx + w);
  minY = Math.min(minY, cy - h); maxY = Math.max(maxY, cy);
  cx += w;
  rowH = Math.max(rowH, h);
}

// renderer -------------------------------------------------------------------
const W = Math.max(64, Math.round((maxX - minX) * ppu));
const H = Math.max(64, Math.round((maxY - minY) * ppu));
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.outputColorSpace = THREE.SRGBColorSpace;
const wrap = document.getElementById('wrap')!;
wrap.style.width = W + 'px';
wrap.style.height = H + 'px';
wrap.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x9fb0a6);

const cam = new THREE.OrthographicCamera(minX, maxX, maxY, minY, -200, 400);
// The layout was computed with screen coordinates measured from the world origin.
cam.position.copy(camDir).multiplyScalar(100);
cam.up.set(0, 1, 0);
cam.lookAt(0, 0, 0);
cam.updateMatrixWorld();

scene.add(new THREE.HemisphereLight(0xe6eeff, 0xa09c8c, 1.7));
const sun = new THREE.DirectionalLight(0xfff2dc, 2.3);
const centre = new THREE.Vector3()
  .addScaledVector(right, (minX + maxX) / 2)
  .addScaledVector(fwdGround, (minY + maxY) / 2 / Math.sin(el));
const sunDir = new THREE.Vector3(-0.55, 1.25, 0.8).normalize();
sun.position.copy(centre).addScaledVector(sunDir, 80);
sun.target.position.copy(centre);
scene.add(sun.target);
sun.castShadow = true;
const span = Math.max(maxX - minX, (maxY - minY) / Math.sin(el)) * 0.75 + 6;
sun.shadow.camera.left = -span; sun.shadow.camera.right = span;
sun.shadow.camera.top = span; sun.shadow.camera.bottom = -span;
sun.shadow.camera.near = 1; sun.shadow.camera.far = 200;
sun.shadow.mapSize.set(4096, 4096);
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.02;
sun.shadow.radius = 2.5;
scene.add(sun);

const ground = new THREE.Mesh(new THREE.PlaneGeometry(600, 600), new THREE.MeshStandardMaterial({ color: 0x8fa58a, roughness: 1 }));
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.002;
ground.receiveShadow = true;
scene.add(ground);

const solidMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.8 });
const glowMat = new THREE.MeshBasicMaterial({ vertexColors: true, toneMapped: false });
const tileA = new THREE.MeshStandardMaterial({ color: 0xe2ddd0, roughness: 0.95 });
const tileB = new THREE.MeshStandardMaterial({ color: 0xd0cabb, roughness: 0.95 });
const tileGeo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
const dummyMat = new THREE.MeshStandardMaterial({ color: 0x8e9299, roughness: 0.9 });
const poseMat = new THREE.MeshStandardMaterial({ color: 0xe0883a, roughness: 0.9 });

/** 0.95-tall chibi stand-in: capsule body + big head. */
function dummy(mat: THREE.Material, pose: 'stand' | 'sit' | 'lie' = 'stand'): THREE.Group {
  const g = new THREE.Group();
  const add = (geo: THREE.BufferGeometry, x: number, y: number, z: number) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, y, z);
    m.castShadow = true;
    m.receiveShadow = true;
    g.add(m);
    return m;
  };
  if (pose === 'stand') {
    add(new THREE.CapsuleGeometry(0.15, 0.3, 4, 10), 0, 0.3, 0);
    add(new THREE.SphereGeometry(0.2, 14, 10), 0, 0.75, 0);
  } else if (pose === 'sit') {
    // origin = seat surface under the hips, facing +Z
    add(new THREE.CapsuleGeometry(0.15, 0.12, 4, 10), 0, 0.2, 0);
    add(new THREE.SphereGeometry(0.2, 14, 10), 0, 0.56, 0);
    const legs = add(new THREE.BoxGeometry(0.26, 0.1, 0.22), 0, 0.06, 0.16);
    legs.castShadow = true;
  } else {
    // origin = centre of the lying surface, head toward -Z
    const b = add(new THREE.CapsuleGeometry(0.13, 0.42, 4, 10), 0, 0.13, 0.2);
    b.rotation.x = Math.PI / 2;
    add(new THREE.SphereGeometry(0.2, 14, 10), 0, 0.2, -0.38);
  }
  return g;
}

type Slot = ['stand' | 'sit' | 'lie', number, number, number];
const SLOTS: Record<string, Slot[]> = {
  bed: [['lie', 0, 0.34, 0]],
  bunk: [['lie', 0, 0.34, 0], ['lie', 0, 0.95, 0]],
  medical_bed: [['lie', 0, 0.38, 0]],
  weight_bench: [['lie', 0, 0.3, 0]],
  toilet: [['sit', 0, 0.24, 0.05]],
  chair: [['sit', 0, 0.26, 0]],
  school_desk: [['sit', 0, 0.26, -0.15]],
  bench: [['sit', -0.5, 0.26, 0], ['sit', 0.5, 0.26, 0]],
  pew: [['sit', -0.5, 0.26, 0], ['sit', 0.5, 0.26, 0]],
  sofa: [['sit', -0.5, 0.24, 0], ['sit', 0.5, 0.24, 0]],
  outdoor_bench: [['sit', -0.5, 0.26, 0], ['sit', 0.5, 0.26, 0]],
  visit_table: [['sit', 0, 0.26, -1], ['sit', 0, 0.26, 1]],
  office_desk: [['sit', 0.5, 0.26, -0.5]],
  cctv_monitor: [['sit', 0, 0.26, 0.3]],
  guard_tower: [['stand', 0, 1.9, 0]],
  shower: [['stand', 0, 0.03, 0]],
  metal_detector: [['stand', 0, 0.02, 0]],
};

const labels: { el: HTMLElement; p: THREE.Vector3 }[] = [];
for (const it of items) {
  const g = new THREE.Group();
  g.position.copy(it.pos);
  // checker patch the size of the footprint
  const fw = Math.max(1, Math.round(it.w)), fd = Math.max(1, Math.round(it.d));
  for (let i = 0; i < fw; i++)
    for (let j = 0; j < fd; j++) {
      const t = new THREE.Mesh(tileGeo, (i + j) % 2 ? tileA : tileB);
      t.position.set(-fw / 2 + 0.5 + i, 0, -fd / 2 + 0.5 + j);
      t.receiveShadow = true;
      g.add(t);
    }
  const solid = new THREE.Mesh(it.model.solid, solidMat);
  solid.castShadow = true;
  solid.receiveShadow = true;
  g.add(solid);
  if (it.model.glow) g.add(new THREE.Mesh(it.model.glow, glowMat));
  // scale dummy beside the object
  const d = dummy(dummyMat);
  d.position.copy(right).multiplyScalar(it.dummyAt);
  g.add(d);
  if (showPeople && SLOTS[it.id] && !it.scenery) {
    for (const [pose, x, y, z] of SLOTS[it.id]) {
      const pd = dummy(poseMat, pose);
      pd.position.set(x, y, z);
      g.add(pd);
    }
  }
  scene.add(g);

  if (showLabels) {
    const e = document.createElement('div');
    e.className = 'lbl';
    const st = stats.find((s) => s.id === it.id && s.scenery === it.scenery)!;
    e.innerHTML = `${it.id} <small>${st.tris}t</small>`;
    wrap.appendChild(e);
    // label sits just below the item's screen box
    const p = it.pos.clone().addScaledVector(right, (it.sx0 + it.sx1) / 2).addScaledVector(up, it.sy0 - 0.08);
    labels.push({ el: e, p });
  }
}

renderer.render(scene, cam);
const v = new THREE.Vector3();
for (const l of labels) {
  v.copy(l.p).project(cam);
  l.el.style.left = ((v.x * 0.5 + 0.5) * W).toFixed(1) + 'px';
  l.el.style.top = ((-v.y * 0.5 + 0.5) * H).toFixed(1) + 'px';
}
// second frame so shadows are definitely in
requestAnimationFrame(() => {
  renderer.render(scene, cam);
  (window as any).__stats = stats;
  (window as any).__size = [W, H];
  (window as any).__ready = true;
});
