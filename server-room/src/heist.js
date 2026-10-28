// Heist layer: the player carries a laptop, plugs it into an open rack with a
// USB cable, and runs a "breach" mini-game that exfiltrates a fictional dataset
// for score. Everything here is arcade flavor — fake terminal chatter and
// made-up loot, no real technique.
import * as THREE from 'three';
import { Rng } from './util.js';
import { FONT } from './painter.js';

const BREACHABLE = new Set(['server', 'storage', 'gpu', 'switch']);

// Fictional datasets, picked by what the box pretends to be.
const LOOT = {
  storage: ['Customer records archive', 'Nightly backup vault', 'Media asset store'],
  gpu: ['Model weights checkpoint', 'Training dataset shard', 'Render farm cache'],
  switch: ['Routing + ACL tables', 'Flow telemetry dump'],
  role: {
    db: 'Credentials ledger shard', web: 'Session + token store', app: 'App config bundle',
    cache: 'In-memory key dump', k8s: 'Cluster secrets bundle', api: 'Partner API tokens',
    vmh: 'Tenant VM snapshots', batch: 'ETL staging data',
  },
};

function datasetFor(dev) {
  const r = new Rng([...dev.hostname].reduce((a, c) => a + c.charCodeAt(0), 7) * 97);
  let name;
  if (dev.def.kind === 'server') {
    const role = (dev.hostname.split('-')[0] || '').replace(/[0-9]/g, '');
    name = LOOT.role[role] ?? 'Service account keys';
  } else {
    name = r.pick(LOOT[dev.def.kind] ?? ['Raw data blocks']);
  }
  const gb = dev.def.kind === 'storage' ? r.range(18, 240) : dev.def.kind === 'gpu' ? r.range(6, 90) : r.range(0.4, 24);
  return { name, gb: Math.round(gb * 10) / 10 };
}

const LOG = [
  '> usb-c bridge: link up', '> handshake ack 0x7F', '> bypassing console lock',
  '> enumerating volumes', '> mounting vol0 (ro)', '> indexing records',
  '> staging payload', '> compressing archive', '> opening exfil channel',
];

export class Heist {
  constructor(camera, scene, hud, audio) {
    this.camera = camera;
    this.scene = scene;
    this.hud = hud;
    this.audio = audio;
    this.breached = new Set();
    this.count = 0;
    this.gb = 0;
    this.state = 'idle'; // idle | connecting | breaching | done | abort
    this.t = 0;
    this.dur = 6.5;
    this.active = null; // { dev, port, data }
    this.log = [];
    this.screenT = 0;

    this.buildLaptop();
    this.buildCable();
    this.drawScreen();
  }

  // ----------------------------------------------------- viewmodel ----
  buildLaptop() {
    const g = (this.group = new THREE.Group());
    g.visible = false;
    this.camera.add(g);
    g.position.set(0.17, -0.215, -0.4);
    g.rotation.set(-0.12, -0.42, 0);
    g.scale.setScalar(0.9);

    const shell = new THREE.MeshStandardMaterial({ color: 0x2a2d31, roughness: 0.42, metalness: 0.7 });
    const dark = new THREE.MeshStandardMaterial({ color: 0x101113, roughness: 0.5, metalness: 0.4 });

    const base = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.015, 0.18), shell);
    base.position.y = -0.002;
    g.add(base);

    // keyboard deck + trackpad
    const deck = document.createElement('canvas');
    deck.width = 256; deck.height = 176;
    const dc = deck.getContext('2d');
    dc.fillStyle = '#17181b'; dc.fillRect(0, 0, 256, 176);
    dc.fillStyle = '#26282c';
    for (let r = 0; r < 5; r++) for (let c = 0; c < 14; c++) { dc.fillRect(10 + c * 17, 8 + r * 15, 14, 12); }
    dc.fillStyle = '#1b1d20'; dc.fillRect(78, 92, 100, 64);
    dc.strokeStyle = '#34373c'; dc.lineWidth = 1; dc.strokeRect(78, 92, 100, 64);
    const deckTex = new THREE.CanvasTexture(deck);
    deckTex.colorSpace = THREE.SRGBColorSpace;
    const deckTop = new THREE.Mesh(new THREE.PlaneGeometry(0.25, 0.17).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ map: deckTex, roughness: 0.55 }));
    deckTop.position.set(0, 0.0065, 0.004);
    g.add(deckTop);

    // USB-C port on the right edge (cable origin)
    const port = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.004, 0.016), dark);
    port.position.set(0.131, 0, -0.02);
    g.add(port);
    this.portLocal = new THREE.Vector3(0.138, 0.001, -0.02);

    // hinged lid with the screen
    const lid = (this.lid = new THREE.Group());
    lid.position.set(0, 0.006, -0.088);
    g.add(lid);
    const back = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.165, 0.008), shell);
    back.position.y = 0.082;
    lid.add(back);
    const sc = document.createElement('canvas');
    sc.width = 512; sc.height = 320;
    this.screen = { canvas: sc, ctx: sc.getContext('2d') };
    const stex = (this.screenTex = new THREE.CanvasTexture(sc));
    stex.colorSpace = THREE.SRGBColorSpace;
    const screenMat = new THREE.MeshStandardMaterial({ map: stex, emissiveMap: stex, emissive: 0xffffff, emissiveIntensity: 1.1, roughness: 0.3 });
    const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.236, 0.147), screenMat);
    screen.position.set(0, 0.082, 0.0055);
    lid.add(screen);
    lid.rotation.x = -1.96; // open

    // a subtle apple-of-nothing glow logo on the lid back
    g.traverse((o) => { if (o.isMesh) o.userData.noAO = true; o.frustumCulled = false; });
    g.renderOrder = 6;
  }

  buildCable() {
    const mat = new THREE.MeshStandardMaterial({ color: 0x15171a, roughness: 0.55, metalness: 0 });
    this.cable = new THREE.Mesh(new THREE.BufferGeometry(), mat);
    this.cable.frustumCulled = false;
    this.cable.visible = false;
    this.cable.userData.noAO = true;
    this.scene.add(this.cable);
    this._from = new THREE.Vector3();
    this._mid = new THREE.Vector3();
  }

  updateCable(to, reach) {
    this.group.getWorldPosition(this._from);
    this._from.copy(this.portLocal).applyMatrix4(this.group.matrixWorld);
    const from = this._from, mid = this._mid.lerpVectors(from, to, 0.5);
    mid.y -= 0.12 + 0.05 * Math.sin(this.t * 2);
    const tip = from.clone().lerp(to, reach);
    if (reach < 1) mid.lerpVectors(from, tip, 0.5).add(new THREE.Vector3(0, -0.05, 0));
    const curve = new THREE.CatmullRomCurve3([from, this._mid.clone(), reach < 1 ? tip : to]);
    const geo = new THREE.TubeGeometry(curve, 20, 0.006, 6, false);
    this.cable.geometry.dispose();
    this.cable.geometry = geo;
  }

  // ------------------------------------------------------- state ------
  show() { this.group.visible = true; this.drawScreen(); }

  canBreach(target) {
    const d = target?.device;
    return !!(d && d.hostname && BREACHABLE.has(d.def.kind) && target.rack.door > 1.0 && !this.breached.has(d));
  }

  prompt(target) {
    if (this.state === 'connecting' || this.state === 'breaching') return 'Breaching… stay close';
    const d = target?.device;
    if (d && BREACHABLE.has(d.def.kind) && d.hostname) {
      if (this.breached.has(d)) return null;
      if (target.rack.door <= 1.0) return null;
      return `Breach ${d.hostname}`;
    }
    return null;
  }

  tryBreach(target) {
    if (this.state === 'connecting' || this.state === 'breaching') return;
    if (!this.canBreach(target)) {
      if (target?.device && BREACHABLE.has(target.device.def.kind) && target.rack.door <= 1.0) this.hud.toast('Open the rack door first (E), then plug in.', 2600);
      return;
    }
    const dev = target.device;
    const port = dev.box.clampPoint(this.camera.position, new THREE.Vector3());
    port.lerp(this.camera.position, 0.04);
    this.active = { dev, port, data: datasetFor(dev) };
    this.state = 'connecting';
    this.t = 0;
    this.log = [];
    this.cable.visible = true;
    this.audio.tone?.(520, 0.08);
  }

  abort(msg) {
    this.state = 'idle';
    this.cable.visible = false;
    this.active = null;
    this.hud.toast(msg, 2600);
    this.hud.breach(null);
    this.drawScreen();
  }

  update(dt, time, target, player) {
    this.t += dt;
    if (!this.group.visible) return;

    // idle hand-sway
    const sway = Math.sin(time * 1.3) * 0.004 + Math.sin(time * 0.7) * 0.003;
    this.group.position.y = -0.215 + sway;
    this.group.rotation.z = Math.sin(time * 0.9) * 0.01;

    const A = this.active;
    if (A) {
      const dist = Math.hypot(this.camera.position.x - A.port.x, this.camera.position.z - A.port.z);
      if (dist > 2.0 && this.state !== 'done') { this.abort('Connection dropped — cable yanked out.'); return; }
    }

    if (this.state === 'connecting') {
      const reach = Math.min(1, this.t / 0.5);
      this.updateCable(A.port, reach);
      if (reach >= 1) { this.state = 'breaching'; this.t = 0; this.audio.tone?.(760, 0.06); this.audio.hack?.(true); }
      this.drawScreen();
    } else if (this.state === 'breaching') {
      this.updateCable(A.port, 1);
      const p = Math.min(1, this.t / this.dur);
      const want = Math.floor(p * LOG.length);
      while (this.log.length < want) { this.log.push(LOG[this.log.length]); this.audio.tone?.(1200 + Math.random() * 400, 0.015); }
      this.hud.breach({ title: `${A.dev.hostname} · ${A.data.name}`, pct: p });
      if (time - this.screenT > 0.05) { this.screenT = time; this.drawScreen(p); }
      if (p >= 1) {
        this.state = 'done'; this.t = 0;
        this.breached.add(A.dev);
        this.count++; this.gb = Math.round((this.gb + A.data.gb) * 10) / 10;
        this.audio.hack?.(false); this.audio.tone?.(300, 0.25);
        this.hud.loot(this.count, this.gb);
        this.hud.toast(`Exfiltrated: ${A.data.name} — ${A.data.gb} GB`, 5000);
        this.drawScreen(1);
      }
    } else if (this.state === 'done') {
      this.updateCable(A.port, 1);
      if (this.t > 2.2) { this.state = 'idle'; this.cable.visible = false; this.active = null; this.hud.breach(null); this.drawScreen(); }
    }
  }

  // ------------------------------------------------------- screen -----
  drawScreen(p = 0) {
    const { ctx: c } = this.screen;
    const W = 512, H = 320;
    c.fillStyle = '#060a09'; c.fillRect(0, 0, W, H);
    c.fillStyle = '#0c1512'; c.fillRect(0, 0, W, 34);
    c.fillStyle = '#39e08a'; c.font = `700 20px ${FONT}`; c.textBaseline = 'middle';
    c.fillText('SUBVERT  //  field console', 16, 18);
    c.font = `500 15px monospace`;
    const A = this.active;
    if (this.state === 'idle' || !A) {
      c.fillStyle = '#6fe3a8';
      c.fillText('READY', 16, 64);
      c.fillStyle = '#4a8f70';
      c.fillText('Open a rack (E), aim at a server,', 16, 92);
      c.fillText('press R to plug in and breach.', 16, 114);
      c.fillStyle = '#2f6b50'; c.fillRect(16, 150, W - 32, 1);
      c.fillStyle = '#6fe3a8';
      c.fillText(`loot   ${this.count} systems`, 16, 180);
      c.fillText(`data   ${this.gb} GB`, 16, 204);
      c.fillStyle = '#2b5a44';
      c.fillText('no live network — training rig', 16, 286);
    } else {
      c.fillStyle = '#8af0b6';
      c.fillText(`target  ${A.dev.hostname}`, 16, 60);
      c.fillText(`data    ${A.data.name}`, 16, 82);
      let y = 118;
      c.fillStyle = '#39e08a';
      for (const l of this.log.slice(-6)) { c.fillText(l, 16, y); y += 20; }
      if (this.state === 'breaching') { c.fillStyle = '#39e08a'; c.fillText(`> exfil ${Math.round(p * 100)}%`, 16, y); }
      // progress bar
      c.strokeStyle = '#2f6b50'; c.strokeRect(16, 262, W - 32, 18);
      c.fillStyle = '#39e08a'; c.fillRect(18, 264, (W - 36) * (this.state === 'done' ? 1 : p), 14);
      if (this.state === 'done') { c.fillStyle = '#eaffed'; c.font = `700 18px ${FONT}`; c.fillText(`EXFILTRATED  ${A.data.gb} GB`, 16, 240); }
    }
    this.screenTex.needsUpdate = true;
  }
}
