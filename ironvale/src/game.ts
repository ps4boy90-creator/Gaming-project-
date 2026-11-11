import * as THREE from 'three';
import { Sim } from './sim/sim';
import { World } from './world/world';
import { Gfx, type Quality } from './render/gfx';
import { Terrain } from './render/terrain';
import { WallRenderer } from './render/walls';
import { ObjectRenderer } from './render/objects';
import { CharacterRenderer } from './render/characters';
import { Overlays } from './render/overlays';
import { Traffic } from './render/traffic';
import { renderThumbnails } from './render/thumbs';
import { buildEmptyPlot, buildStarterPrison } from './world/starter';
import { Input } from './input';
import { UI } from './ui/ui';
import { sfx } from './core/sfx';
import { resetAgentIds, type Agent } from './sim/agent';
import { MAP_H, MAP_W } from './data/defs';

export type Tool =
  | { kind: 'select' }
  | { kind: 'foundation' }
  | { kind: 'wall'; id: number }
  | { kind: 'door'; id: number }
  | { kind: 'floor'; id: number }
  | { kind: 'zone'; id: number }
  | { kind: 'object'; id: string }
  | { kind: 'bulldoze' }
  | { kind: 'station'; guard: number };

export type Selection = { kind: 'agent'; id: number } | { kind: 'object'; id: number } | { kind: 'room'; tile: number } | null;

const SAVE_KEY = 'ironvale-save-v1';

export class Game {
  world = new World();
  sim: Sim;
  gfx: Gfx;
  terrain: Terrain;
  walls: WallRenderer;
  objects: ObjectRenderer;
  chars: CharacterRenderer;
  overlays: Overlays;
  traffic: Traffic;
  input: Input;
  ui: UI;
  thumbs: Record<string, string> = {};
  tool: Tool = { kind: 'select' };
  selection: Selection = null;
  follow = false;
  /** true while the title screen is up: the sim runs as a backdrop */
  inMenu = true;
  showZones = false;
  private last = performance.now();
  private fpsAcc = 0;
  private fpsN = 0;
  fps = 60;
  private slowFor = 0;
  autoQuality = true;

  constructor(canvas: HTMLCanvasElement) {
    this.gfx = new Gfx(canvas);
    this.sim = new Sim(this.world);
    this.terrain = new Terrain(this.gfx, this.world);
    this.walls = new WallRenderer(this.gfx, this.world);
    this.objects = new ObjectRenderer(this.gfx, this.world);
    this.objects.warm();
    this.chars = new CharacterRenderer(this.gfx);
    this.overlays = new Overlays(this.gfx, this.world);
    this.traffic = new Traffic(this.gfx, this.terrain.solidMat, this.objects.glowMat);
    this.thumbs = renderThumbnails((id) => this.objects.model(id));
    this.input = new Input(this);
    this.ui = new UI(this);
    // title backdrop: a living starter prison
    this.newSim('starter');
    this.gfx.target.set(MAP_W / 2 - 1, 0, MAP_H / 2 + 3);
    this.gfx.zoom = this.gfx.zoomTarget = 46;
    requestAnimationFrame((t) => this.frame(t));
  }

  private wire() {
    const s = this.sim;
    s.bus.on('toast', (e) => this.ui.toast(e));
    s.bus.on('bus', (e) => this.traffic.callBus(s.time, e.eta, e.count));
    s.bus.on('day', () => { if (!this.inMenu) this.save(true); });
    s.bus.on('riot', (on) => { if (on) sfx.alarm(); });
    s.bus.on('objective', () => sfx.good());
  }

  private newSim(mode: 'starter' | 'empty') {
    resetAgentIds(1);
    this.world.reset();
    this.sim = new Sim(this.world);
    if (mode === 'starter') buildStarterPrison(this.sim);
    else buildEmptyPlot(this.sim);
    this.wire();
    this.selection = null;
    this.chars.selectedId = 0;
  }

  /** leave the title screen and begin playing */
  start(mode: 'starter' | 'empty' | 'continue') {
    if (mode === 'continue') {
      if (!this.load()) {
        this.ui.toast({ t: 0, text: 'Could not load the saved prison.', kind: 'bad' });
        return;
      }
    } else this.newSim(mode);
    this.inMenu = false;
    this.setTool({ kind: 'select' });
    if (mode === 'empty') {
      this.gfx.target.set(MAP_W / 2, 0, MAP_H - 16);
      this.gfx.zoomTarget = 40;
    } else if (mode === 'starter') {
      this.gfx.target.set(MAP_W / 2, 0, MAP_H / 2 + 2);
      this.gfx.zoomTarget = 40;
    }
    this.ui.onStart(mode);
  }

  setTool(t: Tool) {
    this.tool = t;
    this.input.onToolChange();
    this.ui.onToolChange();
  }
  select(sel: Selection) {
    this.selection = sel;
    this.chars.selectedId = sel && sel.kind === 'agent' ? sel.id : 0;
    if (!sel || sel.kind !== 'agent') this.follow = false;
    this.ui.onSelection();
  }
  selectedAgent(): Agent | null {
    const s = this.selection;
    if (!s || s.kind !== 'agent') return null;
    return this.sim.byId.get(s.id) ?? null;
  }
  focus(x: number, z: number) {
    this.gfx.target.set(x, 0, z);
    if (this.gfx.zoomTarget > 30) this.gfx.zoomTarget = 26;
  }

  setQuality(q: Quality, manual = true) {
    if (manual) this.autoQuality = false;
    this.gfx.setQuality(q);
  }

  // ------------------------------------------------------------ persistence
  hasSave(): boolean {
    try {
      return !!localStorage.getItem(SAVE_KEY);
    } catch {
      return false;
    }
  }
  save(auto = false): boolean {
    try {
      localStorage.setItem(SAVE_KEY, JSON.stringify(this.sim.serialize()));
      if (!auto) this.ui.toast({ t: 0, text: 'Prison saved.', kind: 'good' });
      return true;
    } catch {
      if (!auto) this.ui.toast({ t: 0, text: 'Saving is not available in this browser window.', kind: 'bad' });
      return false;
    }
  }
  load(): boolean {
    try {
      const raw = localStorage.getItem(SAVE_KEY);
      if (!raw) return false;
      const d = JSON.parse(raw);
      const sim = Sim.load(d, this.world);
      if (!sim) return false;
      this.sim = sim;
      this.wire();
      this.selection = null;
      this.chars.selectedId = 0;
      return true;
    } catch (e) {
      console.warn(e);
      return false;
    }
  }

  // ------------------------------------------------------------ main loop
  private frame(now: number) {
    requestAnimationFrame((t) => this.frame(t));
    const dt = Math.min(0.1, (now - this.last) / 1000);
    this.last = now;
    const sim = this.sim, w = this.world;

    this.input.update(dt);
    sim.update(dt);
    sim.sync();

    // doors swing open for anyone at or about to enter them
    const hot = this.walls.doorHot;
    for (const a of sim.agents) {
      hot[sim.tileOf(a)] = 1;
      if (a.path && a.pathI < a.path.length) hot[a.path[a.pathI]] = 1;
    }

    if (this.inMenu) {
      // slow orbiting drift behind the title
      const t = now / 1000;
      this.gfx.target.x = MAP_W / 2 - 1 + Math.sin(t * 0.05) * 6;
      this.gfx.target.z = MAP_H / 2 + 3 + Math.cos(t * 0.04) * 4;
    } else if (this.follow) {
      const a = this.selectedAgent();
      if (a) {
        const k = 1 - Math.exp(-dt * 6);
        this.gfx.target.x += (a.x - this.gfx.target.x) * k;
        this.gfx.target.z += (a.z - this.gfx.target.z) * k;
      } else this.follow = false;
    }

    this.terrain.update();
    this.walls.update(dt);
    this.objects.update();
    const buildMode = this.tool.kind !== 'select' && this.tool.kind !== 'station';
    this.overlays.showGrid = buildMode;
    this.overlays.showZones = this.showZones || this.tool.kind === 'zone' || this.tool.kind === 'station';
    this.overlays.update(this.objects.lights, this.objects.lightsVersion, this.terrain.streetLights, sim.planVersion);
    const animDt = sim.paused ? 0 : dt * Math.min(sim.speed, 2.5);
    this.chars.update(sim.agents, animDt, now / 1000);
    this.traffic.update(sim.paused ? 0 : dt * Math.min(sim.speed, 3), sim.time, sim.paused);
    this.gfx.setTimeOfDay(sim.hourF);
    this.gfx.render(dt);
    this.ui.update(dt);

    // adaptive quality: step down if the frame rate stays poor
    this.fpsAcc += dt;
    this.fpsN++;
    if (this.fpsAcc >= 1) {
      this.fps = this.fpsN / this.fpsAcc;
      this.fpsAcc = 0;
      this.fpsN = 0;
      if (this.autoQuality && document.visibilityState === 'visible') {
        this.slowFor = this.fps < 24 ? this.slowFor + 1 : 0;
        if (this.slowFor >= 4 && this.gfx.quality !== 'low') {
          this.slowFor = 0;
          this.gfx.setQuality(this.gfx.quality === 'high' ? 'medium' : 'low');
          this.ui.refreshSettings();
        }
      }
    }
    void w;
    void THREE;
  }
}
