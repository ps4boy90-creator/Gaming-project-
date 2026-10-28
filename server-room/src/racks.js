// Rack rows: layout, what's installed in every rack, and all the instanced
// geometry that draws it (frames, doors, devices, PDUs, LEDs, cabling).
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { Rng, U, clamp, lerp, damp } from './util.js';
import { atlasMaterial, faceBoxGeometry, setRects } from './materials.js';
import { CableBatch, CABLE } from './cables.js';
import { LedBatch, LED_MODE } from './leds.js';
import { powderCoat, rackPost, doorPerforation, pduFace, labelAtlas } from './textures.js';
import { pbr } from './painter.js';

// 600 × 1200 mm, 42U. Rack-local +z is the front.
export const RACK = {
  w: 0.6,
  d: 1.2,
  h: 2.0,
  base: 0.06,
  frameZ: 0.575, // corner uprights / cross members
  devFront: 0.525, // faceplate plane
  devW: 0.4826,
  doorZ: 0.588,
  hingeX: -0.299,
  rearPost: -0.46,
  pduX: 0.262, // 0U PDUs in the rear corners, outlets facing the rack centre
  pduZ: -0.535,
  bundleX: 0.185,
  bundleZ: -0.515,
};

// Cold aisles between A/B and C/D (fronts face each other), hot aisle B/C.
export const ROWS = [
  { id: 'A', z: -4.2, facing: 1 },
  { id: 'B', z: -1.2, facing: -1 },
  { id: 'C', z: 1.2, facing: 1 },
  { id: 'D', z: 4.2, facing: -1 },
];
// Overhead services above each row, as rack-local z offsets.
export const BUSWAY_Z = -0.5;
export const TRAY_Z = -0.12;
export const RUNWAY_Z = 0.32;
export const PER_ROW = 14;
export const ROW_X0 = -3.9;
export const ROW_HALF = (PER_ROW * RACK.w) / 2;

// c compute · s storage · g GPU · N network/MDA · e empty (awaiting install)
const PLAN = {
  A: 'cccccsNsccccec',
  B: 'ccggggNcccccss',
  C: 'cccsssNccggcce',
  D: 'ccccccNcssccgc',
};

const DEV = {
  srv1u_a: { front: 'srv1u_a', rear: 'rear1u', u: 1, d: 0.75, model: 'Kestrel R1 Gen4', kind: 'server', w: [190, 430] },
  srv1u_b: { front: 'srv1u_b', rear: 'rear1u', u: 1, d: 0.7, model: 'Nordstak N140', kind: 'server', w: [160, 380] },
  srv1u_c: { front: 'srv1u_c', rear: 'rear1u', u: 1, d: 0.72, model: 'Halcyon X1', kind: 'server', w: [170, 400] },
  srv2u_a: { front: 'srv2u_a', rear: 'rear2u', u: 2, d: 0.74, model: 'Kestrel R2 LFF', kind: 'server', w: [260, 610] },
  srv2u_b: { front: 'srv2u_b', rear: 'rear2u', u: 2, d: 0.74, model: 'Kestrel R2 SFF', kind: 'server', w: [280, 640] },
  srv2u_c: { front: 'srv2u_c', rear: 'rear2u', u: 2, d: 0.76, model: 'Halcyon X2', kind: 'server', w: [300, 700] },
  storage4u: { front: 'storage4u', rear: 'rear4u', u: 4, d: 0.82, model: 'ArrayCore 9400', kind: 'storage', w: [520, 880] },
  gpu4u: { front: 'gpu4u', rear: 'reargpu', u: 4, d: 0.86, model: 'Titan G8 (8× accelerator)', kind: 'gpu', w: [3800, 6200] },
  switch48: { front: 'switch48', rear: 'rearsw', u: 1, d: 0.45, model: 'NX-4848 48×10G leaf', kind: 'switch', w: [140, 260] },
  spine32: { front: 'spine32', rear: 'rearsw', u: 1, d: 0.55, model: 'SPX-32Q 32×100G spine', kind: 'switch', w: [320, 520] },
  patch48: { front: 'patch48', rear: 'rearpatch', u: 1, d: 0.12, model: 'Cat6A 48-port patch panel', kind: 'patch' },
  blank: { front: 'blank', rear: 'rearblank', u: 1, d: 0.012, kind: 'blank' },
  cablemgr: { front: 'cablemgr', rear: 'rearblank', u: 1, d: 0.09, model: 'Horizontal cable manager', kind: 'cable' },
  ups2u: { front: 'ups2u', rear: 'rearups', u: 2, d: 0.65, model: 'Voltara 3000 RM UPS', kind: 'ups', w: [60, 90] },
  kvm1u: { front: 'kvm1u', rear: 'rearkvm', u: 1, d: 0.6, model: '17" KVM console drawer', kind: 'kvm', w: [20, 35] },
};

const PALETTES = [
  [CABLE.blue, CABLE.blue, CABLE.blue, CABLE.yellow],
  [CABLE.blue, CABLE.blue, CABLE.grey, CABLE.red],
  [CABLE.yellow, CABLE.blue, CABLE.blue, CABLE.green],
  [CABLE.blue, CABLE.purple, CABLE.blue, CABLE.white],
  [CABLE.grey, CABLE.blue, CABLE.blue, CABLE.orange],
];

const ROLES = ['k8s', 'app', 'web', 'db', 'cache', 'vmh', 'batch', 'api'];

// ------------------------------------------------------------ population --
function populate(profile, rng) {
  const used = new Array(43).fill(false);
  const list = [];
  const place = (type, u) => {
    const h = DEV[type].u;
    if (u < 1 || u + h - 1 > 42) return false;
    for (let k = u; k < u + h; k++) if (used[k]) return false;
    for (let k = u; k < u + h; k++) used[k] = true;
    list.push({ type, u });
    return true;
  };
  if (profile === 'e') return list;
  if (profile === 'N') {
    place('spine32', 42);
    place('spine32', 41);
    place('cablemgr', 40);
    let u = 39;
    for (let i = 0; i < 3; i++) {
      place('patch48', u--);
      place('patch48', u--);
      place('cablemgr', u--);
    }
    for (let i = 0; i < 3; i++) {
      place('switch48', u--);
      place('cablemgr', u--);
    }
    place('kvm1u', 19);
    place('ups2u', 2);
    place('ups2u', 4);
  } else {
    place('switch48', 42);
    place('cablemgr', 41);
    if (rng.chance(0.6)) place('switch48', 40);
    let u = 2;
    if (rng.chance(0.3)) { place('ups2u', 2); u = 4; }
    const top = profile === 'g' ? rng.int(24, 30) : rng.int(24, 38);
    if (profile === 'c') {
      const one = ['srv1u_a', 'srv1u_b', 'srv1u_c'], two = ['srv2u_a', 'srv2u_b', 'srv2u_c'];
      const models = [rng.chance(0.5) ? rng.pick(one) : rng.pick(two)];
      if (rng.chance(0.45)) models.push(rng.pick([...one, ...two]));
      while (u <= top) {
        const t = models[models.length > 1 && u > top * 0.55 ? 1 : 0];
        u += place(t, u) ? DEV[t].u : 1;
        if (rng.chance(0.05)) u++;
      }
    } else if (profile === 's') {
      const n = rng.int(3, 5);
      for (let i = 0; i < n; i++) { place('storage4u', u); u += 4; }
      u++;
      while (u <= top) u += place('srv2u_a', u) ? 2 : 1;
    } else if (profile === 'g') {
      while (u + 3 <= top) { place('gpu4u', u); u += 5; }
    }
  }
  for (let k = 1; k <= 42; k++) if (!used[k]) list.push({ type: 'blank', u: k });
  return list;
}

// ------------------------------------------------------------- geometry --
function boxAt(w, h, d, x, y, z) {
  return new THREE.BoxGeometry(w, h, d).translate(x, y, z);
}

function rackBodyGeometry() {
  const { w, d, h, base } = RACK;
  const parts = [
    boxAt(0.014, h - base, d, -w / 2 + 0.007, base + (h - base) / 2, 0),
    boxAt(0.014, h - base, d, w / 2 - 0.007, base + (h - base) / 2, 0),
    boxAt(w, 0.02, d, 0, h - 0.01, 0),
    boxAt(w - 0.03, base, d - 0.06, 0, base / 2, 0),
    // front and rear frame cross members above U42 and below U1
    boxAt(w - 0.028, 0.035, 0.03, 0, h - 0.038, RACK.frameZ),
    boxAt(w - 0.028, 0.035, 0.03, 0, h - 0.038, -RACK.frameZ),
    boxAt(w - 0.028, 0.02, 0.03, 0, base + 0.005, RACK.frameZ),
    boxAt(w - 0.028, 0.02, 0.03, 0, base + 0.005, -RACK.frameZ),
    // vertical frame uprights at the four corners
    boxAt(0.03, h - base, 0.03, -w / 2 + 0.029, base + (h - base) / 2, RACK.frameZ),
    boxAt(0.03, h - base, 0.03, w / 2 - 0.029, base + (h - base) / 2, RACK.frameZ),
    boxAt(0.03, h - base, 0.03, -w / 2 + 0.029, base + (h - base) / 2, -RACK.frameZ),
    boxAt(0.03, h - base, 0.03, w / 2 - 0.029, base + (h - base) / 2, -RACK.frameZ),
    // levelling feet
    ...[[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([sx, sz]) =>
      new THREE.CylinderGeometry(0.018, 0.022, 0.03, 10).translate(sx * 0.25, 0.015, sz * 0.53)),
  ];
  // cylinders carry different attributes; strip to the shared set
  for (const g of parts) for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(k)) g.deleteAttribute(k);
  return mergeGeometries(parts.map((g) => g.index ? g.toNonIndexed() : g));
}

function postGeometry() {
  const H = 42 * U;
  const y = RACK.base + H / 2;
  const x = RACK.devW / 2 + 0.0175;
  return mergeGeometries([
    boxAt(0.035, H, 0.018, -x, y, RACK.devFront - 0.012),
    boxAt(0.035, H, 0.018, x, y, RACK.devFront - 0.012),
    boxAt(0.035, H, 0.018, -x, y, RACK.rearPost),
    boxAt(0.035, H, 0.018, x, y, RACK.rearPost),
  ]);
}

// Door parts in hinge space (hinge at x=0; door spans +x).
function doorFrameGeometry() {
  return mergeGeometries([
    boxAt(0.592, 0.13, 0.018, 0.299, 1.92, 0),
    boxAt(0.592, 0.07, 0.018, 0.299, 0.07, 0),
    boxAt(0.032, 1.75, 0.018, 0.019, 0.98, 0),
    boxAt(0.05, 1.75, 0.018, 0.57, 0.98, 0),
    boxAt(0.032, 0.21, 0.008, 0.57, 1.12, 0.012),
    boxAt(0.018, 0.15, 0.02, 0.57, 1.12, 0.024),
    boxAt(0.006, 0.06, 0.012, 0.004, 1.7, 0.004),
    boxAt(0.006, 0.06, 0.012, 0.004, 0.3, 0.004),
  ]);
}

// --------------------------------------------------------------- builder --
const _m = new THREE.Matrix4(), _m2 = new THREE.Matrix4(), _v = new THREE.Vector3(), _q = new THREE.Quaternion();
const Y = new THREE.Vector3(0, 1, 0);

export function buildRacks(atlas, { quality = 'high' } = {}) {
  const rng = new Rng(1337);
  const group = new THREE.Group();
  group.name = 'racks';
  const racks = [];
  const devices = [];
  const roleCount = {};

  for (const row of ROWS) {
    for (let i = 0; i < PER_ROW; i++) {
      const id = row.id + String(i + 1).padStart(2, '0');
      const x = ROW_X0 + i * RACK.w;
      const rot = row.facing > 0 ? 0 : Math.PI;
      const matrix = new THREE.Matrix4().compose(new THREE.Vector3(x, 0, row.z), new THREE.Quaternion().setFromAxisAngle(Y, rot), new THREE.Vector3(1, 1, 1));
      const profile = PLAN[row.id][i];
      const rack = {
        id, row: row.id, index: i, x, z: row.z, facing: row.facing, matrix, profile,
        devices: [], door: 0, doorTarget: 0,
        palette: rng.pick(PALETTES),
        role: profile === 's' ? 'ceph' : profile === 'g' ? 'gpu' : rng.pick(ROLES),
        inlet: rng.range(21.5, 24.5),
      };
      racks.push(rack);
      for (const slot of populate(profile, rng)) {
        const def = DEV[slot.type];
        const dev = { ...slot, def, rack, status: 'ok', connected: { front: [], rear: [] } };
        if (def.kind === 'server' || def.kind === 'gpu' || def.kind === 'storage') {
          const role = def.kind === 'storage' ? 'ceph-osd' : def.kind === 'gpu' ? 'gpu' : rack.role;
          roleCount[role] = (roleCount[role] ?? 0) + 1;
          dev.hostname = `${role}-${String(roleCount[role]).padStart(2, '0')}`;
        } else if (def.kind === 'switch') {
          dev.hostname = slot.type === 'spine32' ? `spine-${row.id.toLowerCase()}${slot.u === 42 ? 1 : 2}` : `leaf-${id.toLowerCase()}${slot.u === 42 ? '' : '-' + slot.u}`;
        } else if (def.kind === 'patch') dev.hostname = `PP-${id}-U${slot.u}`;
        else if (def.kind === 'ups') dev.hostname = `ups-${id.toLowerCase()}`;
        else if (def.kind === 'kvm') dev.hostname = `kvm-${id.toLowerCase()}`;
        if (def.w) dev.watts = Math.round(rng.range(def.w[0], def.w[1]));
        dev.temp = rack.inlet + rng.range(-0.6, 0.9);
        rack.devices.push(dev);
        devices.push(dev);
      }
    }
  }

  // A few warm-running machines, and one real fault for the ticket objective.
  for (const d of devices) if (d.hostname && d.def.kind === 'server' && rng.chance(0.015)) { d.status = 'warn'; d.temp += 6.5; }
  const faultRack = racks.find((r) => r.id === 'B10');
  const fault = faultRack.devices.filter((d) => d.def.kind === 'server' && d.u >= 14 && d.u <= 24)[0];
  fault.status = 'fault';
  fault.note = 'PSU 2 input lost';
  fault.hostname = 'db-prod-07';

  // Technician left one door open.
  const openRack = racks.find((r) => r.id === 'C05');
  openRack.door = openRack.doorTarget = 1.75;

  // ---- static rack frames ----
  const nR = racks.length;
  const coat = powderCoat('#303236', 51);
  const frameMat = pbr(coat, { name: 'rack-frame' });
  const body = new THREE.InstancedMesh(rackBodyGeometry(), frameMat, nR);
  const postTex = rackPost();
  const posts = new THREE.InstancedMesh(postGeometry(), pbr(postTex), nR);
  racks.forEach((r, i) => { body.setMatrixAt(i, r.matrix); posts.setMatrixAt(i, r.matrix); });
  group.add(body, posts);

  // ---- PDUs (A feed left, B feed right as seen from the front) ----
  const pduGeo = new THREE.BoxGeometry(0.056, 1.72, 0.045);
  const pduBlack = new THREE.MeshStandardMaterial({ color: 0x2c2d30, roughness: 0.5, metalness: 0.05 });
  for (const [feed, sx] of [['A', -1], ['B', 1]]) {
    const face = pbr(pduFace(feed), { emissiveIntensity: 1.6 });
    const mesh = new THREE.InstancedMesh(pduGeo, [pduBlack, pduBlack, pduBlack, pduBlack, pduBlack, face], nR);
    racks.forEach((r, i) => {
      // turn the textured -z face toward the middle of the rack
      _m.makeRotationY(sx < 0 ? -Math.PI / 2 : Math.PI / 2).setPosition(sx * RACK.pduX, RACK.base + 0.92, RACK.pduZ);
      mesh.setMatrixAt(i, _m2.multiplyMatrices(r.matrix, _m));
    });
    group.add(mesh);
  }

  // ---- labels (door top band and rear cross member) ----
  const labels = labelAtlas(racks.map((r) => r.id));
  const labelMat = atlasMaterial(labels.texture, { roughness: 0.6, metalness: 0 });
  const labelGeo = new THREE.PlaneGeometry(0.105, 0.04);
  const rearLabels = new THREE.InstancedMesh(labelGeo.clone(), labelMat, nR);
  const rearRects = setRects(rearLabels.geometry, nR)[0];
  racks.forEach((r, i) => {
    _m.makeRotationY(Math.PI).setPosition(0, RACK.h - 0.038, -RACK.frameZ - 0.0155);
    rearLabels.setMatrixAt(i, _m2.multiplyMatrices(r.matrix, _m));
    rearRects.setXYZW(i, ...labels.rects[r.id]);
  });
  group.add(rearLabels);

  // ---- doors (instanced so they can swing individually) ----
  const perf = doorPerforation();
  perf.repeat.set(16, 63);
  const doorFrame = new THREE.InstancedMesh(doorFrameGeometry(), frameMat, nR);
  const panelGeo = new THREE.PlaneGeometry(0.51, 1.75).translate(0.29, 0.98, 0);
  const panelMat = new THREE.MeshStandardMaterial({
    color: 0x303236, roughness: 0.42, metalness: 0.1, alphaMap: perf, transparent: true,
    side: THREE.DoubleSide, depthWrite: false,
  });
  const doorPanel = new THREE.InstancedMesh(panelGeo, panelMat, nR);
  doorPanel.renderOrder = 2;
  doorPanel.userData.noAO = true;
  const doorLabel = new THREE.InstancedMesh(labelGeo.clone().translate(0.3, 1.93, 0.0105), labelMat, nR);
  const doorRects = setRects(doorLabel.geometry, nR)[0];
  racks.forEach((r, i) => doorRects.setXYZW(i, ...labels.rects[r.id]));
  for (const m of [doorFrame, doorPanel, doorLabel]) m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  group.add(doorFrame, doorPanel, doorLabel);

  const setDoor = (r, i) => {
    _m.makeRotationY(-r.door).setPosition(RACK.hingeX, 0, RACK.doorZ);
    _m2.multiplyMatrices(r.matrix, _m);
    doorFrame.setMatrixAt(i, _m2);
    doorPanel.setMatrixAt(i, _m2);
    doorLabel.setMatrixAt(i, _m2);
  };
  racks.forEach(setDoor);

  // ---- devices ----
  const devGeo = faceBoxGeometry();
  const devMat = atlasMaterial(atlas.tex, { name: 'devices', emissiveIntensity: 2.2 });
  const devMesh = new THREE.InstancedMesh(devGeo, devMat, devices.length);
  const [rFront, rRear, rSide] = setRects(devGeo, devices.length);
  const side = atlas.regions.side.uv;
  const leds = new LedBatch();
  const cables = new CableBatch();
  const boots = [];

  const toWorld = (rack, x, y, z) => new THREE.Vector3(x, y, z).applyMatrix4(rack.matrix);
  const front = RACK.devFront;

  devices.forEach((dev, i) => {
    const { def, rack } = dev;
    const hU = def.u * U - 0.0008;
    const yc = RACK.base + (dev.u - 1) * U + hU / 2 + 0.0004;
    const zc = front - def.d / 2;
    _m.compose(_v.set(0, yc, zc), _q.identity(), new THREE.Vector3(RACK.devW, hU, def.d));
    devMesh.setMatrixAt(i, _m2.multiplyMatrices(rack.matrix, _m));
    const fr = atlas.regions[def.front], rr = atlas.regions[def.rear];
    rFront.setXYZW(i, ...fr.uv);
    rRear.setXYZW(i, ...rr.uv);
    rSide.setXYZW(i, ...side);
    dev.yc = yc; dev.hU = hU;

    // world AABB for picking
    const c = toWorld(rack, 0, yc, zc);
    dev.box = new THREE.Box3(
      new THREE.Vector3(c.x - RACK.devW / 2, yc - hU / 2, c.z - def.d / 2),
      new THREE.Vector3(c.x + RACK.devW / 2, yc + hU / 2, c.z + def.d / 2),
    );

    // which ports carry a cable
    dev.connected.front = connectFront(dev, fr, rng);
    dev.connected.rear = connectRear(dev, rr, rng);

    const local = (reg, a, rear) => ({
      x: (rear ? -1 : 1) * (a.u - 0.5) * RACK.devW,
      y: yc + (0.5 - a.v) * hU,
    });

    // LEDs
    for (const [reg, rear] of [[fr, false], [rr, true]]) {
      const conn = rear ? dev.connected.rear : dev.connected.front;
      let pwrSeen = 0;
      const healthIdx = Math.min(2, reg.leds.filter((l) => l.kind === 'pwr').length);
      for (const led of reg.leds) {
        const p = local(reg, led, rear);
        const z = rear ? front - def.d - 0.0015 : front + 0.0015;
        const pos = toWorld(rack, p.x, p.y, z);
        const hasCable = led.port >= 0 ? conn[led.port] : true;
        switch (led.kind) {
          case 'pwr': {
            pwrSeen++;
            if (dev.status === 'fault' && !rear && pwrSeen === healthIdx) leds.add(pos, 'amber', LED_MODE.blink, 1.1, 1.6);
            else if (dev.status === 'warn' && !rear && pwrSeen === healthIdx) leds.add(pos, 'amber', LED_MODE.steady, 1, 1.1);
            else leds.add(pos, led.color, LED_MODE.steady, 1, 0.8);
            break;
          }
          case 'psu':
            if (hasCable) leds.add(pos, 'green', LED_MODE.steady, 1, 0.8);
            else leds.add(pos, 'amber', LED_MODE.blink, 0.9, 1.4);
            break;
          case 'disk':
            leds.add(pos, def.kind === 'storage' ? 'blue' : led.color, LED_MODE.flicker, rng.range(7, 22), 0.9);
            break;
          case 'link':
            if (hasCable) leds.add(pos, led.color, LED_MODE.steady, 1, 0.7);
            break;
          case 'act':
            if (hasCable) leds.add(pos, rng.chance(0.7) ? 'green' : 'amber', LED_MODE.flicker, rng.range(9, 30), 0.8);
            break;
          case 'heartbeat':
            leds.add(pos, led.color, LED_MODE.beat, rng.range(0.8, 1.2), 1);
            break;
          case 'fault':
            leds.add(pos, 'amber', LED_MODE.steady, 1, 1);
            break;
          case 'id':
            if (rng.chance(0.04)) leds.add(pos, 'blue', LED_MODE.steady, 1, 1);
            break;
          default:
            break;
        }
      }
    }

    // front patching (switches and patch panels)
    if (def.kind === 'switch' || def.kind === 'patch') {
      const mgr = nearestManager(rack, dev);
      fr.anchors.forEach((a, k) => {
        if (!dev.connected.front[k]) return;
        const p = local(fr, a, false);
        const sideX = p.x < 0 ? -1 : 1;
        const color = a.type === 'qsfp' || a.type === 'sfp' ? (rng.chance(0.7) ? CABLE.aqua : CABLE.black) : rng.pick(rack.palette);
        const r = a.type === 'qsfp' ? 0.0032 : a.type === 'sfp' ? 0.0018 : 0.0028;
        const z0 = front + 0.004;
        const pts = [[p.x, p.y, z0], [p.x, p.y - 0.004, z0 + 0.035]];
        if (mgr) {
          const below = mgr.yc < p.y;
          const yM = mgr.yc + (below ? 0.01 : -0.01) + rng.range(-0.008, 0.008);
          pts.push(
            [p.x * 0.97, yM + (below ? 0.012 : -0.012), z0 + 0.042 + rng.range(0, 0.01)],
            [sideX * (0.19 + rng.range(0, 0.03)), yM, z0 + 0.032 + rng.range(-0.004, 0.006)],
            [sideX * 0.262, yM - 0.04, z0 + 0.012],
            [sideX * 0.272, yM - 0.22 - rng.range(0, 0.2), z0 + 0.01],
            [sideX * 0.25, yM - 0.4 - rng.range(0, 0.2), front - 0.05],
          );
        } else {
          pts.push([p.x, p.y - 0.05, z0 + 0.05], [sideX * 0.22, p.y - 0.09, z0 + 0.035], [sideX * 0.27, p.y - 0.25, z0 + 0.0], [sideX * 0.25, p.y - 0.4, front - 0.05]);
        }
        cables.add(pts.map(([x, y, z]) => toWorld(rack, x, y, z)), r, color, { segLen: 0.08, radial: r < 0.003 ? 3 : 4 });
        boots.push({ pos: toWorld(rack, p.x, p.y, front + 0.012), rack, color, sfp: a.type !== 'eth' });
      });
    }

    // rear cabling
    rr.anchors.forEach((a, k) => {
      if (!dev.connected.rear[k]) return;
      if (quality === 'low' && a.type !== 'psu') return;
      const p = local(rr, a, true);
      const zR = front - def.d;
      const s = p.x < 0 ? -1 : 1;
      if (a.type === 'psu') {
        const ty = clamp(p.y + rng.range(-0.08, 0.06), 0.18, 1.72);
        const color = s < 0 ? CABLE.powerA : CABLE.powerB;
        const sag = rng.range(0.02, 0.08);
        const faceX = s * (RACK.pduX - 0.0225 - 0.004);
        const pz = RACK.pduZ + rng.range(-0.012, 0.012);
        const pts = [
          [p.x, p.y, zR - 0.01], [p.x, p.y - 0.003, zR - 0.06],
          [lerp(p.x, s * 0.17, 0.6), Math.min(p.y, ty) - sag, lerp(zR - 0.06, pz, 0.55)],
          [s * 0.2, ty - 0.01, pz + 0.01], [faceX, ty, pz],
        ];
        cables.add(pts.map(([x, y, z]) => toWorld(rack, x, y, z)), 0.0036, color, { segLen: 0.09, radial: 4 });
      } else {
        const fiber = a.type === 'sfp' || a.type === 'qsfp';
        const color = a.type === 'sas' ? CABLE.black : fiber ? (rng.chance(0.55) ? CABLE.aqua : CABLE.black) : (k === firstEth(rr) ? CABLE.yellow : rng.pick(rack.palette));
        const r = a.type === 'sas' || a.type === 'qsfp' ? 0.0034 : fiber ? 0.002 : 0.0027;
        const bx = s * RACK.bundleX;
        const pts = [
          [p.x, p.y, zR - 0.01], [p.x, p.y + 0.002, zR - 0.05],
          [lerp(p.x, bx, 0.55), p.y - 0.02 - rng.range(0, 0.03), lerp(zR - 0.05, RACK.bundleZ, 0.5) - 0.03],
          [bx + rng.range(-0.012, 0.012), p.y + 0.03, RACK.bundleZ + rng.range(-0.012, 0.012)],
          [bx + rng.range(-0.012, 0.012), p.y + 0.14, RACK.bundleZ + rng.range(-0.012, 0.012)],
        ];
        cables.add(pts.map(([x, y, z]) => toWorld(rack, x, y, z)), r, color, { segLen: 0.1, radial: r < 0.003 ? 3 : 4 });
      }
    });
  });

  // vertical bundles up the rear corners and out through the roof to the tray
  for (const rack of racks) {
    if (rack.profile === 'e') continue;
    const n = quality === 'low' ? 4 : 7;
    for (const s of [-1, 1]) {
      for (let k = 0; k < n; k++) {
        const a = (k / n) * Math.PI * 2 + rng.range(0, 0.4), rr = k === 0 ? 0 : 0.011 + rng.range(0, 0.006);
        const ox = Math.cos(a) * rr, oz = Math.sin(a) * rr;
        const color = k % 3 === 0 ? CABLE.yellow : rng.pick(rack.palette);
        const low = rng.range(0.25, 0.7);
        const bz = RACK.bundleZ;
        const pts = [
          [s * RACK.bundleX + ox, low, bz + oz],
          [s * RACK.bundleX + ox + rng.range(-0.004, 0.004), 1.0, bz + oz],
          [s * RACK.bundleX + ox, 1.6, bz + oz + rng.range(-0.004, 0.004)],
          [s * RACK.bundleX + ox, 1.98, bz + 0.01 + oz],
          [s * 0.18 + ox, 2.2, bz + 0.12 + oz],
          [s * 0.15 + ox, 2.4, TRAY_Z - 0.12 + oz],
          [s * 0.12 + ox, 2.47, TRAY_Z + oz],
        ];
        cables.add(pts.map(([x, y, z]) => toWorld(rack, x, y, z)), 0.0036, color, { segLen: 0.2, radial: 4 });
      }
    }
  }

  const cableMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.5, metalness: 0, name: 'cables' });
  const cableMesh = cables.build(cableMat);
  group.add(devMesh, cableMesh);

  // RJ45 / transceiver boots on patched ports
  const bootGeo = new THREE.BoxGeometry(0.0118, 0.0095, 0.024);
  const bootMesh = new THREE.InstancedMesh(bootGeo, new THREE.MeshStandardMaterial({ roughness: 0.4, metalness: 0 }), boots.length);
  const _c = new THREE.Color();
  boots.forEach((b, i) => {
    _q.setFromAxisAngle(Y, b.rack.facing > 0 ? 0 : Math.PI);
    _m.compose(b.pos, _q, new THREE.Vector3(b.sfp ? 0.8 : 1, 1, 1));
    bootMesh.setMatrixAt(i, _m);
    bootMesh.setColorAt(i, _c.set(b.color));
  });
  group.add(bootMesh);

  const ledMesh = leds.build();
  group.add(ledMesh);

  for (const m of group.children) if (m.isInstancedMesh) m.computeBoundingSphere();

  // ---- interaction ----
  const doorBox = (r) => {
    const c = new THREE.Vector3(0, 1.0, RACK.doorZ).applyMatrix4(r.matrix);
    return new THREE.Box3(new THREE.Vector3(c.x - 0.3, 0.03, c.z - 0.012), new THREE.Vector3(c.x + 0.3, 1.99, c.z + 0.012));
  };
  racks.forEach((r) => { r.doorBox = doorBox(r); });

  const colliders = ROWS.map((row) => ({ minX: -ROW_HALF - 0.02, maxX: ROW_HALF + 0.02, minZ: row.z - RACK.d / 2 - 0.02, maxZ: row.z + RACK.d / 2 + 0.02 }));

  function update(dt, time) {
    ledMesh.material.uniforms.uTime.value = time;
    let dirty = false;
    racks.forEach((r, i) => {
      if (Math.abs(r.door - r.doorTarget) > 1e-3) {
        r.door = damp(r.door, r.doorTarget, 5, dt);
        setDoor(r, i);
        dirty = true;
      }
    });
    if (dirty) {
      doorFrame.instanceMatrix.needsUpdate = true;
      doorPanel.instanceMatrix.needsUpdate = true;
      doorLabel.instanceMatrix.needsUpdate = true;
    }
  }

  const _hit = new THREE.Vector3();
  function pick(ray, maxDist = 3.2) {
    let best = null, bestD = maxDist;
    for (const r of racks) {
      const closed = r.door < 0.25;
      if (closed && ray.intersectBox(r.doorBox, _hit)) {
        const d = _hit.distanceTo(ray.origin);
        if (d < bestD) { bestD = d; best = { rack: r, door: true, device: null }; }
      }
    }
    for (const dev of devices) {
      if (ray.intersectBox(dev.box, _hit)) {
        const d = _hit.distanceTo(ray.origin);
        // through a closed perforated door you can still read what's behind it
        if (d < bestD + 0.3) {
          if (best && best.door && best.rack === dev.rack) {
            if (!best.device || d < best.devD) { best.device = dev; best.devD = d; }
            continue;
          }
          if (d < bestD) { bestD = d; best = { rack: dev.rack, door: false, device: dev }; }
        }
      }
    }
    return best;
  }

  return {
    group, racks, devices, colliders, update, pick, ledMesh, fault,
    stats: { devices: devices.length, leds: leds.count, cables: cables.count, cableVerts: cables.verts },
  };
}

// ------------------------------------------------------------ cabling rules --
function connectFront(dev, reg, rng) {
  const n = reg.anchors.length;
  if (!n) return [];
  const t = dev.def.kind;
  if (dev.type === 'switch48') {
    const servers = dev.rack.devices.filter((d) => d.def.kind === 'server' || d.def.kind === 'gpu' || d.def.kind === 'storage').length;
    const used = dev.u === 42 ? clamp(servers * 2 + rng.int(-2, 4), 6, 48) : clamp(servers + rng.int(0, 6), 4, 40);
    let eth = 0;
    return reg.anchors.map((a) => (a.type === 'eth' ? eth++ < used && rng.chance(0.94) : rng.chance(0.75)));
  }
  if (t === 'switch') return reg.anchors.map(() => rng.chance(0.72));
  if (t === 'patch') return reg.anchors.map(() => rng.chance(0.82));
  return reg.anchors.map(() => false);
}

function firstEth(reg) {
  return reg.anchors.findIndex((a) => a.type === 'eth');
}

function connectRear(dev, reg, rng) {
  const seen = {};
  const out = reg.anchors.map((a) => {
    const k = (seen[a.type] = (seen[a.type] ?? 0) + 1) - 1;
    switch (a.type) {
      case 'psu': return true;
      case 'sfp':
      case 'qsfp': return k < 2 ? rng.chance(0.92) : rng.chance(0.35);
      case 'sas': return k < 2 || rng.chance(0.3);
      case 'eth': return k === 0 ? rng.chance(0.95) : k < 3 ? rng.chance(0.75) : rng.chance(0.12);
      default: return false;
    }
  });
  if (dev.def.kind === 'patch' || dev.def.kind === 'switch' && dev.type === 'switch48') {
    // switch uplinks and patch backs are cabled from the front in this room
    return out.map((v, i) => reg.anchors[i].type === 'psu' && v);
  }
  if (dev.status === 'fault') {
    // the failed feed: PSU 2's cord is out
    let n = 0;
    return out.map((v, i) => (reg.anchors[i].type === 'psu' && n++ === 1 ? false : v));
  }
  return out;
}

function nearestManager(rack, dev) {
  let best = null, bd = 99;
  for (const d of rack.devices) {
    if (d.type !== 'cablemgr') continue;
    const dist = Math.abs(d.u - dev.u);
    if (dist < bd && dist <= 2) { bd = dist; best = d; }
  }
  if (!best) return null;
  return { yc: RACK.base + (best.u - 1) * U + U / 2 };
}
