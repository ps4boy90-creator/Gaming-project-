import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { MAP_W, MAP_H } from '../data/defs';
import { clamp, lerp, smooth } from '../core/util';

export type Quality = 'low' | 'medium' | 'high';

const ELEVATION = (38 * Math.PI) / 180;
const CAM_DIST = 160;

/** Core renderer: scene, isometric camera, lights, day/night and post-processing. */
export class Gfx {
  renderer: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  camera: THREE.OrthographicCamera;
  sun: THREE.DirectionalLight;
  hemi: THREE.HemisphereLight;
  composer: EffectComposer | null = null;
  private gtao: GTAOPass | null = null;
  private bloom: UnrealBloomPass | null = null;
  quality: Quality = 'high';

  // camera state
  target = new THREE.Vector3(MAP_W / 2, 0, MAP_H / 2);
  /** quarter-turn index; the azimuth eases towards 45deg + 90deg * rotIndex */
  rotIndex = 0;
  azimuth = Math.PI / 4;
  zoom = 34;
  zoomTarget = 34;
  minZoom = 7;
  maxZoom = 120;

  /** 0 = full day, 1 = deep night */
  night = 0;
  /** objects register per-frame callbacks for night-dependent materials */
  onNight: ((night: number) => void)[] = [];

  private raycaster = new THREE.Raycaster();
  private ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  private v2 = new THREE.Vector2();
  private v3 = new THREE.Vector3();
  width = 1;
  height = 1;

  constructor(public canvas: HTMLCanvasElement) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance', stencil: false });
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.scene.background = new THREE.Color(0x40613a);

    this.camera = new THREE.OrthographicCamera(-10, 10, 10, -10, 1, 600);

    this.hemi = new THREE.HemisphereLight(0xcfe3ff, 0x6b6250, 1.1);
    this.scene.add(this.hemi);
    this.sun = new THREE.DirectionalLight(0xfff1d6, 3.0);
    this.sun.castShadow = true;
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.normalBias = 0.035;
    this.sun.shadow.camera.near = 1;
    this.sun.shadow.camera.far = 400;
    this.scene.add(this.sun);
    this.scene.add(this.sun.target);

    this.setQuality('high');
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  setQuality(q: Quality) {
    this.quality = q;
    const pr = q === 'low' ? 1 : Math.min(window.devicePixelRatio || 1, q === 'high' ? 2 : 1.5);
    this.renderer.setPixelRatio(pr);
    const size = q === 'high' ? 4096 : q === 'medium' ? 2048 : 1024;
    const max = this.renderer.capabilities.maxTextureSize;
    this.sun.shadow.mapSize.set(Math.min(size, max), Math.min(size, max));
    if (this.sun.shadow.map) {
      this.sun.shadow.map.dispose();
      (this.sun.shadow as any).map = null;
    }
    this.sun.shadow.radius = q === 'high' ? 2.2 : 1.5;
    if (this.composer) {
      this.composer.dispose();
      this.composer = null;
      this.gtao = null;
      this.bloom = null;
    }
    if (q !== 'low') {
      const w = Math.max(2, this.canvas.clientWidth), h = Math.max(2, this.canvas.clientHeight);
      const rt = new THREE.WebGLRenderTarget(w * pr, h * pr, { type: THREE.HalfFloatType, samples: 4 });
      const composer = new EffectComposer(this.renderer, rt);
      composer.addPass(new RenderPass(this.scene, this.camera));
      if (q === 'high') {
        const gtao = new GTAOPass(this.scene, this.camera, w, h);
        gtao.updateGtaoMaterial({ radius: 0.55, distanceExponent: 1.2, thickness: 1.4, scale: 1.25, samples: 12, distanceFallOff: 1, screenSpaceRadius: false });
        gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, radiusExponent: 1, rings: 2, samples: 12 });
        gtao.blendIntensity = 0.9;
        // keep overlays, sprites and translucent helpers out of the AO g-buffer
        const anyG = gtao as any;
        anyG._overrideVisibility = function () {
          const cache = this._visibilityCache;
          this.scene.traverse((o: any) => {
            if ((o.isPoints || o.isLine || o.isSprite || o.userData.noAO) && o.visible) {
              o.visible = false;
              cache.push(o);
            }
          });
        };
        composer.addPass(gtao);
        this.gtao = gtao;
      }
      const bloom = new UnrealBloomPass(new THREE.Vector2(w, h), 0.22, 0.6, 0.92);
      composer.addPass(bloom);
      this.bloom = bloom;
      composer.addPass(new OutputPass());
      this.composer = composer;
    }
    this.resize();
  }

  resize() {
    const w = Math.max(2, this.canvas.clientWidth || window.innerWidth);
    const h = Math.max(2, this.canvas.clientHeight || window.innerHeight);
    this.width = w;
    this.height = h;
    this.renderer.setSize(w, h, false);
    if (this.composer) {
      this.composer.setPixelRatio(this.renderer.getPixelRatio());
      this.composer.setSize(w, h);
    }
    this.updateCamera();
  }

  // ------------------------------------------------------------ camera
  rotate(dir: number) {
    this.rotIndex += dir;
  }

  get camRight(): THREE.Vector3 {
    return new THREE.Vector3(Math.cos(this.azimuth), 0, -Math.sin(this.azimuth));
  }
  get camForward(): THREE.Vector3 {
    // direction on the ground pointing "up the screen"
    return new THREE.Vector3(-Math.sin(this.azimuth), 0, -Math.cos(this.azimuth));
  }

  /** pan by screen-space pixels */
  panPixels(dx: number, dy: number) {
    const unitsPerPx = this.zoom / this.height;
    const r = this.camRight, f = this.camForward;
    this.target.addScaledVector(r, -dx * unitsPerPx);
    this.target.addScaledVector(f, (dy * unitsPerPx) / Math.sin(ELEVATION));
    this.clampTarget();
  }
  panUnits(right: number, forward: number) {
    this.target.addScaledVector(this.camRight, right);
    this.target.addScaledVector(this.camForward, forward);
    this.clampTarget();
  }
  private clampTarget() {
    this.target.x = clamp(this.target.x, -6, MAP_W + 6);
    this.target.z = clamp(this.target.z, -6, MAP_H + 12);
  }
  zoomBy(factor: number) {
    this.zoomTarget = clamp(this.zoomTarget * factor, this.minZoom, this.maxZoom);
  }

  updateCamera(dt = 0) {
    const targetAz = Math.PI / 4 + (this.rotIndex * Math.PI) / 2;
    if (dt > 0) {
      const k = 1 - Math.exp(-dt * 10);
      this.azimuth += (targetAz - this.azimuth) * k;
      this.zoom += (this.zoomTarget - this.zoom) * (1 - Math.exp(-dt * 14));
    } else {
      this.azimuth = targetAz;
      this.zoom = this.zoomTarget;
    }
    const aspect = this.width / this.height;
    const hh = this.zoom / 2, hw = hh * aspect;
    const cam = this.camera;
    cam.left = -hw;
    cam.right = hw;
    cam.top = hh;
    cam.bottom = -hh;
    const ce = Math.cos(ELEVATION), se = Math.sin(ELEVATION);
    cam.position.set(
      this.target.x + Math.sin(this.azimuth) * ce * CAM_DIST,
      se * CAM_DIST,
      this.target.z + Math.cos(this.azimuth) * ce * CAM_DIST,
    );
    cam.lookAt(this.target);
    cam.updateProjectionMatrix();
    cam.updateMatrixWorld();
  }

  /** screen pixel -> point on the ground plane (y = 0) */
  screenToGround(px: number, py: number, out = new THREE.Vector3()): THREE.Vector3 | null {
    this.v2.set((px / this.width) * 2 - 1, -(py / this.height) * 2 + 1);
    this.raycaster.setFromCamera(this.v2, this.camera);
    return this.raycaster.ray.intersectPlane(this.ground, out);
  }
  /** world position -> screen pixel */
  worldToScreen(x: number, y: number, z: number): [number, number] {
    this.v3.set(x, y, z).project(this.camera);
    return [(this.v3.x * 0.5 + 0.5) * this.width, (-this.v3.y * 0.5 + 0.5) * this.height];
  }

  // ------------------------------------------------------------ lighting
  /** hour in [0, 24) */
  setTimeOfDay(hour: number) {
    // daylight factor: 1 during the day, 0 at night, smooth at dawn (5.5-7.5) and dusk (18.5-20.5)
    let day: number;
    if (hour < 5.5 || hour >= 20.5) day = 0;
    else if (hour < 7.5) day = smooth((hour - 5.5) / 2);
    else if (hour < 18.5) day = 1;
    else day = 1 - smooth((hour - 18.5) / 2);
    this.night = 1 - day;

    // sun path: rises in the east (+X), sets in the west. Kept fairly high so shadows stay readable.
    const dayT = clamp((hour - 5.5) / 15, 0, 1);
    const sunAz = lerp(-1.1, 1.9, dayT) + Math.PI * 0.25;
    const sunEl = (lerp(24, 62, Math.sin(dayT * Math.PI)) * Math.PI) / 180;
    // moon: fixed, high and cool
    const moonAz = 2.4, moonEl = (58 * Math.PI) / 180;
    const useMoon = day < 0.12;
    const az = useMoon ? moonAz : sunAz;
    const el = useMoon ? moonEl : sunEl;
    this.sunDir.set(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az)).normalize();

    // warm tint near the horizon
    const warm = 1 - Math.sin(dayT * Math.PI);
    const sunCol = new THREE.Color(0xfff3dc).lerp(new THREE.Color(0xffb070), clamp(warm * 1.1 - 0.25, 0, 1));
    if (useMoon) {
      const m = 1 - day / 0.12;
      this.sun.color.set(0x9db8ff);
      this.sun.intensity = 1.7 * m;
    } else {
      this.sun.color.copy(sunCol);
      this.sun.intensity = 3.1 * smooth(clamp((day - 0.12) / 0.5, 0, 1));
    }
    this.hemi.color.set(0xcfe3ff).lerp(new THREE.Color(0x8ea2e6), this.night);
    this.hemi.groundColor.set(0x7a715c).lerp(new THREE.Color(0x3a4270), this.night);
    this.hemi.intensity = lerp(1.15, 1.2, this.night);
    (this.scene.background as THREE.Color).set(0x40613a).lerp(new THREE.Color(0x18243a), this.night);
    this.renderer.toneMappingExposure = lerp(1.0, 1.08, this.night);
    if (this.bloom) this.bloom.strength = lerp(0.12, 0.5, this.night);
    for (const fn of this.onNight) fn(this.night);
  }
  private sunDir = new THREE.Vector3(0.5, 0.8, 0.3).normalize();

  private fitShadow() {
    const aspect = this.width / this.height;
    // radius of the visible ground footprint around the target
    const viewR = Math.hypot((this.zoom * aspect) / 2, this.zoom / 2 / Math.sin(ELEVATION));
    const ext = clamp(viewR * 1.05 + 3, 14, 110);
    const sc = this.sun.shadow.camera;
    sc.left = -ext;
    sc.right = ext;
    sc.top = ext;
    sc.bottom = -ext;
    // snap the shadow frustum centre to shadow texels to stop shimmering while panning
    const texel = (ext * 2) / this.sun.shadow.mapSize.x;
    const d = this.sunDir;
    const right = new THREE.Vector3(d.z, 0, -d.x).normalize();
    const up = new THREE.Vector3().crossVectors(d, right).normalize();
    const c = this.target;
    const rx = Math.round(c.dot(right) / texel) * texel;
    const uy = Math.round(c.dot(up) / texel) * texel;
    const along = c.dot(d);
    const centre = new THREE.Vector3().addScaledVector(right, rx).addScaledVector(up, uy).addScaledVector(d, along);
    this.sun.target.position.copy(centre);
    this.sun.position.copy(centre).addScaledVector(d, 200);
    this.sun.target.updateMatrixWorld();
    sc.updateProjectionMatrix();
  }

  render(dt: number) {
    this.updateCamera(dt);
    this.fitShadow();
    if (this.composer) this.composer.render(dt);
    else this.renderer.render(this.scene, this.camera);
  }
}
