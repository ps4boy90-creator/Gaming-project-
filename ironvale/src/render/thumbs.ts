import * as THREE from 'three';
import { DOORS, OBJECTS, STAFF, WALLS } from '../data/defs';
import type { ModelResult } from './modelkit';
import { MB } from './modelkit';
import { buildFigure } from './characters';

/**
 * Renders small product-shot thumbnails of every buildable thing with a throwaway
 * renderer, and returns them as data URLs keyed by id.
 */
export function renderThumbnails(model: (id: string) => ModelResult, size = 112): Record<string, string> {
  const out: Record<string, string> = {};
  let renderer: THREE.WebGLRenderer;
  try {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size * 2;
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  } catch {
    return out;
  }
  renderer.setPixelRatio(1);
  renderer.setSize(size * 2, size * 2, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.setClearColor(0x000000, 0);
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xdfeaff, 0x8a7f6a, 1.5));
  const sun = new THREE.DirectionalLight(0xfff2dc, 3.2);
  sun.position.set(3, 6, 4);
  scene.add(sun);
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100);
  const solidMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.78 });
  const glowMat = new THREE.MeshBasicMaterial({ vertexColors: true, toneMapped: false });
  const holder = new THREE.Group();
  scene.add(holder);
  const el = (38 * Math.PI) / 180, az = Math.PI / 4;
  const dir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), Math.cos(az) * Math.cos(el));

  const shoot = (id: string, obj: THREE.Object3D) => {
    holder.clear();
    holder.add(obj);
    const box = new THREE.Box3().setFromObject(obj);
    const c = box.getCenter(new THREE.Vector3());
    const sz = box.getSize(new THREE.Vector3());
    const r = Math.max(0.42, Math.hypot(sz.x, sz.z) * 0.5 * 0.92, sz.y * 0.5 + Math.hypot(sz.x, sz.z) * 0.22);
    cam.left = -r; cam.right = r; cam.top = r; cam.bottom = -r;
    cam.position.copy(c).addScaledVector(dir, 20);
    cam.lookAt(c);
    cam.updateProjectionMatrix();
    renderer.render(scene, cam);
    out[id] = renderer.domElement.toDataURL('image/png');
  };
  const fromModel = (m: ModelResult) => {
    const g = new THREE.Group();
    g.add(new THREE.Mesh(m.solid, solidMat));
    if (m.glow) g.add(new THREE.Mesh(m.glow, glowMat));
    return g;
  };

  for (const o of OBJECTS) {
    try {
      shoot('obj:' + o.id, fromModel(model(o.id)));
    } catch (e) {
      console.warn('thumbnail failed', o.id, e);
    }
  }
  // walls: a short run of each type
  const wallCols: Record<string, [number, number]> = {
    concrete: [0xcfd0cb, 0x8b9299], brick: [0xb9694b, 0xd9d3c4], perimeter: [0xb4b6b1, 0x6c737b],
  };
  for (const w of WALLS) {
    if (!w.id) continue;
    const b = new MB();
    if (w.key === 'fence') {
      for (const x of [-0.75, 0, 0.75]) b.box(0.07, 1.5, 0.07, x, 0, 0, 0x9aa3ad);
      b.box(1.5, 0.04, 0.04, 0, 1.45, 0, 0x9aa3ad).box(1.5, 0.04, 0.04, 0, 0.03, 0, 0x9aa3ad);
      for (let i = 0; i < 9; i++) b.box(0.02, 1.9, 0.02, -0.62 + i * 0.155, -0.2, 0, 0xc4ccd4, { rz: 0.75 }).box(0.02, 1.9, 0.02, -0.62 + i * 0.155, -0.2, 0, 0xc4ccd4, { rz: -0.75 });
    } else if (w.key === 'window') {
      b.box(1.6, 0.48, 0.26, 0, 0, 0, 0xcfd0cb).box(1.6, 0.28, 0.26, 0, 1.02, 0, 0xcfd0cb);
      b.box(0.4, 0.54, 0.26, -0.6, 0.48, 0, 0xcfd0cb).box(0.4, 0.54, 0.26, 0.6, 0.48, 0, 0xcfd0cb);
      for (let i = -2; i <= 2; i++) b.box(0.03, 0.54, 0.03, i * 0.14, 0.48, 0, 0x3d444d);
      b.box(0.8, 0.5, 0.02, 0, 0.5, 0, 0x9fd0ea);
      b.box(1.6, 0.06, 0.32, 0, 1.3, 0, 0x8b9299);
    } else {
      const [body, cap] = wallCols[w.key];
      b.box(1.6, w.height, w.thick, 0, 0, 0, body).box(1.6, 0.07, w.thick + 0.07, 0, w.height, 0, cap);
      if (w.key === 'brick') for (let r = 0; r < 11; r++) b.box(1.61, 0.012, w.thick + 0.005, 0, 0.1 + r * 0.108, 0, 0xe6dccd);
      if (w.key === 'perimeter') for (let i = 0; i < 7; i++) b.torus(0.1, 0.012, -0.66 + i * 0.22, w.height + 0.1, 0, 0xc9d1d9, 10, { rz: Math.PI / 2 });
    }
    shoot('wall:' + w.id, fromModel(b.build()));
  }
  // doors
  const doorCols = [0, 0x8e6b4a, 0x565d66, 0x3f6aa8, 0x59626c];
  for (const d of DOORS) {
    if (!d.id) continue;
    const b = new MB();
    const frame = d.id === 2 ? 0x565d66 : d.id === 3 ? 0x3a5a8c : d.id === 4 ? 0x4a525c : 0xa7adb3;
    const h = d.id === 4 ? 1.6 : 1.3;
    b.box(0.11, h, 0.3, -0.445, 0, 0, frame).box(0.11, h, 0.3, 0.445, 0, 0, frame).box(1.0, 0.16, 0.3, 0, h - 0.16, 0, frame);
    if (d.id === 2 || d.id === 4) {
      for (let i = 0; i < 7; i++) b.cyl(0.022, 0.022, h - 0.2, -0.36 + i * 0.12, 0.02, 0, 0x7b858f, 6);
      b.box(0.78, 0.06, 0.06, 0, 0.5, 0, doorCols[d.id]);
      if (d.id === 4) b.box(0.5, 0.2, 0.08, 0, 0.9, 0, 0xe2b93b);
    } else {
      b.rbox(0.76, h - 0.2, 0.07, 0, 0.02, 0, doorCols[d.id], 0.015);
      if (d.id === 3) b.box(0.3, 0.26, 0.09, 0, 0.68, 0, 0xa9d4ea).box(0.76, 0.07, 0.09, 0, 0.3, 0, 0xe2b93b);
      else b.box(0.6, 0.36, 0.085, 0, 0.14, 0, 0x7d5d40).box(0.6, 0.36, 0.085, 0, 0.6, 0, 0x7d5d40);
      b.box(0.05, 0.05, 0.14, 0.28, 0.52, 0, 0xd9c27a);
    }
    shoot('door:' + d.id, fromModel(b.build()));
  }
  // staff portraits
  const looks: Record<string, [number, number, number]> = {
    warden: [0x3b4252, 0x2b303b, 0], guard: [0x2f4a80, 0x1f2a44, 1], doctor: [0xf2f3f1, 0x4d9a94, 0], cook: [0xf4f4f2, 0x6b7480, 2],
    janitor: [0x4f8f7a, 0x3d6f5f, 0], workman: [0xe2c435, 0x3f5f8a, 3], teacher: [0x8a6a4a, 0x4a4f5a, 0], psych: [0x8a6fb0, 0x4a4458, 0],
    chaplain: [0x2c2c33, 0x23232a, 0],
  };
  for (const s of STAFF) {
    const [torso, legs, hat] = looks[s.role];
    shoot('staff:' + s.role, buildFigure({ torso, legs, skin: 0xe5b48c, hair: s.role === 'warden' ? 0x9a9a9a : 0x3d2b1c, hat, bald: false }));
  }
  shoot('prisoner:0', buildFigure({ torso: 0x5f93c9, legs: 0x5f93c9, skin: 0xd29b6f, hair: 0x2b2118, hat: 0, bald: false }));
  shoot('prisoner:1', buildFigure({ torso: 0xe8842c, legs: 0xe8842c, skin: 0xe5b48c, hair: 0x2b2118, hat: 0, bald: true }));
  shoot('prisoner:2', buildFigure({ torso: 0xc8443a, legs: 0xc8443a, skin: 0x9a5f3b, hair: 0x1b1b1f, hat: 0, bald: false }));
  shoot('visitor', buildFigure({ torso: 0x5b8fb5, legs: 0x3a4a66, skin: 0xf1c7a3, hair: 0x7a5633, hat: 0, bald: false }));
  shoot('riot', buildFigure({ torso: 0x23272e, legs: 0x1b1e24, skin: 0xe5b48c, hair: 0x2b2118, hat: 4, bald: false }));

  renderer.dispose();
  renderer.forceContextLoss();
  return out;
}
