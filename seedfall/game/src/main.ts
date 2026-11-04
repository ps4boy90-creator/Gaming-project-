import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { Input } from './core/input';
import { bus } from './core/events';
import { ShipClock } from './core/clock';
import { loadSave, writeSave, loadSettings, saveSettings, SaveData, Settings, FlagValue, clearSave } from './core/save';
import { CollisionWorld, rayBox } from './world/collision';
import { Materials, DECK_COLORS } from './world/ship/materials';
import { LightPool } from './world/ship/lights';
import { Kit, Item, Room, Seat } from './world/ship/kit';
import { buildLayout, DECK_Y, ShipRefs } from './world/ship/layout';
import { Builder } from './world/ship/builder';
import { buildExterior } from './world/ship/exterior';
import { OrbitView } from './world/orbit/orbit';
import { Player } from './player/player';
import { AudioEngine } from './audio/audio';
import { Hud, TouchControls } from './ui/hud';
import { Pipeline } from './render/pipeline';
import { VESTA_ROOMS, MAIL, OBJECTIVES, FREE_ROAM, FLAVOR, PLANET_FACTS } from './systems/story';

type State = 'loading' | 'title' | 'play' | 'paused' | 'reader' | 'scope' | 'busy';

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const frame = () => new Promise<void>((r) => requestAnimationFrame(() => r()));
const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

interface HotApi {
  snapshot?: (fn: () => unknown) => void;
  ready?: (fn: (data: unknown) => void) => void;
  data?: unknown;
}

class Game {
  state: State = 'loading';
  settings: Settings = loadSettings();
  renderer!: THREE.WebGLRenderer;
  interior = new THREE.Scene();
  over = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(75, 1, 0.05, 6000);
  world = new CollisionWorld();
  mats!: Materials;
  kit!: Kit;
  refs!: ShipRefs;
  lights!: LightPool;
  orbit!: OrbitView;
  pipeline!: Pipeline;
  player!: Player;
  input!: Input;
  touch!: TouchControls;
  audio = new AudioEngine();
  hud = new Hud();
  clock = new ShipClock();
  flags: Record<string, FlagValue> = {};
  sun = new THREE.DirectionalLight(0xfff1dc, 3);
  hemi = new THREE.HemisphereLight(0x0b1018, 0x6c7a66, 0.5);
  private room: Room | null = null;
  private target: Item | null = null;
  private last = performance.now();
  private elapsed = 0;
  private shake = 0;
  private scopeT = 0;
  private scopeDone = false;
  private prevFov = 75;
  private returnTo: 'title' | 'paused' = 'title';
  private holo: THREE.Mesh | null = null;
  private hotSave: SaveData | null = null;

  async boot(): Promise<void> {
    const canvas = $<HTMLCanvasElement>('view');
    this.input = new Input(canvas);
    this.touch = new TouchControls(this.input);
    try {
      this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance', stencil: false });
    } catch {
      this.hud.setLoading('WebGL is not available in this browser. Try a desktop browser with hardware acceleration on.', 0);
      return;
    }
    const r = this.renderer;
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 1.05;
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    this.applyPixelRatio();
    r.setSize(window.innerWidth, window.innerHeight, false);

    this.hud.setLoading('Calibrating environment light…', 0.05);
    await frame();
    const pmrem = new THREE.PMREMGenerator(r);
    const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    this.interior.environment = env;
    this.interior.environmentIntensity = 0.22;
    this.over.environment = env;
    this.over.environmentIntensity = 0.12;
    this.interior.fog = new THREE.FogExp2(0x0b0f12, 0.006);

    const steps = ['wall cladding', 'deck plating', 'metals', 'fabrics', 'collector film'];
    let si = 0;
    await frame();
    this.mats = new Materials((label) => {
      si++;
      this.hud.setLoading(`Printing ${label}…`, 0.08 + (si / steps.length) * 0.32);
    });
    this.hud.setLoading('Pressurising decks…', 0.45);
    await frame();
    await document.fonts?.ready?.catch(() => undefined);

    this.lights = new LightPool(this.interior, this.settings.quality === 'low' ? 7 : 10);
    this.kit = new Kit(this.mats, this.world, this.interior, this.lights);
    this.refs = buildLayout(this.kit);
    this.kit.b.build(this.interior, this.over);
    const ext = new Builder(this.mats, this.world);
    buildExterior(ext);
    ext.build(this.interior, this.over).forEach((m) => {
      m.castShadow = false;
      m.receiveShadow = false;
    });
    this.mats.signs.commit();
    this.mats.screens.commit();
    this.addHologram();
    this.addMist();

    this.hud.setLoading('Imaging KX-7c from orbit…', 0.62);
    await frame();
    this.orbit = new OrbitView(r, this.settings.quality);
    this.orbit.setPixelRatio(r.getPixelRatio());
    this.over.add(this.orbit.group);

    this.sun.castShadow = true;
    this.sun.shadow.mapSize.setScalar(this.settings.quality === 'low' ? 1024 : 2048);
    const sc = this.sun.shadow.camera;
    sc.left = sc.bottom = -18;
    sc.right = sc.top = 18;
    sc.near = 1;
    sc.far = 200;
    this.sun.shadow.bias = -0.0006;
    this.sun.shadow.normalBias = 0.06;
    this.interior.add(this.sun, this.sun.target, this.hemi);

    this.hud.setLoading('Waking VESTA…', 0.85);
    await frame();
    this.player = new Player(this.camera, this.world);
    this.interior.add(this.camera);
    this.applySettings();
    this.pipeline = new Pipeline(r, this.interior, this.over, this.camera);
    this.pipeline.build(this.settings.quality);
    // compile shaders up front from the title view
    this.titleCamera(0);
    this.orbit.update(0, this.camera.position);
    r.compile(this.interior, this.camera);
    this.pipeline.render(0);

    this.wireUi();
    this.wireEvents();
    window.addEventListener('resize', () => this.resize());
    this.resize();
    await this.setupHot();
    this.hud.setLoading('Ready.', 1);
    await wait(250);
    this.toTitle();
    requestAnimationFrame(() => this.loop());
    (window as unknown as { __seedfall: unknown }).__seedfall = this.debugApi();
  }

  // ------------------------------------------------------------------ setup helpers

  private applyPixelRatio(): void {
    const dpr = window.devicePixelRatio || 1;
    const q = this.settings.quality;
    const pr = q === 'low' ? Math.min(dpr, 1) * 0.8 : q === 'medium' ? Math.min(dpr, 1.5) : Math.min(dpr, 2);
    this.renderer.setPixelRatio(pr);
  }

  private applySettings(): void {
    this.camera.fov = this.settings.fov;
    this.camera.updateProjectionMatrix();
    this.prevFov = this.settings.fov;
    this.player.sensitivity = this.settings.sensitivity;
    this.player.headBob = this.settings.headBob;
    this.audio.setVolume(this.settings.volume);
  }

  private resize(): void {
    const w = window.innerWidth;
    const h = window.innerHeight;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.pipeline?.resize();
  }

  private addHologram(): void {
    const g = new THREE.Group();
    const wire = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.34, 3),
      new THREE.MeshBasicMaterial({ color: 0x6fe0ff, wireframe: true, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false }),
    );
    const core = new THREE.Mesh(
      new THREE.SphereGeometry(0.3, 32, 16),
      new THREE.MeshBasicMaterial({ color: 0x1d4a44, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false }),
    );
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(0.5, 0.004, 4, 64),
      new THREE.MeshBasicMaterial({ color: 0xffb050, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending }),
    );
    ring.rotation.x = Math.PI / 2 - 0.5;
    const ship = new THREE.Mesh(new THREE.SphereGeometry(0.018, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffd080 }));
    ship.position.set(0.5, 0, 0);
    ring.add(ship);
    g.add(core, wire, ring);
    g.position.copy(this.refs.holoPos);
    this.interior.add(g);
    this.holo = wire;
  }

  private addMist(): void {
    const mat = new THREE.MeshBasicMaterial({
      map: this.mats.mistTex,
      color: 0x8fc8e0,
      transparent: true,
      opacity: 0.14,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    for (let i = 0; i < 4; i++) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(38, 11), mat.clone());
      m.rotation.x = -Math.PI / 2;
      m.position.set(-43, 0.08 + i * 0.12, -8);
      (m.material as THREE.MeshBasicMaterial).map = this.mats.mistTex.clone();
      (m.material as THREE.MeshBasicMaterial).map!.repeat.set(3, 1);
      (m.material as THREE.MeshBasicMaterial).map!.needsUpdate = true;
      m.userData.speed = 0.004 + i * 0.002;
      m.name = 'mist';
      m.renderOrder = 3;
      this.interior.add(m);
    }
  }

  /** Keep progress across live republishes of the page (the viewer's hot-update hook). */
  private async setupHot(): Promise<void> {
    const hot = (window as unknown as { claude?: { hot?: HotApi } }).claude?.hot;
    if (!hot) return;
    hot.snapshot?.(() => (this.state === 'title' || this.state === 'loading' ? null : this.snapshot()));
    const take = (data: unknown) => {
      const d = data as SaveData | null | undefined;
      if (d && d.version === 1) this.hotSave = d;
    };
    if (hot.ready) await new Promise<void>((res) => hot.ready!((d) => { take(d); res(); }));
    else take(hot.data);
  }

  // ------------------------------------------------------------------ UI wiring

  private wireUi(): void {
    const click = (id: string, fn: () => void) => $(id).addEventListener('click', () => {
      this.audio.play('ui');
      fn();
    });
    click('btn-new', () => void this.newGame());
    click('btn-continue', () => void this.continueGame());
    click('btn-settings', () => this.openSettings('title'));
    click('btn-controls', () => this.openControls('title'));
    click('btn-resume', () => this.resume());
    click('btn-save', () => {
      this.save();
      this.hud.notice('Game saved.', 1800);
      $('pause-hint').textContent = `Saved at ${this.clock.format()}.`;
    });
    click('btn-psettings', () => this.openSettings('paused'));
    click('btn-pcontrols', () => this.openControls('paused'));
    click('btn-quit', () => {
      this.save();
      this.toTitle();
    });
    click('reader-close', () => this.closeReader(true));
    click('controls-close', () => {
      this.hud.show('controls', false);
      this.hud.show(this.returnTo === 'title' ? 'title' : 'pause', true);
    });

    const form = $<HTMLFormElement>('settings-form');
    const q = $<HTMLSelectElement>('set-quality');
    const sens = $<HTMLInputElement>('set-sens');
    const fov = $<HTMLInputElement>('set-fov');
    const vol = $<HTMLInputElement>('set-vol');
    const bob = $<HTMLInputElement>('set-bob');
    const sync = () => {
      $('out-sens').textContent = Number(sens.value).toFixed(2);
      $('out-fov').textContent = `${fov.value}°`;
      $('out-vol').textContent = `${Math.round(Number(vol.value) * 100)}%`;
    };
    const fill = () => {
      q.value = this.settings.quality;
      sens.value = String(this.settings.sensitivity);
      fov.value = String(this.settings.fov);
      vol.value = String(this.settings.volume);
      bob.checked = this.settings.headBob;
      sync();
    };
    fill();
    [sens, fov, vol].forEach((el) => el.addEventListener('input', sync));
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const prevQ = this.settings.quality;
      this.settings = {
        quality: q.value as Settings['quality'],
        sensitivity: Number(sens.value),
        fov: Number(fov.value),
        volume: Number(vol.value),
        headBob: bob.checked,
      };
      saveSettings(this.settings);
      this.applySettings();
      if (prevQ !== this.settings.quality) {
        this.applyPixelRatio();
        this.orbit.setPixelRatio(this.renderer.getPixelRatio());
        this.pipeline.build(this.settings.quality);
        this.resize();
      }
      this.hud.show('settings', false);
      this.hud.show(this.returnTo === 'title' ? 'title' : 'pause', true);
    });
    $('settings').addEventListener('fill', fill);

    window.addEventListener('keydown', (e) => {
      if (e.code !== 'Escape') return;
      if (this.state === 'reader') this.closeReader(false);
      else if (this.hud.isOpen('settings') || this.hud.isOpen('controls')) {
        this.hud.show('settings', false);
        this.hud.show('controls', false);
        this.hud.show(this.returnTo === 'title' ? 'title' : 'pause', true);
      } else if (this.state === 'scope') this.exitScope();
      else if (this.state === 'play' && !this.input.pointerLocked) this.pause();
    });
    $('view').addEventListener('click', () => {
      if (this.state === 'play' && !this.input.pointerLocked && !this.touch.active) void this.input.requestPointerLock(true);
    });
  }

  private wireEvents(): void {
    bus.on('pointerlock', (locked: boolean) => {
      if (!locked && this.state === 'play' && !this.input.dragLook) this.pause();
    });
    bus.on('sfx', (e: { kind: string; x?: number; y?: number; z?: number; speed?: number; crouch?: boolean; heavy?: boolean; strength?: number }) => {
      this.audio.play(e.kind, e);
    });
    bus.on('fell', () => this.player.teleport(this.refs.startPos.x, DECK_Y.crew, 5, 0));
  }

  private openSettings(from: 'title' | 'paused'): void {
    this.returnTo = from;
    $('settings').dispatchEvent(new Event('fill'));
    this.hud.show('title', false);
    this.hud.show('pause', false);
    this.hud.show('settings', true);
  }

  private openControls(from: 'title' | 'paused'): void {
    this.returnTo = from;
    this.hud.show('title', false);
    this.hud.show('pause', false);
    this.hud.show('controls', true);
  }

  // ------------------------------------------------------------------ flow

  private toTitle(): void {
    this.state = 'title';
    this.input.exitPointerLock();
    this.audio.stopSignal();
    this.hud.clearSubs();
    ['hud', 'pause', 'reader', 'settings', 'controls', 'loading'].forEach((id) => this.hud.show(id, false));
    this.touch.show(false);
    const save = this.hotSave ?? loadSave();
    $('btn-continue').hidden = !save;
    $('btn-new').textContent = save ? 'New game' : 'Wake up';
    $('btn-new').classList.toggle('primary', !save);
    $('btn-continue').classList.toggle('primary', !!save);
    this.hud.show('title', true);
    void this.hud.fade(0, 1200);
    if (this.audio.ctx) this.audio.setAmbience('hab');
  }

  private beginPlay(): void {
    this.audio.start();
    this.audio.setVolume(this.settings.volume);
    this.hud.show('title', false);
    this.hud.show('hud', true);
    this.touch.show(true);
    this.state = 'play';
    if (!this.touch.active) void this.input.requestPointerLock(true);
    this.room = null;
  }

  async newGame(): Promise<void> {
    clearSave();
    this.hotSave = null;
    this.flags = {};
    this.clock = new ShipClock();
    this.orbit.time = 0;
    await this.hud.fade(1, 400);
    this.beginPlay();
    const bunk = this.kit.seats.find((s) => s.id === this.refs.bedSeatId)!;
    this.player.teleport(bunk.exitX, DECK_Y.crew, bunk.exitZ, bunk.yaw);
    this.player.sitAt(bunk);
    this.player.update(1, this.input, false, false, false);
    this.state = 'busy';
    this.updateObjective();
    await wait(600);
    void this.hud.fade(0, 3200);
    this.audio.play('breath');
    await wait(2200);
    this.vesta('Good morning, Specialist. Ship time oh-six-forty, day two thousand two hundred and fourteen.');
    this.vesta('You were revived early. Your messages explain why. Please take your time; cryo legs are unreliable.');
    this.state = 'play';
  }

  async continueGame(): Promise<void> {
    const s = this.hotSave ?? loadSave();
    if (!s) return void this.newGame();
    await this.hud.fade(1, 400);
    this.beginPlay();
    this.flags = { ...s.flags };
    this.clock.minutes = s.shipMinutes;
    this.player.teleport(s.player.x, s.player.y, s.player.z, s.player.yaw, s.player.pitch);
    this.updateObjective();
    void this.hud.fade(0, 1200);
    this.hud.toast('Welcome back', this.clock.format());
  }

  private pause(): void {
    if (this.state !== 'play') return;
    this.state = 'paused';
    this.input.clear();
    $('pause-clock').textContent = `${this.clock.format()} · ${this.room?.name ?? 'CSV Meridian'}`;
    this.hud.show('pause', true);
    this.touch.show(false);
  }

  private resume(): void {
    this.hud.show('pause', false);
    this.touch.show(true);
    this.state = 'play';
    if (!this.touch.active) void this.input.requestPointerLock(true);
  }

  snapshot(): SaveData {
    const p = this.player;
    const seatY = p.seat ? p.seat.y - 0.5 : p.pos.y;
    return {
      version: 1,
      savedAt: Date.now(),
      shipMinutes: this.clock.minutes,
      player: {
        x: p.seat ? p.seat.exitX : p.pos.x,
        y: Math.round(seatY / 4) * 4 >= 0 ? this.floorBelow(p.seat ? p.seat.exitX : p.pos.x, seatY + 0.6, p.seat ? p.seat.exitZ : p.pos.z) : p.pos.y,
        z: p.seat ? p.seat.exitZ : p.pos.z,
        yaw: p.yaw,
        pitch: 0,
      },
      flags: { ...this.flags },
    };
  }

  private floorBelow(x: number, y: number, z: number): number {
    const g = this.world.groundAt(x, z, 0.2, y);
    return g > -Infinity ? g : y;
  }

  save(): void {
    if (this.state === 'title' || this.state === 'loading') return;
    writeSave(this.snapshot());
  }

  // ------------------------------------------------------------------ VESTA, objectives

  vesta(text: string): void {
    this.audio.play('vesta');
    this.hud.say('VESTA', text);
  }

  private updateObjective(): void {
    const next = OBJECTIVES.find((o) => !this.flags[`obj:${o.id}`]);
    this.hud.objective(next ? next.text : FREE_ROAM);
  }

  private complete(id: string): void {
    if (this.flags[`obj:${id}`]) return;
    this.flags[`obj:${id}`] = true;
    if (id !== 'getup') this.audio.play('success');
    this.updateObjective();
  }

  // ------------------------------------------------------------------ main loop

  private loop(): void {
    requestAnimationFrame(() => this.loop());
    const now = performance.now();
    const dt = Math.min(0.05, (now - this.last) / 1000);
    this.last = now;
    this.elapsed += dt;
    try {
      this.update(dt);
    } catch (err) {
      console.error(err);
    }
    this.input.endFrame();
  }

  private update(dt: number): void {
    this.simulate(dt);
    this.pipeline.render(this.elapsed);
  }

  /** Everything except drawing. Tests call this directly at a fixed step. */
  private simulate(dt: number): void {
    const st = this.state;
    if (st === 'title') this.titleCamera(dt);
    if (st === 'play' || st === 'busy' || st === 'scope' || st === 'reader') {
      if (st === 'play') this.clock.update(dt);
      const lying = this.player.mode === 'lying' && !!this.player.seat?.sleep;
      const canLook = st === 'play' || st === 'busy' || st === 'scope';
      const canMove = st === 'play';
      if (st === 'scope') this.updateScope(dt);
      else this.player.update(dt, this.input, canLook, canMove, !lying);
      if (st === 'play') this.handleInput(lying);
      for (const d of this.kit.doors) d.update(dt, this.player.pos.x, this.player.pos.y, this.player.pos.z);
      this.trackRoom();
    }
    if (st === 'play' && this.input.pressed('pause')) this.pause();
    if (this.shake > 0) {
      this.shake = Math.max(0, this.shake - dt);
      this.camera.position.y += Math.sin(this.elapsed * 31) * 0.006 + Math.sin(this.elapsed * 17) * 0.004;
    }
    // world animation
    this.orbit.update(dt, this.camera.position);
    this.updateLighting(dt);
    if (this.holo) {
      this.holo.rotation.y += dt * 0.25;
      (this.holo.parent!.children[2] as THREE.Mesh).rotation.z += dt * 0.6;
    }
    for (const m of this.interior.children) {
      if (m.name === 'mist') {
        const map = ((m as THREE.Mesh).material as THREE.MeshBasicMaterial).map!;
        map.offset.x += dt * (m.userData.speed as number);
      }
    }
    this.audio.setListener(this.camera.position, this.player?.yaw ?? 0);
    this.audio.update(dt);
    this.hud.update(dt * 1000);
  }

  private updateLighting(dt: number): void {
    const night = this.clock.nightFactor();
    this.mats.setShift(night);
    const tint = new THREE.Color(1, 1 - night * 0.12, 1 - night * 0.35);
    this.lights.update(dt, this.camera.position, 1 - night * 0.55, tint);
    const sunDir = this.orbit.sunDir;
    const c = this.camera.position;
    const snap = 0.5;
    this.sun.target.position.set(Math.round(c.x / snap) * snap, Math.round(c.y / snap) * snap, Math.round(c.z / snap) * snap);
    this.sun.position.copy(this.sun.target.position).addScaledVector(sunDir, 90);
    this.sun.intensity = 3.4 * this.orbit.sunVisible;
    this.hemi.position.copy(this.orbit.planetDir).negate();
    this.hemi.groundColor.setRGB(0.42, 0.5, 0.44).multiplyScalar(0.25 + this.orbit.litFraction * 0.75);
    this.hemi.intensity = 0.35;
  }

  private titleCamera(dt: number): void {
    this.elapsed += 0; // keep time from the main loop
    const t = this.elapsed * 0.03;
    this.camera.position.set(2.4 + Math.sin(t) * 0.5, DECK_Y.command + 1.5, 6.9);
    this.camera.rotation.order = 'YXZ';
    this.camera.rotation.set(-0.26 + Math.sin(t * 0.7) * 0.03, Math.PI + 0.42 + Math.sin(t * 0.8) * 0.08, 0);
    void dt;
  }

  private trackRoom(): void {
    const p = this.player.pos;
    const r = this.kit.roomAt(p.x, p.y + 0.5, p.z);
    if (!r || r === this.room) return;
    const prev = this.room;
    this.room = r;
    this.audio.setAmbience(r.ambience);
    if (r.ambience === 'lift') return;
    if (!prev || prev.name !== r.name) {
      const deckLabel: Record<string, string> = { command: 'Deck 1 · Command', crew: 'Deck 2 · Crew', science: 'Deck 3 · Science', spine: 'Spine', aft: 'Aft section' };
      this.hud.toast(r.name, `${deckLabel[r.deck] ?? ''} · ${this.clock.format()}`, DECK_COLORS[r.deck]);
    }
    const key = `v:${r.id}`;
    if (VESTA_ROOMS[r.id] && !this.flags[key] && this.state === 'play') {
      this.flags[key] = true;
      this.vesta(VESTA_ROOMS[r.id]);
    }
  }

  // ------------------------------------------------------------------ interaction

  private findTarget(): Item | null {
    const o = this.camera.position;
    const d = this.player.forward();
    let best: Item | null = null;
    let bestT = Infinity;
    for (const it of this.kit.items) {
      const range = it.range ?? 2.3;
      const t = rayBox(o.x, o.y, o.z, d.x, d.y, d.z, it.min[0], it.min[1], it.min[2], it.max[0], it.max[1], it.max[2]);
      if (t < 0 || t > range || t >= bestT) continue;
      best = it;
      bestT = t;
    }
    if (!best) return null;
    const wall = this.world.raycast(o.x, o.y, o.z, d.x, d.y, d.z, bestT, 'wall');
    if (wall < bestT - 0.06 && wall > 0.05) return null;
    return best;
  }

  private promptFor(it: Item): string {
    switch (it.action) {
      case 'music':
        return this.audio.musicPlaying ? 'Music player · stop' : 'Music player · play';
      case 'shower':
        return this.flags[`shower:${it.data}`] ? 'Turn off shower' : 'Turn on shower';
      case 'treadmill':
        return it.prompt;
      default:
        return it.prompt;
    }
  }

  private handleInput(lyingInBunk: boolean): void {
    if (this.input.pressed('light')) {
      const on = this.player.toggleFlashlight();
      this.audio.play('flashlight');
      if (on && !this.flags['tip:light']) {
        this.flags['tip:light'] = true;
        this.hud.notice('Suit flashlight. It matters more on the surface.', 2600);
      }
    }
    const p = this.player;
    if (p.mode === 'seated' || p.mode === 'lying') {
      this.target = null;
      if (lyingInBunk) {
        this.hud.prompt('Sleep until morning and save · Space to get up');
        if (this.input.pressed('use')) void this.sleep();
      } else this.hud.prompt('Stand up', 'Space');
      if (!this.flags['obj:getup'] && p.seat?.id === this.refs.bedSeatId && (this.input.pressed('jump') || this.input.axis().y !== 0)) {
        // handled by the player; mark complete next frame
      }
      return;
    }
    if (!this.flags['obj:getup']) this.complete('getup');
    this.target = this.findTarget();
    this.hud.prompt(this.target ? this.promptFor(this.target) : null);
    if (this.target && this.input.pressed('use')) this.use(this.target);
  }

  private use(it: Item): void {
    const center = { x: (it.min[0] + it.max[0]) / 2, y: (it.min[1] + it.max[1]) / 2, z: (it.min[2] + it.max[2]) / 2 };
    switch (it.action) {
      case 'seat':
        this.player.sitAt(it.data as Seat);
        break;
      case 'mail':
        this.openMail();
        break;
      case 'telescope':
        this.enterScope();
        break;
      case 'orbitalMap':
        this.openOrbitalMap();
        break;
      case 'kestrel':
        this.openKestrel();
        break;
      case 'mule':
        this.hud.notice('CL-01 MULE · heavy cargo lifter\nFour engines. Overpowered for hauling. Rated for orbit-to-ground drops.\nStatus: standby.', 4200);
        break;
      case 'signal':
        this.openSignal();
        break;
      case 'research':
        this.openResearch();
        break;
      case 'lift':
        void this.rideLift(it.data as string);
        break;
      case 'locked':
        this.audio.play('denied', center);
        this.hud.notice(String(it.data ?? it.prompt), 2800);
        break;
      case 'pod':
        this.audio.play('beep');
        this.hud.notice(String(it.data), 5200);
        break;
      case 'coffee':
        this.audio.play('coffee', center);
        this.hud.notice(this.flags.coffee ? 'Another cup. VESTA notes it, silently.' : 'Coffee. Real beans, seven years old. It is the best thing you have ever tasted.', 3200);
        this.flags.coffee = ((this.flags.coffee as number) || 0) + 1;
        break;
      case 'food':
        this.audio.play('dispense', center);
        this.hud.notice('Protein loaf. Flavour: "Harvest". It is beige.', 2800);
        break;
      case 'music': {
        const on = !this.audio.musicPlaying;
        this.audio.setMusic(on, center);
        this.hud.notice(on ? 'Now playing: "Long Dark, Low Sun" · Meridian library' : 'Music stopped.', 2400);
        break;
      }
      case 'shower': {
        const on = this.audio.toggleLoop(`shower:${it.data}`, 'shower', center);
        this.flags[`shower:${it.data}`] = on;
        break;
      }
      case 'plants':
        this.hud.notice('You check the seedlings. Wheat, chard, a stubborn tomato. Everything here was grown from the seed bank, for Haven.', 3800);
        break;
      case 'medscan':
        this.audio.play('beep');
        this.hud.notice('BIOMONITOR · SPECIALIST\nHR 64 · SpO₂ 98% · cryo recovery 94%\nNo pathogens detected.', 4000);
        break;
      case 'lab':
        this.audio.play('denied', center);
        this.hud.notice(`${it.data === 'microscope' ? 'Microscope' : 'Gene sequencer'}: no sample loaded.\nYou need something from the surface first.`, 3000);
        break;
      case 'decon':
        void this.runDecon(center);
        break;
      case 'flavor': {
        const key = String(it.data ?? '');
        if (key.startsWith('suit:')) {
          const name = key.slice(5);
          this.hud.notice(name === 'Specialist' ? 'Your EVA suit. Pressure-tested, filters full, helmet seals green.' : `${name}'s EVA suit. Pressure-tested.`, 3000);
        } else this.hud.notice(FLAVOR[key] ?? key, 3600);
        break;
      }
      default:
        this.hud.notice(it.prompt, 2000);
    }
  }

  // ------------------------------------------------------------------ actions

  private async sleep(): Promise<void> {
    this.state = 'busy';
    this.hud.prompt(null);
    this.audio.play('breath');
    await this.hud.fade(1, 1600);
    const hours = this.clock.sleepUntilMorning();
    this.orbit.time += hours * 3600 * 0.25 / 15;
    this.save();
    this.hud.notice(`Slept ${Math.round(hours)} hours. Game saved.`, 2400);
    await wait(1400);
    void this.hud.fade(0, 1800);
    await wait(800);
    this.vesta('Good morning. Nothing has changed on the surface. The signal is still playing.');
    this.state = 'play';
  }

  private async rideLift(target: string): Promise<void> {
    const decks = Object.entries(DECK_Y) as [string, number][];
    const here = decks.reduce((a, b) => (Math.abs(b[1] - this.player.pos.y) < Math.abs(a[1] - this.player.pos.y) ? b : a));
    if (here[0] === target) {
      this.audio.play('beep');
      return;
    }
    this.state = 'busy';
    this.hud.prompt(null);
    const from = this.kit.doorById.get(`lift-${here[0]}`)!;
    const to = this.kit.doorById.get(`lift-${target}`)!;
    from.override = 0;
    to.override = 0;
    this.audio.play('beep');
    for (let i = 0; i < 40 && !from.isClosed(); i++) await wait(50);
    this.audio.play('lift');
    this.shake = 2.3;
    await wait(2400);
    const dy = DECK_Y[target as keyof typeof DECK_Y] - here[1];
    this.player.shiftY(dy);
    from.override = null;
    to.override = null;
    this.room = null;
    this.state = 'play';
    if (!this.flags['v:lift']) {
      this.flags['v:lift'] = true;
      this.vesta('Lift. Please state your deck. Or press the button. I am not proud.');
    }
  }

  private async runDecon(pos: { x: number; y: number; z: number }): Promise<void> {
    this.state = 'busy';
    this.hud.prompt(null);
    this.audio.play('decon', pos);
    this.hud.notice('DECON CYCLE · UV · MIST · PURGE', 3600);
    this.shake = 0.4;
    await wait(3900);
    this.flags.decon = true;
    this.vesta(this.flags.deconOnce ? 'Cycle complete.' : 'Cycle complete. You were already clean. Protocol Seven thanks you anyway.');
    this.flags.deconOnce = true;
    this.state = 'play';
  }

  private enterScope(): void {
    this.state = 'scope';
    this.hud.prompt(null);
    this.scopeT = 0;
    this.scopeDone = !!this.flags['obj:telescope'];
    this.prevFov = this.camera.fov;
    const d = this.orbit.planetDir.clone().add(new THREE.Vector3(0.08, 0.16, 0)).normalize();
    this.player.yaw = Math.atan2(-d.x, -d.z);
    this.player.pitch = Math.asin(d.y);
    this.audio.play('scope');
    this.orbit.setDetail(1);
    this.hud.scope(true, this.scopeDone ? 'Free look. Press F or Space to step back.' : 'Acquiring the northern continent…', 0);
  }

  private updateScope(dt: number): void {
    const look = this.input.takeLook();
    const k = 0.0022 * this.settings.sensitivity * 0.12;
    this.player.yaw -= look.dx * k;
    this.player.pitch = THREE.MathUtils.clamp(this.player.pitch - look.dy * k, -1.3, 0.4);
    this.camera.rotation.set(this.player.pitch, this.player.yaw, 0);
    this.camera.fov += (6 - this.camera.fov) * Math.min(1, dt * 3);
    this.camera.updateProjectionMatrix();
    this.scopeT += dt;
    if (!this.scopeDone) {
      const lines = [
        'Acquiring the northern continent…',
        'Spectral survey: chlorophyll analogues, strong.\nGrassland, river deltas, dense forest.',
        'Thermal survey: no animal heat signatures.\nNone. Anywhere.',
        'Signal source triangulated · 61.2°N 14.8°E',
        'Landing zone marked: LZ-1 · THE SIGNAL FIELDS',
      ];
      const p = Math.min(1, this.scopeT / 6.5);
      const idx = Math.min(lines.length - 1, Math.floor(p * lines.length));
      if (Math.floor(this.scopeT * 2) !== Math.floor((this.scopeT - dt) * 2)) this.audio.play('beep');
      this.hud.scope(true, lines[idx], p);
      if (p >= 1) {
        this.scopeDone = true;
        this.flags.lz1 = true;
        this.complete('telescope');
        this.vesta('No animal heat. No birdsong on the long-range microphones. Grass, rivers and forest, and nothing living in them. I have marked the signal source as landing zone one. The crew is calling it the Signal Fields.');
        this.hud.scope(true, 'LZ-1 · THE SIGNAL FIELDS · marked\nFree look. Press F or Space to step back.', 1);
      }
    } else if (this.scopeT > 0.6 && (this.input.pressed('use') || this.input.pressed('jump'))) this.exitScope();
  }

  private exitScope(): void {
    this.hud.scope(false);
    this.orbit.setDetail(0);
    this.camera.fov = this.prevFov;
    this.camera.updateProjectionMatrix();
    this.state = 'play';
  }

  // ------------------------------------------------------------------ readers

  private openReader(title: string, body: HTMLElement | string, onClose?: () => void): HTMLElement {
    this.state = 'reader';
    this.hud.prompt(null);
    this.input.exitPointerLock();
    this.touch.show(false);
    return this.hud.openReader(title, body, onClose);
  }

  private closeReader(byClick: boolean): void {
    this.hud.closeReader();
    this.state = 'play';
    this.touch.show(true);
    if (!this.touch.active && !this.input.dragLook) {
      if (byClick) void this.input.requestPointerLock(true);
      else
        void this.input.requestPointerLock(false).then((ok) => {
          if (!ok) this.pause();
        });
    }
  }

  private openMail(): void {
    const root = document.createElement('div');
    root.className = 'mail';
    const list = document.createElement('div');
    list.className = 'mail-list';
    const view = document.createElement('article');
    view.className = 'mail-view';
    const show = (i: number) => {
      const m = MAIL[i];
      this.flags[`mail:${m.id}`] = true;
      list.querySelectorAll('.mail-item').forEach((el, j) => {
        el.classList.toggle('active', i === j);
        if (i === j) el.classList.remove('unread');
      });
      view.innerHTML = `<h3></h3><p class="meta"></p>${m.body.map(() => '<p></p>').join('')}`;
      view.querySelector('h3')!.textContent = m.subject;
      view.querySelector('.meta')!.textContent = `${m.from} · ${m.date}`;
      view.querySelectorAll('p:not(.meta)').forEach((p, j) => (p.textContent = m.body[j]));
      if (MAIL.every((mm) => this.flags[`mail:${mm.id}`])) this.complete('mail');
      else if (this.flags['mail:revival'] && this.flags['mail:captain']) this.complete('mail');
    };
    MAIL.forEach((m, i) => {
      const b = document.createElement('button');
      b.className = 'mail-item' + (this.flags[`mail:${m.id}`] ? '' : ' unread');
      b.innerHTML = '<b></b><span></span>';
      b.querySelector('b')!.textContent = m.subject;
      b.querySelector('span')!.textContent = m.from;
      b.addEventListener('click', () => {
        this.audio.play('ui');
        show(i);
      });
      list.appendChild(b);
    });
    root.append(list, view);
    this.openReader('Personal terminal · inbox', root);
    show(0);
  }

  private openOrbitalMap(): void {
    const root = document.createElement('div');
    const canvas = document.createElement('canvas');
    canvas.className = 'term-canvas';
    canvas.width = 960;
    canvas.height = 540;
    const c = canvas.getContext('2d')!;
    const cx = 330;
    const cy = 270;
    const R = 210;
    const g = c.createRadialGradient(cx - 60, cy - 70, 20, cx, cy, R);
    g.addColorStop(0, '#2f5a4c');
    g.addColorStop(0.7, '#14302a');
    g.addColorStop(1, '#071312');
    c.fillStyle = '#020707';
    c.fillRect(0, 0, 960, 540);
    c.fillStyle = g;
    c.beginPath();
    c.arc(cx, cy, R, 0, Math.PI * 2);
    c.fill();
    c.strokeStyle = 'rgba(143,227,210,0.22)';
    for (let i = -3; i <= 3; i++) {
      c.beginPath();
      c.ellipse(cx, cy + i * 52, Math.sqrt(Math.max(0, R * R - (i * 52) ** 2)), 9, 0, 0, Math.PI * 2);
      c.stroke();
      c.beginPath();
      c.ellipse(cx, cy, Math.abs(i) * 60 + 2, R, 0, 0, Math.PI * 2);
      c.stroke();
    }
    c.strokeStyle = '#e8a23a';
    c.lineWidth = 2;
    c.beginPath();
    c.ellipse(cx, cy, R + 40, 90, -0.42, 0, Math.PI * 2);
    c.stroke();
    const shipA = (this.orbit.time / (40 * 60)) * Math.PI * 2;
    c.fillStyle = '#ffd080';
    c.beginPath();
    c.arc(cx + Math.cos(shipA) * (R + 40) * Math.cos(-0.42) - Math.sin(shipA) * 90 * Math.sin(-0.42), cy + Math.cos(shipA) * (R + 40) * Math.sin(-0.42) + Math.sin(shipA) * 90 * Math.cos(-0.42), 6, 0, Math.PI * 2);
    c.fill();
    const sx = cx + 40;
    const sy = cy - 140;
    c.strokeStyle = '#e2603f';
    c.lineWidth = 2;
    for (let r = 8; r <= 26; r += 9) {
      c.beginPath();
      c.arc(sx, sy, r, 0, Math.PI * 2);
      c.stroke();
    }
    c.fillStyle = '#e6e8e3';
    c.font = '500 15px "IBM Plex Mono", monospace';
    c.fillText('SIGNAL · 61.2°N 14.8°E', sx + 32, sy - 6);
    if (this.flags.lz1) {
      c.fillStyle = '#8fe3d2';
      c.fillRect(sx - 4, sy + 30, 8, 8);
      c.fillText('LZ-1 · THE SIGNAL FIELDS', sx + 32, sy + 40);
    } else {
      c.fillStyle = 'rgba(230,232,227,0.5)';
      c.fillText('Landing zones: survey pending (telescope)', sx + 32, sy + 40);
    }
    c.fillStyle = '#ffd080';
    c.fillText('CSV MERIDIAN', 700, 470);
    root.appendChild(canvas);
    const grid = document.createElement('div');
    grid.className = 'data-grid';
    for (const [k, v] of PLANET_FACTS) {
      const d = document.createElement('div');
      d.innerHTML = '<span></span><strong></strong>';
      d.querySelector('span')!.textContent = k;
      d.querySelector('strong')!.textContent = v;
      grid.appendChild(d);
    }
    root.appendChild(grid);
    const note = document.createElement('p');
    note.className = this.flags.lz1 ? 'teal' : 'warn';
    note.textContent = this.flags.lz1
      ? 'LZ-1 is plotted. Pre-flight continues in the hangar.'
      : 'No landing zone yet. Survey the surface with the telescope in the observation dome first.';
    root.appendChild(note);
    this.openReader('Orbital map · KX-7c', root);
    this.complete('orbitalMap');
  }

  private openKestrel(): void {
    const ready = !!this.flags.lz1;
    const html = `
      <div class="data-grid">
        <div><span>Craft</span><strong>LND-01 Kestrel</strong></div>
        <div><span>Fuel</span><strong>100%</strong></div>
        <div><span>Cradle</span><strong>Locked</strong></div>
        <div><span>Hull</span><strong>Nominal</strong></div>
        <div><span>Crew</span><strong>0 / 4</strong></div>
        <div><span>Destination</span><strong>${ready ? 'LZ-1 · Signal Fields' : 'None plotted'}</strong></div>
      </div>
      <p>Pilot's note, H. Brandt: <span class="teal">"Pre-flight at 1800. If anyone touches my seat settings I will know."</span></p>
      <p class="warn">Build note: flying the Kestrel down to the surface and back arrives in Milestone 2, "Between ships".</p>`;
    this.openReader('Kestrel · pre-flight status', html);
    this.complete('kestrel');
  }

  private openSignal(): void {
    const html = `
      <p class="meta">COMMS · LIVE · KX-7c SURFACE · 61.2°N 14.8°E</p>
      <p>A woman is humming. The melody is slow and simple, the kind you'd sing to a child at night.</p>
      <p>Every repeat is a little different, as if she is still learning it.</p>
      <p class="warn">Carrier: unknown. No human transmitter on record matches it. Thirty-one hours, without a breath.</p>
      <p class="meta">Close the terminal to stop listening.</p>`;
    this.audio.stopSignal();
    this.audio.startSignal();
    this.flags.heardSignal = true;
    this.openReader('Signal monitor · live', html, () => this.audio.stopSignal());
  }

  private openResearch(): void {
    const html = `
      <p>Research projects run on samples brought back from the surface. Results arrive overnight while you sleep.</p>
      <div class="tree">
        <section><h4>Xenobiology</h4><ul><li>Spore morphology</li><li>Filter efficiency</li><li>Antifungal injector</li></ul></section>
        <section><h4>Xenoarchaeology</h4><ul><li>Glyph rubbings</li><li>Translation key</li><li>New landing sites</li></ul></section>
        <section><h4>Signals</h4><ul><li>Carrier analysis</li><li>Bio-sonar noise filter</li><li>Source triangulation</li></ul></section>
        <section><h4>Engineering</h4><ul><li>Scanner range</li><li>Suit plating</li><li>Weapon mods</li></ul></section>
      </div>
      <p class="warn" style="margin-top:14px">Queue empty · no samples in containment.</p>`;
    this.openReader('Research terminal', html);
  }

  // ------------------------------------------------------------------ debug

  private debugApi() {
    return {
      game: this,
      teleport: (x: number, y: number, z: number, yaw = 0, pitch = 0) => {
        this.player.teleport(x, y, z, yaw, pitch);
        this.room = null;
      },
      look: (yaw: number, pitch: number) => {
        this.player.yaw = yaw;
        this.player.pitch = pitch;
      },
      setTime: (hour: number) => {
        this.clock.minutes = this.clock.day * 1440 + hour * 60;
      },
      setOrbit: (seconds: number) => {
        this.orbit.time = seconds;
      },
      startPlay: () => {
        this.beginPlay();
        this.hud.fade(0, 10);
      },
      state: () => this.state,
      step: (seconds: number) => {
        const n = Math.max(1, Math.round(seconds * 30));
        for (let i = 0; i < n; i++) {
          this.elapsed += 1 / 30;
          this.simulate(1 / 30);
          this.input.endFrame();
        }
      },
      aim: (x: number, y: number, z: number) => {
        const c = this.camera.position;
        const dx = x - c.x;
        const dy = y - c.y;
        const dz = z - c.z;
        this.player.yaw = Math.atan2(-dx, -dz);
        this.player.pitch = Math.atan2(dy, Math.hypot(dx, dz));
      },
      prompt: () => (document.getElementById('prompt')!.hidden ? null : document.getElementById('prompt-text')!.textContent),
      flags: () => ({ ...this.flags }),
      mode: () => this.player.mode,
      door: (i: number) => this.kit.doors[i].open,
      doorAt: (x: number, z: number) => {
        let best = this.kit.doors[0];
        for (const d of this.kit.doors) if (Math.hypot(d.o.x - x, d.o.z - z) < Math.hypot(best.o.x - x, best.o.z - z)) best = d;
        return { open: best.open, x: best.o.x, z: best.o.z, locked: best.locked };
      },
      sitBunk: () => {
        const bunk = this.kit.seats.find((s) => s.id === this.refs.bedSeatId)!;
        this.player.sitAt(bunk);
      },
      clock: () => this.clock.format(),
      info: () => ({
        pos: this.player.pos.toArray(),
        room: this.room?.id,
        items: this.kit.items.length,
        seats: this.kit.seats.length,
        doors: this.kit.doors.length,
        boxes: this.world.boxes.length,
        calls: this.renderer.info.render.calls,
        tris: this.renderer.info.render.triangles,
      }),
    };
  }
}

const game = new Game();
void game.boot().catch((err) => {
  console.error(err);
  const el = document.getElementById('loading-text');
  if (el) el.textContent = `Something went wrong while loading: ${String(err?.message ?? err)}`;
});
