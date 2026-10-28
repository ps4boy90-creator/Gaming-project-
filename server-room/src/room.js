// The hall around the racks: raised floor, walls, ceiling and lighting,
// overhead services, containment, cooling, fire suppression and the props
// that make it read as a working room.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { ROWS, RACK, PER_ROW, ROW_X0, ROW_HALF, BUSWAY_Z, TRAY_Z, RUNWAY_Z } from './racks.js';
import * as TX from './textures.js';
import { Painter, pbr, FONT } from './painter.js';
import { CableBatch, CABLE } from './cables.js';
import { Rng, damp } from './util.js';

export const ROOM = { minX: -7.8, maxX: 7.8, minZ: -7.2, maxZ: 7.2, h: 3.2 };
export const COLD_AISLES = [-2.7, 2.7];
export const LIGHT_LINES = [
  ...[-5.4, -2.7, 0, 2.7, 5.4].map((z) => ({ axis: 'x', c: z, a: -ROW_HALF, b: ROW_HALF })),
  { axis: 'z', c: -5.55, a: -6.6, b: 6.6 },
  { axis: 'z', c: 5.55, a: -6.6, b: 6.6 },
];

// ------------------------------------------------------------------ batch --
// Static props are merged per material to keep draw calls low.
class StaticBatch {
  constructor() { this.byMat = new Map(); }
  add(geo, mat, matrix) {
    let g = geo.index ? geo.toNonIndexed() : geo;
    if (g === geo) g = geo.clone();
    for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(k)) g.deleteAttribute(k);
    if (!g.getAttribute('uv')) g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(g.getAttribute('position').count * 2), 2));
    if (matrix) g.applyMatrix4(matrix);
    if (!this.byMat.has(mat)) this.byMat.set(mat, []);
    this.byMat.get(mat).push(g);
    return g;
  }
  box(mat, w, h, d, x, y, z, ry = 0) {
    const m = new THREE.Matrix4().makeRotationY(ry).setPosition(x, y, z);
    return this.add(new THREE.BoxGeometry(w, h, d), mat, m);
  }
  cyl(mat, r0, r1, h, x, y, z, { seg = 16, rx = 0, rz = 0, ry = 0 } = {}) {
    const m = new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(rx, ry, rz)).setPosition(x, y, z);
    return this.add(new THREE.CylinderGeometry(r0, r1, h, seg), mat, m);
  }
  build(parent) {
    for (const [mat, geos] of this.byMat) {
      const mesh = new THREE.Mesh(mergeGeometries(geos), mat);
      mesh.matrixAutoUpdate = false;
      parent.add(mesh);
    }
  }
}

const std = (color, r = 0.5, m = 0, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: r, metalness: m, ...extra });
const scaleUv = (geo, su, sv) => {
  const uv = geo.getAttribute('uv');
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * su, uv.getY(i) * sv);
  return geo;
};
const setRepeat = (tex, x, y) => {
  for (const t of Object.values(tex)) {
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(x, y);
  }
  return tex;
};

// Sign helper: canvas -> plane mesh (optionally double-sided back-to-back).
function sign(w, h, px, draw, opts = {}) {
  const mat = TX.signMaterial(Math.round(w * px), Math.round(h * px), draw, opts);
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
  return mesh;
}

function textLines(ctx, lines, x, y, { size = 40, color = '#111', weight = 700, gap = 1.25, align = 'center', font = FONT } = {}) {
  ctx.fillStyle = color;
  ctx.textAlign = align;
  ctx.textBaseline = 'middle';
  lines.forEach((l, i) => {
    const s = typeof l === 'string' ? size : l.size;
    ctx.font = `${typeof l === 'string' ? weight : l.weight ?? weight} ${s}px ${font}`;
    ctx.fillText(typeof l === 'string' ? l : l.t, x, y + i * size * gap);
  });
}

// ------------------------------------------------------------------ build --
export function buildRoom({ quality = 'high' } = {}) {
  const group = new THREE.Group();
  group.name = 'room';
  const batch = new StaticBatch();
  const cables = new CableBatch();
  const rng = new Rng(99);
  const colliders = [];
  const occluders = []; // boxes for the light bake
  const interactables = [];
  const updaters = [];
  const W = ROOM.maxX - ROOM.minX, D = ROOM.maxZ - ROOM.minZ, H = ROOM.h;

  // shared materials
  const M = {
    galv: std(0x9aa0a6, 0.42, 0.85),
    alu: std(0xb9bec4, 0.32, 0.9),
    strut: std(0x8e959c, 0.48, 0.8),
    rod: std(0x6f757b, 0.5, 0.8),
    yellow: std(0xe7b416, 0.42, 0),
    yellowDark: std(0xc99a0c, 0.5, 0),
    whitePaint: std(0xeeeeea, 0.55, 0.1),
    offWhite: pbr(TX.powderCoat('#d4d2cb', 52), {}),
    darkGrey: pbr(TX.powderCoat('#2a2c30', 53), {}),
    black: std(0x111214, 0.5, 0.3),
    rubber: std(0x1a1b1c, 0.85, 0),
    red: std(0xb3161b, 0.38, 0.25),
    redPaint: std(0xa8151a, 0.32, 0.15),
    chrome: std(0xdde2e6, 0.12, 1),
    brass: std(0xb08d3a, 0.3, 1),
    doorGrey: pbr(TX.powderCoat('#6b7177', 54), {}),
    glassDark: std(0x0b0f12, 0.05, 0.9),
    lightHousing: std(0xf0f0ee, 0.4, 0.3),
  };

  // ---------------------------------------------------------- shell --
  const floorTex = setRepeat(TX.floorTiles(), W / 1.2, D / 1.2);
  const floorMat = pbr(floorTex, { name: 'floor' });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(W, D).rotateX(-Math.PI / 2), floorMat);
  floor.position.set((ROOM.minX + ROOM.maxX) / 2, 0, (ROOM.minZ + ROOM.maxZ) / 2);
  group.add(floor);

  const perfTex = setRepeat(TX.perfTile(), PER_ROW, 1);
  const perfMat = pbr(perfTex, { name: 'perf' });
  const perfGeos = [];
  for (const c of COLD_AISLES) for (const dz of [-0.6, 0.6]) {
    perfGeos.push(new THREE.PlaneGeometry(PER_ROW * RACK.w, 0.6).rotateX(-Math.PI / 2).translate(0, 0.0015, c + dz));
  }
  const perf = new THREE.Mesh(mergeGeometries(perfGeos), perfMat);
  group.add(perf);

  const wallTex = setRepeat(TX.wallPaint(), 1, 1);
  const wallMat = pbr(wallTex, { name: 'wall' });
  const wall = (len, x, z, ry) => {
    const g = scaleUv(new THREE.PlaneGeometry(len, H), len / 1.6, H / 1.6);
    const m = new THREE.Mesh(g, wallMat);
    m.position.set(x, H / 2, z);
    m.rotation.y = ry;
    group.add(m);
  };
  wall(W, 0, ROOM.minZ, 0);
  wall(W, 0, ROOM.maxZ, Math.PI);
  wall(D, ROOM.minX, 0, Math.PI / 2);
  wall(D, ROOM.maxX, 0, -Math.PI / 2);
  // rubber skirting
  batch.box(M.rubber, W, 0.1, 0.012, 0, 0.05, ROOM.minZ + 0.006);
  batch.box(M.rubber, W, 0.1, 0.012, 0, 0.05, ROOM.maxZ - 0.006);
  batch.box(M.rubber, 0.012, 0.1, D, ROOM.minX + 0.006, 0.05, 0);
  batch.box(M.rubber, 0.012, 0.1, D, ROOM.maxX - 0.006, 0.05, 0);

  const ceilTex = setRepeat(TX.ceilingTile(), W / 0.6, D / 0.6);
  const ceilMat = pbr(ceilTex, { name: 'ceiling' });
  const ceiling = new THREE.Mesh(new THREE.PlaneGeometry(W, D).rotateX(Math.PI / 2), ceilMat);
  ceiling.position.set(0, H, 0);
  group.add(ceiling);

  colliders.push(
    { minX: ROOM.minX - 1, maxX: ROOM.maxX + 1, minZ: ROOM.minZ - 1, maxZ: ROOM.minZ },
    { minX: ROOM.minX - 1, maxX: ROOM.maxX + 1, minZ: ROOM.maxZ, maxZ: ROOM.maxZ + 1 },
    { minX: ROOM.minX - 1, maxX: ROOM.minX, minZ: ROOM.minZ - 1, maxZ: ROOM.maxZ + 1 },
    { minX: ROOM.maxX, maxX: ROOM.maxX + 1, minZ: ROOM.minZ - 1, maxZ: ROOM.maxZ + 1 },
  );

  // ------------------------------------------------------- lighting --
  // Continuous linear LED luminaires over every aisle; each is matched by a
  // RectAreaLight of the same footprint so highlights line up with fixtures.
  const lightMat = new THREE.MeshStandardMaterial({ color: 0x000000, emissive: 0xf3f6ff, emissiveIntensity: 9, roughness: 1, metalness: 0 });
  const areaLights = [];
  for (const L of LIGHT_LINES) {
    const len = L.b - L.a, mid = (L.a + L.b) / 2;
    const [x, z] = L.axis === 'x' ? [mid, L.c] : [L.c, mid];
    const ry = L.axis === 'x' ? 0 : Math.PI / 2;
    batch.box(M.lightHousing, len + 0.04, 0.05, 0.17, x, H - 0.025, z, ry);
    const diff = new THREE.Mesh(new THREE.PlaneGeometry(len, 0.12).rotateX(Math.PI / 2), lightMat);
    diff.position.set(x, H - 0.051, z);
    diff.rotation.y = ry;
    group.add(diff);
    const light = new THREE.RectAreaLight(0xf2f5ff, 1, len, 0.12);
    light.position.set(x, H - 0.06, z);
    if (L.axis === 'x') light.rotation.set(-Math.PI / 2, 0, 0);
    else light.rotation.set(-Math.PI / 2, Math.PI / 2, 0, 'YXZ');
    light.userData.base = 1;
    group.add(light);
    areaLights.push(light);
  }
  // sky = light from above; ground = bounce off the pale floor onto ceilings and undersides
  const hemi = new THREE.HemisphereLight(0x8a9097, 0xc3c8cc, 0.55);
  group.add(hemi);

  // --------------------------------------------- overhead services --
  for (const row of ROWS) {
    const wz = (lz) => row.z + row.facing * lz;
    const len = PER_ROW * RACK.w + 0.3;
    // power busway with a tap-off box and whip feeding every rack
    batch.box(M.alu, len, 0.11, 0.15, 0, 2.29, wz(BUSWAY_Z));
    batch.box(M.strut, len, 0.012, 0.05, 0, 2.34, wz(BUSWAY_Z));
    for (let i = 0; i < PER_ROW; i++) {
      const x = ROW_X0 + i * RACK.w + 0.12;
      batch.box(M.darkGrey, 0.17, 0.15, 0.13, x, 2.155, wz(BUSWAY_Z));
      batch.box(M.yellow, 0.06, 0.03, 0.002, x - 0.03, 2.18, wz(BUSWAY_Z) + row.facing * 0.066);
      const zb = wz(BUSWAY_Z), zr = wz(-0.52);
      cables.add([
        new THREE.Vector3(x + 0.04, 2.08, zb),
        new THREE.Vector3(x + 0.05, 2.04, (zb + zr) / 2 + row.facing * 0.03),
        new THREE.Vector3(x + 0.07, 2.02, zr - row.facing * 0.02),
        new THREE.Vector3(x + 0.07, 1.99, zr),
      ], 0.008, CABLE.black, { segLen: 0.02 });
    }
    // ladder tray
    const tz = wz(TRAY_Z);
    batch.box(M.galv, len, 0.075, 0.012, 0, 2.47, tz - 0.225);
    batch.box(M.galv, len, 0.075, 0.012, 0, 2.47, tz + 0.225);
    for (let x = -len / 2 + 0.1; x < len / 2; x += 0.3) batch.box(M.galv, 0.03, 0.014, 0.45, x, 2.44, tz);
    // cables laid in the tray
    const trayColors = [CABLE.blue, CABLE.blue, CABLE.yellow, CABLE.grey, CABLE.blue, CABLE.black, CABLE.red, CABLE.blue, CABLE.green];
    trayColors.forEach((col, k) => {
      const r = rng.range(0.012, 0.022);
      const oz = -0.18 + (k / (trayColors.length - 1)) * 0.36;
      const pts = [];
      for (let x = -len / 2; x <= len / 2 + 1e-6; x += 0.6) pts.push(new THREE.Vector3(x, 2.447 + r + (k % 3) * 0.006, tz + oz + rng.range(-0.012, 0.012)));
      cables.add(pts, r, col, { segLen: 0.15, radial: 6 });
    });
    // yellow fibre runway with spill-outs into selected racks
    const rz = wz(RUNWAY_Z);
    batch.box(M.yellow, len, 0.008, 0.3, 0, 2.66, rz);
    batch.box(M.yellow, len, 0.1, 0.006, 0, 2.71, rz - 0.147);
    batch.box(M.yellow, len, 0.1, 0.006, 0, 2.71, rz + 0.147);
    for (let x = -len / 2 + 0.05; x < len / 2; x += 1.83) batch.box(M.yellowDark, 0.09, 0.115, 0.315, x, 2.712, rz);
    for (let k = 0; k < 4; k++) {
      const pts = [];
      for (let x = -len / 2; x <= len / 2 + 1e-6; x += 0.7) pts.push(new THREE.Vector3(x, 2.672 + k * 0.004, rz - 0.09 + k * 0.06 + rng.range(-0.01, 0.01)));
      cables.add(pts, 0.009, k % 2 ? CABLE.aqua : CABLE.yellow, { segLen: 0.2 });
    }
    for (let i = 0; i < PER_ROW; i++) {
      if (!(i === 6 || i % 4 === 1)) continue;
      const x = ROW_X0 + i * RACK.w + 0.1;
      const edge = rz - row.facing * 0.15;
      cables.add([
        new THREE.Vector3(x, 2.69, rz - row.facing * 0.1),
        new THREE.Vector3(x, 2.68, edge - row.facing * 0.04),
        new THREE.Vector3(x, 2.5, wz(RUNWAY_Z - 0.06)),
        new THREE.Vector3(x, 2.0, wz(RUNWAY_Z - 0.06)),
      ], 0.024, '#e8b512', { segLen: 0.03, radial: 10 });
    }
    // threaded rods and unistrut trapezes
    for (let x = -len / 2 + 0.15; x < len / 2; x += 1.8) {
      for (const [z0, z1, y] of [[BUSWAY_Z - 0.11, BUSWAY_Z + 0.11, 2.225], [TRAY_Z - 0.26, TRAY_Z + 0.26, 2.415], [RUNWAY_Z - 0.18, RUNWAY_Z + 0.18, 2.637]]) {
        batch.box(M.strut, 0.041, 0.041, Math.abs(z1 - z0), x, y, wz((z0 + z1) / 2));
        for (const zz of [z0 + 0.01, z1 - 0.01]) batch.cyl(M.rod, 0.005, 0.005, H - y, x, (H + y) / 2, wz(zz), { seg: 6 });
      }
    }
    // row end identification on both end panels
    for (const end of [-1, 1]) {
      const s = sign(0.42, 0.26, 600, (ctx, w, h) => {
        ctx.fillStyle = '#1b3f8f';
        ctx.fillRect(0, 0, w, h);
        textLines(ctx, [`ROW ${row.id}`], w / 2, h * 0.38, { size: 70, color: '#fff', weight: 800 });
        textLines(ctx, [`${row.id}01 – ${row.id}${PER_ROW}`], w / 2, h * 0.78, { size: 34, color: '#d8e2f7', weight: 600 });
      });
      s.position.set(end * (ROW_HALF + 0.002), 1.7, row.z);
      s.rotation.y = end * Math.PI / 2;
      group.add(s);
    }
  }

  // VESDA sampling pipe runs (red) with sample points
  for (const z of [-4.2, -1.2, 1.2, 4.2]) {
    batch.cyl(M.red, 0.0125, 0.0125, W - 0.4, 0, H - 0.07, z, { seg: 10, rz: Math.PI / 2 });
    for (let x = ROOM.minX + 1.2; x < ROOM.maxX - 1; x += 2.4) batch.cyl(M.red, 0.007, 0.007, 0.04, x, H - 0.1, z, { seg: 8 });
  }
  // smoke detectors, sprinklers and clean-agent nozzles
  for (let x = -6; x <= 6; x += 3.6) {
    for (const z of [-3.9, -1.35, 1.35, 3.9, -6.3, 6.3]) {
      batch.cyl(M.whitePaint, 0.065, 0.07, 0.04, x, H - 0.02, z, { seg: 20 });
      batch.cyl(M.whitePaint, 0.035, 0.05, 0.012, x, H - 0.046, z, { seg: 16 });
    }
    for (const z of [-2.7, 2.7]) {
      batch.cyl(M.chrome, 0.012, 0.012, 0.06, x + 1.2, H - 0.03, z, { seg: 10 });
      batch.cyl(M.chrome, 0.03, 0.006, 0.012, x + 1.2, H - 0.065, z, { seg: 12 });
    }
  }
  for (const [x, z] of [[-2.4, -5.4], [2.4, -5.4], [-2.4, 5.4], [2.4, 5.4], [0, 0]]) {
    batch.cyl(M.galv, 0.016, 0.016, 0.12, x, H - 0.06, z, { seg: 10 });
    batch.cyl(M.chrome, 0.035, 0.035, 0.03, x, H - 0.13, z, { seg: 14 });
  }
  // CCTV domes in two corners
  for (const [x, z] of [[ROOM.minX + 0.5, ROOM.maxZ - 0.5], [ROOM.maxX - 0.5, ROOM.minZ + 0.5]]) {
    batch.cyl(M.whitePaint, 0.08, 0.08, 0.02, x, H - 0.01, z, { seg: 20 });
    const dome = new THREE.Mesh(new THREE.SphereGeometry(0.07, 20, 10, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), std(0x0a0a0c, 0.05, 0.6, { transparent: true, opacity: 0.85 }));
    dome.position.set(x, H - 0.02, z);
    group.add(dome);
  }

  // hanging aisle signs at both ends of every aisle
  const aisles = [
    { z: -5.4, name: 'HOT AISLE 1', hot: true },
    { z: -2.7, name: 'COLD AISLE 1', hot: false },
    { z: 0, name: 'HOT AISLE 2', hot: true },
    { z: 2.7, name: 'COLD AISLE 2', hot: false },
    { z: 5.4, name: 'HOT AISLE 3', hot: true },
  ];
  for (const a of aisles) {
    for (const end of [-1, 1]) {
      const draw = (ctx, w, h) => {
        ctx.fillStyle = a.hot ? '#b52a20' : '#1f5fae';
        ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 6;
        ctx.strokeRect(10, 10, w - 20, h - 20);
        textLines(ctx, [a.name], w / 2, h / 2 + 2, { size: 64, color: '#fff', weight: 800 });
      };
      const x = end * (ROW_HALF + 0.35);
      for (const face of [1, -1]) {
        const s = sign(0.9, 0.22, 500, draw);
        s.position.set(x + face * 0.004, 2.5, a.z);
        s.rotation.y = face * Math.PI / 2;
        group.add(s);
      }
      for (const dz of [-0.38, 0.38]) batch.cyl(M.rod, 0.003, 0.003, H - 2.61, x, (H + 2.61) / 2, a.z + dz, { seg: 5 });
    }
  }

  // ------------------------------------------------- containment ----
  // Cold aisle 2 is fully contained: polycarbonate roof and bi-parting doors.
  const cz = COLD_AISLES[1], z0 = cz - 0.9, z1 = cz + 0.9;
  const polyMat = new THREE.MeshPhysicalMaterial({ color: 0xe6eef4, roughness: 0.18, metalness: 0, transparent: true, opacity: 0.16, side: THREE.DoubleSide, depthWrite: false });
  const roof = new THREE.Mesh(new THREE.PlaneGeometry(PER_ROW * RACK.w, 1.8).rotateX(-Math.PI / 2), polyMat);
  roof.position.set(0, 2.06, cz);
  roof.renderOrder = 3;
  roof.userData.noAO = true;
  group.add(roof);
  batch.box(M.alu, PER_ROW * RACK.w, 0.05, 0.04, 0, 2.04, z0 + 0.02);
  batch.box(M.alu, PER_ROW * RACK.w, 0.05, 0.04, 0, 2.04, z1 - 0.02);
  for (let x = -ROW_HALF; x <= ROW_HALF + 1e-6; x += 1.2) batch.box(M.alu, 0.035, 0.035, 1.8, x, 2.055, cz);

  const glassMat = new THREE.MeshPhysicalMaterial({ color: 0xdfe9ee, roughness: 0.05, metalness: 0, transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false });
  const doorSticker = TX.signMaterial(512, 160, (ctx, w, h) => {
    ctx.fillStyle = '#1f5fae';
    ctx.fillRect(0, 0, w, h);
    textLines(ctx, ['COLD AISLE 2', { t: 'KEEP DOORS CLOSED', size: 30, weight: 600 }], w / 2, h * 0.36, { size: 54, color: '#fff', weight: 800, gap: 1.3 });
  });
  const leaves = [];
  for (const end of [-1, 1]) {
    const x = end * (ROW_HALF + 0.035);
    batch.box(M.alu, 0.06, 2.06, 0.05, x, 1.03, z0 + 0.025);
    batch.box(M.alu, 0.06, 2.06, 0.05, x, 1.03, z1 - 0.025);
    batch.box(M.alu, 0.07, 0.12, 1.8, x, 2.0, cz);
    for (const side of [-1, 1]) {
      const leaf = new THREE.Group();
      const frameGeo = mergeGeometries([
        new THREE.BoxGeometry(0.03, 1.92, 0.035).translate(0, 0.96, -0.43),
        new THREE.BoxGeometry(0.03, 1.92, 0.035).translate(0, 0.96, 0.43),
        new THREE.BoxGeometry(0.03, 0.05, 0.9).translate(0, 1.895, 0),
        new THREE.BoxGeometry(0.03, 0.08, 0.9).translate(0, 0.04, 0),
        new THREE.BoxGeometry(0.04, 0.3, 0.025).translate(0, 1.05, -side * 0.38),
      ]);
      leaf.add(new THREE.Mesh(frameGeo, M.alu));
      const glass = new THREE.Mesh(new THREE.PlaneGeometry(0.84, 1.8).rotateY(Math.PI / 2).translate(0, 0.98, 0), glassMat);
      glass.renderOrder = 3;
      glass.userData.noAO = true;
      leaf.add(glass);
      for (const f of [1, -1]) {
        const st = new THREE.Mesh(new THREE.PlaneGeometry(0.42, 0.13), doorSticker);
        st.position.set(f * 0.017, 1.5, 0);
        st.rotation.y = f * Math.PI / 2;
        leaf.add(st);
      }
      const closedZ = cz + side * 0.45;
      leaf.position.set(x, 0, closedZ);
      group.add(leaf);
      leaves.push({ leaf, end, side, closedZ, x });
    }
  }
  const contDoors = [-1, 1].map((end) => ({ end, x: end * (ROW_HALF + 0.035), open: 0, collider: { minX: end * (ROW_HALF + 0.035) - 0.06, maxX: end * (ROW_HALF + 0.035) + 0.06, minZ: z0, maxZ: z1, active: true } }));
  for (const d of contDoors) colliders.push(d.collider);
  updaters.push((dt, player) => {
    for (const d of contDoors) {
      const dist = Math.hypot(player.x - d.x, player.z - cz);
      const target = dist < 2.1 ? 1 : 0;
      d.open = damp(d.open, target, target ? 4.5 : 2.5, dt);
      d.collider.active = d.open < 0.7;
    }
    for (const l of leaves) {
      const d = contDoors.find((c) => c.end === l.end);
      l.leaf.position.z = l.closedZ + l.side * d.open * 0.86;
    }
  });

  // ---------------------------------------------------------- CRACs --
  const cracUnits = [
    { name: 'CRAC-01', x: ROOM.maxX - 0.45, z: -2.7, face: -1, sup: 17.8, ret: 29.6 },
    { name: 'CRAC-02', x: ROOM.maxX - 0.45, z: 2.7, face: -1, sup: 18.1, ret: 30.4 },
    { name: 'CRAC-03', x: ROOM.minX + 0.45, z: -2.7, face: 1, sup: 17.6, ret: 28.9 },
  ];
  const grille = TX.eggCrate();
  setRepeat(grille, 4, 10);
  const grilleMat = pbr(grille);
  for (const c of cracUnits) {
    const face = pbr(TX.cracFace(c.name, c.sup, c.ret), { emissiveIntensity: 1.4 });
    const mats = [M.offWhite, M.offWhite, grilleMat, M.offWhite, M.offWhite, M.offWhite];
    mats[c.face < 0 ? 1 : 0] = face;
    const unit = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.95, 2.5), mats);
    unit.position.set(c.x, 0.975, c.z);
    group.add(unit);
    batch.box(M.darkGrey, 0.92, 0.035, 2.52, c.x, 0.0175, c.z);
    const box = { minX: c.x - 0.47, maxX: c.x + 0.47, minZ: c.z - 1.27, maxZ: c.z + 1.27 };
    colliders.push(box);
    occluders.push(new THREE.Box3(new THREE.Vector3(c.x - 0.45, 0, c.z - 1.25), new THREE.Vector3(c.x + 0.45, 1.95, c.z + 1.25)));
    const fx = c.x + c.face * 0.452;
    // controller display hit-box (middle panel, upper half)
    interactables.push({
      kind: 'crac', name: c.name, sup: c.sup, ret: c.ret,
      box: new THREE.Box3(new THREE.Vector3(fx - 0.03, 1.08, c.z - 0.36), new THREE.Vector3(fx + 0.03, 1.55, c.z + 0.36)),
    });
  }

  // ---------------------------------------------- fire suppression --
  const cylX = ROOM.minX + 0.27;
  const cylZs = [1.75, 2.3, 2.85];
  const fmLabel = TX.signMaterial(256, 256, (ctx, w, h) => {
    ctx.fillStyle = '#f4f2ea';
    ctx.fillRect(0, 0, w, h);
    textLines(ctx, ['FM-200', { t: 'HFC-227ea', size: 26, weight: 600 }, { t: 'CLEAN AGENT', size: 24, weight: 600 }, { t: '106 kg', size: 30, weight: 700 }], w / 2, 50, { size: 56, color: '#111', weight: 800, gap: 0.95 });
  });
  for (const z of cylZs) {
    batch.cyl(M.redPaint, 0.19, 0.19, 1.2, cylX, 0.62, z, { seg: 28 });
    const dome = new THREE.SphereGeometry(0.19, 28, 10, 0, Math.PI * 2, 0, Math.PI / 2).scale(1, 0.7, 1);
    batch.add(dome, M.redPaint, new THREE.Matrix4().makeTranslation(cylX, 1.22, z));
    batch.cyl(M.redPaint, 0.18, 0.19, 0.04, cylX, 0.02, z, { seg: 28 });
    batch.cyl(M.brass, 0.045, 0.05, 0.1, cylX, 1.4, z, { seg: 14 });
    batch.cyl(M.black, 0.06, 0.06, 0.07, cylX, 1.48, z, { seg: 14 });
    batch.cyl(M.chrome, 0.03, 0.03, 0.012, cylX + 0.06, 1.48, z, { seg: 14, rz: Math.PI / 2 });
    cables.add([
      new THREE.Vector3(cylX, 1.52, z), new THREE.Vector3(cylX, 1.62, z + 0.04),
      new THREE.Vector3(cylX - 0.1, 1.72, z + 0.08), new THREE.Vector3(cylX - 0.12, 1.78, z + 0.1),
    ], 0.018, '#202022', { segLen: 0.02, radial: 8 });
    const lbl = new THREE.Mesh(new THREE.CylinderGeometry(0.1915, 0.1915, 0.3, 28, 1, true, -0.7, 1.4), fmLabel);
    lbl.position.set(cylX, 0.85, z);
    lbl.rotation.y = Math.PI / 2;
    group.add(lbl);
  }
  batch.box(M.black, 0.03, 0.06, 1.6, ROOM.minX + 0.07, 1.0, 2.3);
  batch.cyl(M.redPaint, 0.035, 0.035, 1.5, cylX - 0.12, 1.79, 2.3, { seg: 14, rx: Math.PI / 2 });
  batch.cyl(M.redPaint, 0.035, 0.035, H - 1.79, cylX - 0.12, (H + 1.79) / 2, 3.05, { seg: 14 });
  batch.cyl(M.redPaint, 0.03, 0.03, ROOM.maxX - ROOM.minX - 1, 0, H - 0.18, 3.05, { seg: 12, rz: Math.PI / 2 });
  colliders.push({ minX: ROOM.minX, maxX: ROOM.minX + 0.5, minZ: 1.5, maxZ: 3.1 });
  occluders.push(new THREE.Box3(new THREE.Vector3(ROOM.minX, 0, 1.5), new THREE.Vector3(ROOM.minX + 0.47, 1.5, 3.1)));
  // release panel and warning sign
  batch.box(M.redPaint, 0.12, 0.48, 0.38, ROOM.minX + 0.06, 1.45, 4.1);
  const relPanel = sign(0.3, 0.4, 600, (ctx, w, h) => {
    ctx.fillStyle = '#b3161b';
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = '#0d1a10';
    ctx.fillRect(30, 40, w - 60, 70);
    textLines(ctx, ['SYSTEM NORMAL'], w / 2, 76, { size: 30, color: '#6dff9a', font: 'monospace' });
    textLines(ctx, ['AGENT RELEASE', { t: 'CONTROL PANEL', size: 28 }], w / 2, 160, { size: 32, color: '#fff', weight: 800 });
    ctx.fillStyle = '#ffd400';
    ctx.fillRect(w / 2 - 70, 200, 140, 26);
    textLines(ctx, ['ABORT  ·  HOLD'], w / 2, 213, { size: 20, color: '#111', weight: 800 });
  }, { emissive: 0.25 });
  relPanel.position.set(ROOM.minX + 0.121, 1.45, 4.1);
  relPanel.rotation.y = Math.PI / 2;
  group.add(relPanel);
  const warn = sign(0.9, 0.5, 500, (ctx, w, h) => {
    ctx.fillStyle = '#ffd400';
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, w, 70);
    textLines(ctx, ['WARNING'], w / 2, 36, { size: 46, color: '#ffd400', weight: 900 });
    textLines(ctx, ['THIS ROOM IS PROTECTED BY A', 'CLEAN AGENT FIRE SUPPRESSION', 'SYSTEM. WHEN ALARM SOUNDS', 'VACATE IMMEDIATELY.'], w / 2, 110, { size: 31, color: '#111', weight: 800, gap: 1.22 });
  });
  warn.position.set(ROOM.minX + 0.004, 2.15, 2.3);
  warn.rotation.y = Math.PI / 2;
  group.add(warn);

  // ------------------------------------------------------- entrance --
  const doorX = -5.6, wz = ROOM.maxZ;
  batch.box(M.doorGrey, 0.06, 2.16, 0.14, doorX - 0.53, 1.08, wz - 0.05);
  batch.box(M.doorGrey, 0.06, 2.16, 0.14, doorX + 0.53, 1.08, wz - 0.05);
  batch.box(M.doorGrey, 1.12, 0.06, 0.14, doorX, 2.13, wz - 0.05);
  batch.box(M.doorGrey, 1.0, 2.1, 0.045, doorX, 1.05, wz - 0.03);
  batch.box(M.glassDark, 0.13, 0.62, 0.005, doorX + 0.25, 1.52, wz - 0.054);
  batch.box(M.alu, 0.95, 0.22, 0.003, doorX, 0.12, wz - 0.054);
  batch.box(M.alu, 0.9, 0.04, 0.06, doorX, 1.0, wz - 0.1);
  batch.box(M.alu, 0.03, 0.04, 0.07, doorX - 0.4, 1.0, wz - 0.075);
  batch.box(M.alu, 0.03, 0.04, 0.07, doorX + 0.4, 1.0, wz - 0.075);
  batch.box(M.black, 0.32, 0.06, 0.06, doorX - 0.25, 2.04, wz - 0.08);
  batch.box(M.black, 0.32, 0.02, 0.025, doorX - 0.1, 2.02, wz - 0.12, 0.25);
  const doorSign = sign(0.32, 0.22, 600, (ctx, w, h) => {
    ctx.fillStyle = '#f2f1ec';
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = '#b3161b';
    ctx.fillRect(0, 0, w, 34);
    textLines(ctx, ['RESTRICTED AREA'], w / 2, 18, { size: 22, color: '#fff', weight: 800 });
    textLines(ctx, ['DATA HALL B', { t: 'AUTHORIZED', size: 22 }, { t: 'PERSONNEL ONLY', size: 22 }], w / 2, 66, { size: 30, color: '#111', weight: 800, gap: 1.15 });
  });
  doorSign.position.set(doorX - 0.18, 1.55, wz - 0.054);
  doorSign.rotation.y = Math.PI;
  group.add(doorSign);
  // illuminated exit sign
  batch.box(M.whitePaint, 0.36, 0.18, 0.05, doorX, 2.42, wz - 0.03);
  const exit = sign(0.32, 0.14, 600, (ctx, w, h) => {
    ctx.fillStyle = '#f6f6f2';
    ctx.fillRect(0, 0, w, h);
    textLines(ctx, ['EXIT'], w / 2, h / 2 + 3, { size: 70, color: '#d1121a', weight: 900 });
  }, { emissive: 2.2 });
  exit.position.set(doorX, 2.42, wz - 0.056);
  exit.rotation.y = Math.PI;
  group.add(exit);
  // emergency power off station
  batch.box(M.yellow, 0.18, 0.22, 0.03, -4.75, 1.38, wz - 0.015);
  batch.cyl(M.red, 0.032, 0.036, 0.04, -4.75, 1.4, wz - 0.05, { seg: 20, rx: Math.PI / 2 });
  const coverMat = new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.05, transparent: true, opacity: 0.18, depthWrite: false });
  const cover = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.16, 0.07), coverMat);
  cover.position.set(-4.75, 1.4, wz - 0.065);
  cover.userData.noAO = true;
  group.add(cover);
  const epoLbl = sign(0.2, 0.08, 800, (ctx, w, h) => {
    ctx.fillStyle = '#b3161b';
    ctx.fillRect(0, 0, w, h);
    textLines(ctx, ['EMERGENCY', 'POWER OFF'], w / 2, h * 0.3, { size: 22, color: '#fff', weight: 900, gap: 1.2 });
  });
  epoLbl.position.set(-4.75, 1.2, wz - 0.002);
  epoLbl.rotation.y = Math.PI;
  group.add(epoLbl);
  interactables.push({ kind: 'epo', box: new THREE.Box3(new THREE.Vector3(-4.85, 1.26, wz - 0.11), new THREE.Vector3(-4.65, 1.5, wz)) });
  // request-to-exit reader, pull station, extinguisher
  batch.box(M.black, 0.06, 0.1, 0.025, doorX - 0.75, 1.15, wz - 0.012);
  batch.box(M.red, 0.11, 0.15, 0.05, doorX - 0.85, 1.25, wz - 0.025);
  batch.box(M.black, 0.03, 0.03, 0.03, doorX - 0.85, 1.26, wz - 0.055);
  batch.cyl(M.red, 0.075, 0.075, 0.62, -6.95, 0.41, wz - 0.12, { seg: 20 });
  batch.cyl(M.black, 0.03, 0.04, 0.06, -6.95, 0.75, wz - 0.12, { seg: 12 });
  batch.cyl(M.black, 0.018, 0.035, 0.22, -6.88, 0.6, wz - 0.12, { seg: 12, rz: 0.4 });
  batch.box(M.black, 0.04, 0.05, 0.1, -6.95, 0.5, wz - 0.03);
  const extSign = sign(0.2, 0.2, 600, (ctx, w, h) => {
    ctx.fillStyle = '#c4161c';
    ctx.fillRect(0, 0, w, h);
    textLines(ctx, ['FIRE', 'EXTINGUISHER', { t: 'CO₂', size: 26 }], w / 2, h * 0.28, { size: 18, color: '#fff', weight: 800, gap: 1.6 });
  });
  extSign.position.set(-6.95, 1.35, wz - 0.004);
  extSign.rotation.y = Math.PI;
  group.add(extSign);
  const noFood = sign(0.3, 0.2, 600, (ctx, w, h) => {
    ctx.fillStyle = '#f4f3ee';
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = '#c4161c';
    ctx.lineWidth = 9;
    ctx.beginPath();
    ctx.arc(w / 2, 58, 40, 0, Math.PI * 2);
    ctx.moveTo(w / 2 - 28, 30);
    ctx.lineTo(w / 2 + 28, 86);
    ctx.stroke();
    textLines(ctx, ['NO FOOD OR DRINK'], w / 2, 132, { size: 22, color: '#111', weight: 800 });
  });
  noFood.position.set(-4.0, 1.55, wz - 0.004);
  noFood.rotation.y = Math.PI;
  group.add(noFood);

  // NOC status display on the front wall
  const noc = buildNocDisplay();
  noc.position.set(0.6, 1.75, wz - 0.03);
  noc.rotation.y = Math.PI;
  group.add(noc);

  // ---------------------------------------- power distribution ------
  for (const [x, name] of [[-5.5, 'PDU-1A'], [5.5, 'PDU-1B']]) {
    const face = pbr(cabinetFace(name), { emissiveIntensity: 1.3 });
    const mats = [M.offWhite, M.offWhite, M.offWhite, M.offWhite, face, M.offWhite];
    const cab = new THREE.Mesh(new THREE.BoxGeometry(1.0, 2.0, 0.8), mats);
    cab.position.set(x, 1.0, ROOM.minZ + 0.4);
    group.add(cab);
    colliders.push({ minX: x - 0.52, maxX: x + 0.52, minZ: ROOM.minZ, maxZ: ROOM.minZ + 0.82 });
    occluders.push(new THREE.Box3(new THREE.Vector3(x - 0.5, 0, ROOM.minZ), new THREE.Vector3(x + 0.5, 2.0, ROOM.minZ + 0.8)));
    for (let k = 0; k < 3; k++) batch.cyl(M.galv, 0.02, 0.02, H - 2.0, x - 0.25 + k * 0.25, (H + 2.0) / 2, ROOM.minZ + 0.3, { seg: 10 });
  }
  // wall panelboard with conduits
  batch.box(M.offWhite, 0.6, 1.1, 0.14, 0, 1.55, ROOM.minZ + 0.07);
  batch.box(M.darkGrey, 0.5, 0.95, 0.002, 0, 1.55, ROOM.minZ + 0.141);
  for (let k = 0; k < 4; k++) batch.cyl(M.galv, 0.014, 0.014, H - 2.1, -0.18 + k * 0.12, (H + 2.1) / 2, ROOM.minZ + 0.06, { seg: 10 });
  const panelLbl = sign(0.2, 0.05, 800, (ctx, w, h) => {
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, w, h);
    textLines(ctx, ['RPP-B2  480/277V'], w / 2, h / 2, { size: 22, color: '#fff', weight: 800 });
  });
  panelLbl.position.set(0, 2.0, ROOM.minZ + 0.143);
  group.add(panelLbl);

  // ------------------------------------------------------ crash cart --
  const cart = new THREE.Group();
  const cb = new StaticBatch();
  for (const [dx, dz] of [[-0.28, -0.2], [0.28, -0.2], [-0.28, 0.2], [0.28, 0.2]]) {
    cb.cyl(M.alu, 0.012, 0.012, 0.9, dx, 0.52, dz, { seg: 8 });
    cb.cyl(M.black, 0.035, 0.035, 0.03, dx, 0.04, dz, { seg: 14, rz: Math.PI / 2 });
  }
  cb.box(M.darkGrey, 0.62, 0.02, 0.46, 0, 0.25, 0);
  cb.box(M.darkGrey, 0.62, 0.02, 0.46, 0, 0.88, 0);
  cb.box(M.black, 0.42, 0.015, 0.15, 0, 0.9, 0.1);
  for (let k = 0; k < 4; k++) cb.box(M.rubber, 0.36, 0.006, 0.012, 0, 0.91, 0.05 + k * 0.03);
  cb.box(M.black, 0.06, 0.02, 0.1, 0.25, 0.9, 0.1);
  cb.box(M.black, 0.04, 0.22, 0.04, 0, 1.0, -0.15);
  cb.box(M.black, 0.42, 0.29, 0.03, 0, 1.24, -0.15);
  cb.cyl(M.black, 0.08, 0.08, 0.04, 0.05, 0.28, 0.05, { seg: 20 });
  cb.build(cart);
  const term = sign(0.39, 0.25, 900, (ctx, w, h) => {
    ctx.fillStyle = '#060a08';
    ctx.fillRect(0, 0, w, h);
    const lines = ['kestrel-r1 login: root', 'Last login: Tue Oct 27 03:12 on tty1', '[root@app-31 ~]# ipmitool sel list | tail -3', ' 41 | PSU 2 | Power Supply AC lost | Asserted', ' 42 | PSU 2 | Redundancy Lost | Asserted', ' 43 | Fan 4 | Lower Critical | Deasserted', '[root@app-31 ~]# _'];
    ctx.font = '600 19px monospace';
    ctx.fillStyle = '#9ef0b0';
    lines.forEach((l, i) => ctx.fillText(l, 14, 28 + i * 28));
  }, { emissive: 1.8 });
  term.position.set(0, 1.24, -0.134);
  cart.add(term);
  cart.position.set(5.3, 0, -2.75);
  cart.rotation.y = -0.35;
  group.add(cart);
  colliders.push({ minX: 4.95, maxX: 5.65, minZ: -3.1, maxZ: -2.4 });

  // humidity / temperature sensor next to the NOC screen
  batch.box(M.whitePaint, 0.09, 0.12, 0.03, 1.75, 1.5, wz - 0.015);
  const sensor = sign(0.06, 0.035, 1200, (ctx, w, h) => {
    ctx.fillStyle = '#0f1914';
    ctx.fillRect(0, 0, w, h);
    textLines(ctx, ['22.4°C 45%'], w / 2, h / 2 + 2, { size: 13, color: '#9ef0b0', font: 'monospace' });
  }, { emissive: 1.4 });
  sensor.position.set(1.75, 1.52, wz - 0.031);
  sensor.rotation.y = Math.PI;
  group.add(sensor);

  batch.build(group);
  const cableMesh = cables.build(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.55, metalness: 0 }));
  group.add(cableMesh);

  // rack rows as occluders for the floor bake
  for (const row of ROWS) {
    occluders.push(new THREE.Box3(new THREE.Vector3(-ROW_HALF, 0, row.z - RACK.d / 2), new THREE.Vector3(ROW_HALF, RACK.h, row.z + RACK.d / 2)));
    // overhead services shade a little too
    occluders.push(new THREE.Box3(new THREE.Vector3(-ROW_HALF, 2.42, row.z + row.facing * TRAY_Z - 0.23), new THREE.Vector3(ROW_HALF, 2.51, row.z + row.facing * TRAY_Z + 0.23)));
  }

  function update(dt, player) {
    for (const u of updaters) u(dt, player);
  }

  return {
    group, colliders, occluders, interactables, areaLights, hemi, lightMat, update,
    floorMats: [floorMat, perfMat],
    spawn: { x: -6.25, z: 6.55, yaw: -0.78 },
  };
}

// ------------------------------------------------------------- helpers --
function cabinetFace(name) {
  const p = new Painter(512, 1024, { base: '#d4d2cb', r: 0.5, m: 0.1, emissive: true });
  p.grain(0, 0, 512, 1024, 0.015, { seed: 5 });
  p.strokeRect(0, 0, 512, 1024, 4, { c: '#9c9a94', h: 0.25 });
  p.line(256, 0, 256, 1024, 3, { c: '#9c9a94', h: 0.25 });
  for (let y = 60; y < 300; y += 14) { p.rect(30, y, 196, 6, { c: '#8f8d87', h: 0.3 }); p.rect(286, y, 196, 6, { c: '#8f8d87', h: 0.3 }); }
  p.rect(296, 360, 180, 140, { c: '#2c2d30', h: 0.65, r: 0.4, m: 0 });
  p.rect(306, 370, 160, 100, { c: '#08121c', e: '#0a1622', h: 0.66, r: 0.1, m: 0 });
  const ink = { c: '#9fd7ff', e: '#86ccff' };
  p.text(name, 314, 386, 15, ink, { font: 'monospace' });
  for (let k = 0; k < 3; k++) {
    p.text(`L${k + 1}`, 314, 412 + k * 20, 13, ink, { font: 'monospace' });
    p.rect(340, 406 + k * 20, 110, 10, { c: '#14324a', e: '#0c2030' });
    p.rect(340, 406 + k * 20, [62, 71, 55][k], 10, { c: '#4fd18b', e: '#3ccf7c' });
  }
  for (const y of [560, 900]) for (const x of [226, 482]) p.circle(x, y, 10, { c: '#2a2b2d', h: 0.7 });
  p.rect(60, 600, 140, 40, { c: '#f0efe9', h: 0.52 });
  p.text(name, 130, 620, 22, { c: '#111' }, { align: 'center' });
  p.text('480V 3Ø  225 kVA', 130, 660, 13, { c: '#5b5a56' }, { align: 'center' });
  return p.textures({ normalStrength: 2.5, blur: 1 });
}

function buildNocDisplay() {
  const g = new THREE.Group();
  const bezel = new THREE.Mesh(new THREE.BoxGeometry(1.64, 0.94, 0.05), std(0x070708, 0.35, 0.2));
  g.add(bezel);
  const c = document.createElement('canvas');
  c.width = 1600; c.height = 900;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#081019';
  ctx.fillRect(0, 0, 1600, 900);
  ctx.fillStyle = '#d9e6f2';
  ctx.font = `700 42px ${FONT}`;
  ctx.fillText('DATA HALL B · ENVIRONMENT', 50, 70);
  ctx.font = `500 26px ${FONT}`;
  ctx.fillStyle = '#7f95aa';
  ctx.fillText('Rack inlet temperature (°C) · ASHRAE A1 recommended 18–27', 50, 112);
  const rng = new Rng(5);
  const rows = ['A', 'B', 'C', 'D'];
  rows.forEach((r, ri) => {
    ctx.fillStyle = '#9fb3c7';
    ctx.font = `700 30px ${FONT}`;
    ctx.fillText(r, 50, 190 + ri * 92);
    for (let i = 0; i < PER_ROW; i++) {
      let t = rng.range(21, 24.8);
      if (r === 'B' && i === 9) t = 26.1;
      if (r === 'B' && (i >= 2 && i <= 5)) t += 1.2;
      const k = (t - 20) / 8;
      ctx.fillStyle = `hsl(${200 - k * 170}, 70%, ${38 + k * 10}%)`;
      ctx.fillRect(90 + i * 66, 150 + ri * 92, 60, 74);
      ctx.fillStyle = '#071018';
      ctx.font = `600 20px ${FONT}`;
      ctx.fillText(t.toFixed(1), 96 + i * 66, 193 + ri * 92);
    }
  });
  const kpi = [['IT LOAD', '412 kW'], ['PUE', '1.38'], ['SUPPLY AIR', '17.8 °C'], ['RH', '45 %']];
  kpi.forEach(([k, v], i) => {
    ctx.fillStyle = '#7f95aa';
    ctx.font = `600 24px ${FONT}`;
    ctx.fillText(k, 1060, 180 + i * 92);
    ctx.fillStyle = '#e8f1fa';
    ctx.font = `700 48px ${FONT}`;
    ctx.fillText(v, 1300, 190 + i * 92);
  });
  ctx.fillStyle = '#2a1408';
  ctx.fillRect(50, 560, 1500, 150);
  ctx.fillStyle = '#ffb347';
  ctx.font = `700 30px ${FONT}`;
  ctx.fillText('● MAJOR  B10 · db-prod-07 · PSU 2 input lost · redundancy lost', 80, 610);
  ctx.fillStyle = '#e0a060';
  ctx.font = `500 26px ${FONT}`;
  ctx.fillText('Opened 03:12 · INC-48213 · assigned: on-site tech', 80, 660);
  ctx.fillStyle = '#5c7287';
  ctx.font = `500 24px ${FONT}`;
  ctx.fillText('CRAC-01 RUN · CRAC-02 RUN · CRAC-03 STANDBY        UPS-A 43%  UPS-B 41%        FM-200 NORMAL', 50, 790);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  const screen = new THREE.Mesh(
    new THREE.PlaneGeometry(1.58, 0.89),
    new THREE.MeshStandardMaterial({ map: tex, emissiveMap: tex, emissive: 0xffffff, emissiveIntensity: 1.1, roughness: 0.25, metalness: 0 }),
  );
  screen.position.z = 0.026;
  g.add(screen);
  return g;
}
