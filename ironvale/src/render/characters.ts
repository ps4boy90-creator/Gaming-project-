import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import type { Agent, Look } from '../sim/agent';
import type { Gfx } from './gfx';
import { Batch } from './batch';
import { MB, type ModelResult } from './modelkit';
import { makeIconTexture } from './textures';

const HIP = 0.3;
const TORSO_H = 0.36;
const HEAD_Y = HIP + TORSO_H + 0.135;
const SHOULDER_Y = HIP + TORSO_H - 0.05;

function hatModel(kind: number): ModelResult {
  const b = new MB();
  if (kind === 1) {
    // guard cap
    b.cyl(0.165, 0.175, 0.075, 0, 0.085, 0, 0x263a66, 14);
    b.cyl(0.178, 0.178, 0.03, 0, 0.07, 0, 0x1a2747, 14);
    b.box(0.2, 0.02, 0.13, 0, 0.068, 0.15, 0x141c33);
    b.box(0.05, 0.035, 0.012, 0, 0.1, 0.168, 0xe2c14a);
  } else if (kind === 2) {
    // chef hat
    b.cyl(0.15, 0.14, 0.13, 0, 0.08, 0, 0xf6f6f2, 12);
    b.sphere(0.165, 0, 0.15, 0, 0xfbfbf8, 1, 0.62, 1, 12);
  } else if (kind === 3) {
    // hard hat
    b.sphere(0.185, 0, -0.03, 0, 0xf2c230, 1, 0.9, 1.02, 14);
    b.cyl(0.215, 0.215, 0.025, 0, 0.07, 0.02, 0xe0ae22, 14);
    b.box(0.04, 0.05, 0.3, 0, 0.26, 0, 0xe0ae22);
  } else {
    // riot helmet
    b.sphere(0.2, 0, -0.07, 0, 0x1d2026, 1, 1, 1.02, 14);
    b.box(0.26, 0.11, 0.03, 0, 0.0, 0.17, 0x6fb6d8);
  }
  return b.build();
}

const colorCache = new WeakMap<Look, { torso: THREE.Color; legs: THREE.Color; skin: THREE.Color; hair: THREE.Color }>();
function colors(l: Look) {
  let c = colorCache.get(l);
  if (!c) {
    const mk = (h: number) => new THREE.Color().setHex(h, THREE.SRGBColorSpace);
    c = { torso: mk(l.torso), legs: mk(l.legs), skin: mk(l.skin), hair: mk(l.hair) };
    colorCache.set(l, c);
  }
  return c;
}

export const ICONS = ['sleep', 'angry', 'hungry', 'fight', 'family', 'medical', 'cuffs', 'escape', 'work', 'build', 'shower', 'toilet', 'learn', 'calm'];

/** Instanced chibi people with procedural animation. */
export class CharacterRenderer {
  private group = new THREE.Group();
  private torso: Batch;
  private head: Batch;
  private hair: Batch;
  private leg: Batch;
  private arm: Batch;
  private eyes: Batch;
  private hats: Batch[] = [];
  private icons = new Map<string, Batch>();
  private ring: THREE.Mesh;
  private root = new THREE.Matrix4();
  private tmp = new THREE.Matrix4();
  private tmp2 = new THREE.Matrix4();
  private q = new THREE.Quaternion();
  private p = new THREE.Vector3();
  private s = new THREE.Vector3(1, 1, 1);
  private e = new THREE.Euler();
  selectedId = 0;

  constructor(private gfx: Gfx) {
    gfx.scene.add(this.group);
    const cloth = new THREE.MeshStandardMaterial({ roughness: 0.85 });
    const skin = new THREE.MeshStandardMaterial({ roughness: 0.65 });
    const o = { cast: true, receive: true, cap: 128 };
    const torsoG = new RoundedBoxGeometry(0.36, TORSO_H, 0.24, 2, 0.075);
    torsoG.translate(0, TORSO_H / 2, 0);
    this.torso = new Batch(torsoG, cloth, this.group, o);
    const headG = new THREE.SphereGeometry(0.172, 16, 12);
    headG.scale(1, 0.96, 0.97);
    this.head = new Batch(headG, skin, this.group, o);
    const hairG = new THREE.SphereGeometry(0.184, 16, 8, 0, Math.PI * 2, 0, Math.PI * 0.52);
    hairG.rotateX(-0.32);
    this.hair = new Batch(hairG, new THREE.MeshStandardMaterial({ roughness: 0.95 }), this.group, { cast: false, receive: true, cap: 128 });
    const legG = new RoundedBoxGeometry(0.145, HIP, 0.17, 1, 0.045);
    legG.translate(0, -HIP / 2, 0);
    this.leg = new Batch(legG, cloth, this.group, { ...o, cap: 256 });
    const armG = new RoundedBoxGeometry(0.105, 0.3, 0.125, 1, 0.04);
    armG.translate(0, -0.12, 0);
    this.arm = new Batch(armG, cloth, this.group, { ...o, cap: 256 });
    const eyeL = new THREE.SphereGeometry(0.022, 6, 5);
    eyeL.translate(-0.062, 0.012, 0.158);
    const eyeR = new THREE.SphereGeometry(0.022, 6, 5);
    eyeR.translate(0.062, 0.012, 0.158);
    this.eyes = new Batch(mergeGeometries([eyeL, eyeR])!, new THREE.MeshBasicMaterial({ color: 0x1b1b22 }), this.group, { cap: 128, colors: false });
    const hatMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.7 });
    for (let k = 1; k <= 4; k++) this.hats[k] = new Batch(hatModel(k).solid, hatMat, this.group, { cast: true, cap: 32, colors: false });
    const plane = new THREE.PlaneGeometry(1, 1);
    for (const kind of ICONS) {
      const mat = new THREE.MeshBasicMaterial({ map: makeIconTexture(kind), transparent: true, depthTest: false, depthWrite: false, toneMapped: false });
      this.icons.set(kind, new Batch(plane, mat, this.group, { noAO: true, cap: 32, colors: false, renderOrder: 20 }));
    }
    const ringG = new THREE.RingGeometry(0.32, 0.42, 28);
    ringG.rotateX(-Math.PI / 2);
    this.ring = new THREE.Mesh(ringG, new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.95, depthTest: false, toneMapped: false }));
    this.ring.renderOrder = 15;
    this.ring.userData.noAO = true;
    this.ring.visible = false;
    this.group.add(this.ring);
  }

  private part(batch: Batch, x: number, y: number, z: number, rx: number, color?: THREE.Color, sy = 1) {
    this.tmp.makeRotationX(rx);
    if (sy !== 1) this.tmp.scale(this.s.set(1, sy, 1));
    this.tmp.setPosition(x, y, z);
    this.tmp2.multiplyMatrices(this.root, this.tmp);
    batch.addM(this.tmp2, color);
  }

  /** dtAnim: animation time step (already scaled by game speed) */
  update(agents: Agent[], dtAnim: number, time: number) {
    const all = [this.torso, this.head, this.hair, this.leg, this.arm, this.eyes, this.hats[1], this.hats[2], this.hats[3], this.hats[4]];
    for (const b of all) b.begin();
    for (const b of this.icons.values()) b.begin();
    // icons keep a constant size on screen (about 27px) whatever the zoom
    const iconScale = Math.min(4, Math.max(0.5, ((27 * this.gfx.zoom) / this.gfx.height) / 0.52));
    const camQ = this.gfx.camera.quaternion;
    let sel: Agent | null = null;

    for (const a of agents) {
      if (a.hidden || a.dead) continue;
      if (a.id === this.selectedId) sel = a;
      const c = colors(a.look);
      const pose = a.pose;
      const moving = pose === 'walk' || pose === 'run';
      a.anim += dtAnim * (pose === 'run' ? 1.5 : 1);
      const t = a.anim;
      let legL = 0, legR = 0, armL = 0, armR = 0, bob = 0, lean = 0;
      let lying = false, hipDrop = 0;
      switch (pose) {
        case 'walk':
        case 'run': {
          const sw = Math.sin(t * 9) * (pose === 'run' ? 0.95 : 0.62);
          legL = sw; legR = -sw; armL = -sw * 0.85; armR = sw * 0.85;
          bob = Math.abs(Math.sin(t * 9)) * 0.03;
          lean = pose === 'run' ? 0.16 : 0.04;
          break;
        }
        case 'sit':
          legL = legR = -1.45;
          armL = armR = -0.55;
          hipDrop = HIP - 0.075;
          break;
        case 'lie':
        case 'down':
          lying = true;
          if (pose === 'down') { armL = -0.5; armR = 0.4; legL = 0.25; }
          break;
        case 'work': {
          const w = Math.sin(t * 8);
          armL = -1.2 + w * 0.3; armR = -1.2 - w * 0.3;
          lean = 0.12;
          break;
        }
        case 'fight': {
          const w = Math.sin(t * 15);
          armL = -1.45 + Math.max(0, w) * 0.5 - 0.2; armR = -1.45 + Math.max(0, -w) * 0.5 - 0.2;
          legL = 0.25; legR = -0.2;
          bob = Math.abs(Math.sin(t * 7.5)) * 0.03;
          lean = 0.2 + w * 0.08;
          break;
        }
        case 'exercise': {
          const w = Math.sin(t * 7);
          armL = armR = -(1.7 + w * 1.2);
          bob = Math.max(0, w) * 0.09;
          legL = w * 0.2; legR = -w * 0.2;
          break;
        }
        case 'cuffed':
          armL = armR = 0.45;
          lean = 0.15;
          break;
        default: {
          const w = Math.sin(t * 1.6 + a.id);
          armL = w * 0.05; armR = -w * 0.05;
        }
      }

      // root transform
      this.q.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, a.yaw);
      this.p.set(a.x, a.y, a.z);
      this.root.compose(this.p, this.q, this.s.set(1, 1, 1));
      if (lying) {
        this.tmp.makeRotationX(-Math.PI / 2);
        this.tmp.setPosition(0, 0.125, 0.5);
        this.root.multiply(this.tmp);
      } else {
        if (hipDrop || bob) {
          this.tmp.makeTranslation(0, bob - hipDrop, 0);
          this.root.multiply(this.tmp);
        }
      }
      // torso (leans from the hip)
      this.part(this.torso, 0, HIP, 0, lean, c.torso);
      const hz = Math.sin(lean) * (TORSO_H + 0.13), hy = HEAD_Y - (1 - Math.cos(lean)) * 0.3;
      this.part(this.head, 0, hy, hz, lean * 0.5, c.skin);
      this.part(this.eyes, 0, hy, hz, lean * 0.5);
      if (a.look.hat) this.part(this.hats[a.look.hat], 0, hy, hz, lean * 0.5);
      else if (!a.look.bald) this.part(this.hair, 0, hy, hz, lean * 0.5, c.hair);
      const sz = Math.sin(lean) * (TORSO_H - 0.05);
      this.part(this.arm, -0.228, SHOULDER_Y, sz, armL, c.torso);
      this.part(this.arm, 0.228, SHOULDER_Y, sz, armR, c.torso);
      this.part(this.leg, -0.088, HIP, 0, legL, c.legs);
      this.part(this.leg, 0.088, HIP, 0, legR, c.legs);

      // status icon
      const icon = a.icon;
      if (icon) {
        const b = this.icons.get(icon);
        if (b) {
          const top = a.y + (lying ? 0.6 : 1.05 - hipDrop) + 0.3 * iconScale + Math.sin(time * 3 + a.id) * 0.03;
          this.p.set(a.x, top, a.z);
          this.tmp.compose(this.p, camQ, this.s.set(0.52 * iconScale, 0.52 * iconScale, 1));
          b.addM(this.tmp);
        }
      }
      void moving;
    }
    for (const b of all) b.end();
    for (const b of this.icons.values()) b.end();

    if (sel) {
      this.ring.visible = true;
      this.ring.position.set(sel.x, sel.y + 0.04, sel.z);
      const pulse = 1 + Math.sin(time * 5) * 0.07;
      this.ring.scale.set(pulse, 1, pulse);
    } else this.ring.visible = false;
  }

  /** nearest agent to a screen position, or null */
  pick(agents: Agent[], px: number, py: number): Agent | null {
    const unit = this.gfx.height / this.gfx.zoom;
    const maxD = Math.max(16, unit * 0.5);
    let best: Agent | null = null, bd = maxD;
    for (const a of agents) {
      if (a.hidden || a.dead) continue;
      const [sx, sy] = this.gfx.worldToScreen(a.x, a.y + 0.5, a.z);
      const d = Math.hypot(sx - px, sy - py);
      if (d < bd) {
        bd = d;
        best = a;
      }
    }
    return best;
  }
}

/** Static posed figure (for UI thumbnails). */
export function buildFigure(look: Look): THREE.Group {
  const g = new THREE.Group();
  const mat = (hex: number, rough = 0.85) => new THREE.MeshStandardMaterial({ color: new THREE.Color().setHex(hex, THREE.SRGBColorSpace), roughness: rough });
  const torso = new THREE.Mesh(new RoundedBoxGeometry(0.36, TORSO_H, 0.24, 2, 0.075), mat(look.torso));
  torso.position.y = HIP + TORSO_H / 2;
  g.add(torso);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.172, 16, 12), mat(look.skin, 0.65));
  head.position.y = HEAD_Y;
  g.add(head);
  for (const sx of [-1, 1]) {
    const leg = new THREE.Mesh(new RoundedBoxGeometry(0.145, HIP, 0.17, 1, 0.045), mat(look.legs));
    leg.position.set(sx * 0.088, HIP / 2, 0);
    g.add(leg);
    const arm = new THREE.Mesh(new RoundedBoxGeometry(0.105, 0.3, 0.125, 1, 0.04), mat(look.torso));
    arm.position.set(sx * 0.228, SHOULDER_Y - 0.12, 0);
    g.add(arm);
    const eye = new THREE.Mesh(new THREE.SphereGeometry(0.022, 6, 5), new THREE.MeshBasicMaterial({ color: 0x1b1b22 }));
    eye.position.set(sx * 0.062, HEAD_Y + 0.012, 0.158);
    g.add(eye);
  }
  if (look.hat) {
    const hat = new THREE.Mesh(hatModel(look.hat).solid, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.7 }));
    hat.position.y = HEAD_Y;
    g.add(hat);
  } else if (!look.bald) {
    const hg = new THREE.SphereGeometry(0.184, 16, 8, 0, Math.PI * 2, 0, Math.PI * 0.52);
    hg.rotateX(-0.32);
    const hair = new THREE.Mesh(hg, mat(look.hair, 0.95));
    hair.position.y = HEAD_Y;
    g.add(hair);
  }
  return g;
}
