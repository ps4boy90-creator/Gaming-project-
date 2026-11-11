import {
  ACTS, ACT_COLOR, ACT_LABEL, DEFAULT_REGIME, DOORS, FLOORS, NEEDS, NEED_LABEL, OBJ, OBJECTS, OBJ_CATS, ROOMS, SEC_NAME, STAFF,
  STAFF_BY_ROLE, WALLS, type Activity, type ObjCat, type StaffRole,
} from '../data/defs';
import { fmtMoney, fmtTime } from '../core/util';
import { isMuted, setMuted, sfx } from '../core/sfx';
import { INTAKE_NAME, type LogEntry } from '../sim/sim';
import type { Agent } from '../sim/agent';
import type { Game } from '../game';

const IC: Record<string, string> = {
  select: '<path d="M5 3l14 8-6 2-2 6z"/>',
  foundation: '<path d="M3 20h18M5 20V9l7-5 7 5v11M10 20v-6h4v6"/>',
  wall: '<path d="M3 6h18v12H3zM3 12h18M9 6v6M15 12v6"/>',
  door: '<path d="M6 21V4h12v17M4 21h16"/><circle cx="14.5" cy="13" r="0.8"/>',
  floor: '<path d="M3 9l9-5 9 5-9 5zM3 14l9 5 9-5"/>',
  rooms: '<path d="M4 4h16v16H4zM4 12h8v8M12 4v4"/>',
  objects: '<path d="M4 12h16v4H4zM6 16v4M18 16v4M6 12V7a2 2 0 012-2h8a2 2 0 012 2v5"/>',
  staff: '<circle cx="12" cy="7.5" r="3.5"/><path d="M5 21c0-4 3-7 7-7s7 3 7 7"/>',
  bulldoze: '<path d="M4 20h16M6 20l2-12h8l2 12M9 4h6M12 4v4"/>',
  alert: '<path d="M12 3l10 18H2zM12 10v5M12 18v.5"/>',
  reports: '<path d="M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-6"/>',
  regime: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  money: '<circle cx="12" cy="12" r="9"/><path d="M15 9c-.5-1.2-1.6-2-3-2-1.7 0-3 1-3 2.5 0 3.2 6 1.8 6 5 0 1.500-1.300 2.500-3 2.500-1.500 0-2.700-.800-3.200-2M12 5v14"/>',
  inmate: '<circle cx="12" cy="7.5" r="3.5"/><path d="M5 21c0-4 3-7 7-7s7 3 7 7M8 16l8 3M8 19l6-4"/>',
  star: '<path d="M12 3l2.700 5.800 6.300.800-4.600 4.400 1.200 6.300L12 17.300 6.400 20.300l1.200-6.300L3 9.600l6.300-.800z"/>',
  shield: '<path d="M12 3l8 3v6c0 5-3.500 8-8 9-4.500-1-8-4-8-9V6z"/>',
  pause: '<path d="M8 5v14M16 5v14"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  rotl: '<path d="M4 12a8 8 0 108-8H7M7 4L4 7l3 3"/>',
  rotr: '<path d="M20 12a8 8 0 11-8-8h5M17 4l3 3-3 3"/>',
};
const ic = (k: string) => `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${IC[k] ?? ''}</svg>`;
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!));
const pct = (v: number) => Math.round(Math.max(0, Math.min(1, v)) * 100);
const heat = (v: number) => (v < 0.4 ? 'var(--good)' : v < 0.7 ? 'var(--warn)' : 'var(--bad)');
const cool = (v: number) => (v > 0.6 ? 'var(--good)' : v > 0.3 ? 'var(--warn)' : 'var(--bad)');
const hex = (n: number) => '#' + n.toString(16).padStart(6, '0');

type Cat = 'select' | 'foundation' | 'walls' | 'doors' | 'floors' | 'rooms' | 'objects' | 'staff' | 'bulldoze' | 'emergency';
const CATS: { id: Cat; name: string; icon: string; hint: string }[] = [
  { id: 'select', name: 'Select', icon: 'select', hint: 'Click people, objects and rooms to inspect them. Drag to move the camera.' },
  { id: 'foundation', name: 'Building', icon: 'foundation', hint: 'Drag a rectangle to lay out concrete walls and floor in one go.' },
  { id: 'walls', name: 'Walls', icon: 'wall', hint: 'Drag to draw a straight run of wall or fence.' },
  { id: 'doors', name: 'Doors', icon: 'door', hint: 'Click a wall tile to fit a door. Inmates cannot pass Staff Doors or Gates.' },
  { id: 'floors', name: 'Floors', icon: 'floor', hint: 'Drag a rectangle to lay flooring.' },
  { id: 'rooms', name: 'Rooms', icon: 'rooms', hint: 'Drag over floor to tell everyone what a room is for. Red labels list what is missing.' },
  { id: 'objects', name: 'Objects', icon: 'objects', hint: 'Click to place. R rotates. Right-click or Esc to stop.' },
  { id: 'staff', name: 'Staff', icon: 'staff', hint: 'Click a role to hire. Wages are paid every midnight.' },
  { id: 'bulldoze', name: 'Demolish', icon: 'bulldoze', hint: 'Drag over walls, doors and objects to remove them. Plans are refunded in full.' },
  { id: 'emergency', name: 'Control', icon: 'alert', hint: 'Emergency orders and the intake rate.' },
];

export class UI {
  private root: HTMLElement;
  private hud!: HTMLElement;
  private left!: HTMLElement;
  private toasts!: HTMLElement;
  private tracker!: HTMLElement;
  private insp!: HTMLElement;
  private dock!: HTMLElement;
  private palette!: HTMLElement;
  private toolbar!: HTMLElement;
  private hint!: HTMLElement;
  private cost!: HTMLElement;
  private modal!: HTMLElement;
  private menu!: HTMLElement;
  private banner!: HTMLElement;
  private cat: Cat = 'select';
  private objCat: ObjCat = 'housing';
  private modalTab: string | null = null;
  private brush: Activity = 'free';
  private acc = 0;
  private slow = 0;
  private swatches: Record<string, string> = {};
  private hoverHint = '';

  constructor(private game: Game) {
    this.root = document.getElementById('ui')!;
    for (const f of FLOORS) this.swatches[f.key] = game.terrain.floorSwatch(f.key);
    this.root.innerHTML = `
      <header id="hud"></header>
      <div id="left"><div id="tracker" class="glass" hidden></div><div id="toasts"></div></div>
      <div id="banner" hidden></div>
      <aside id="inspector" class="glass" hidden></aside>
      <div id="dock"><div id="hint"></div><div id="palette" class="glass" hidden></div><nav id="toolbar" class="glass"></nav></div>
      <div id="costtag" hidden></div>
      <div id="modal" hidden></div>
      <div id="menu"></div>`;
    const q = (id: string) => this.root.querySelector('#' + id) as HTMLElement;
    this.hud = q('hud'); this.left = q('left'); this.toasts = q('toasts'); this.tracker = q('tracker'); this.insp = q('inspector');
    this.dock = q('dock'); this.palette = q('palette'); this.toolbar = q('toolbar'); this.hint = q('hint'); this.cost = q('costtag');
    this.modal = q('modal'); this.menu = q('menu'); this.banner = q('banner');
    this.root.addEventListener('click', (e) => this.onClick(e));
    this.root.addEventListener('pointerover', (e) => {
      const t = (e.target as HTMLElement).closest('[data-hint]') as HTMLElement | null;
      this.hoverHint = t ? t.dataset.hint! : '';
      this.renderHint();
    });
    this.modal.addEventListener('pointerdown', (e) => { if (e.target === this.modal) this.closeModal(); });
    this.buildHud();
    this.buildToolbar();
    this.buildMenu();
    this.setPlaying(false);
  }

  private setPlaying(on: boolean) {
    this.hud.hidden = !on;
    this.left.hidden = !on;
    this.dock.hidden = !on;
    this.menu.hidden = on;
    if (!on) {
      this.insp.hidden = true;
      this.banner.hidden = true;
    }
  }

  // ================================================================== title screen
  private buildMenu() {
    const cont = this.game.hasSave();
    this.menu.innerHTML = `<div class="inner">
      <div class="num">State Correctional Facility No. 0417</div>
      <h1>IRONVALE</h1>
      <div class="strap">Prison Simulator</div>
      <p>Design the blocks, hire the staff, set the daily regime and keep several dozen unhappy people fed, safe and inside the fence.</p>
      <div class="opts">
        ${cont ? '<button class="opt pri" data-act="start" data-arg="continue"><b>Continue</b><span>Pick up your saved prison</span></button>' : ''}
        <button class="opt ${cont ? '' : 'pri'}" data-act="start" data-arg="starter"><b>Starter prison</b><span>A small working jail with staff and nine inmates</span></button>
        <button class="opt" data-act="start" data-arg="empty"><b>Empty plot</b><span>$80,000, four workmen and a field</span></button>
        <button class="opt" data-act="modal" data-arg="help"><b>How to play</b><span>Controls and first steps</span></button>
      </div>
    </div>`;
  }

  onStart(mode: string) {
    this.setPlaying(true);
    this.cat = 'select';
    this.buildToolbar();
    this.renderPalette();
    this.toasts.innerHTML = '';
    this.onSelection();
    if (mode === 'empty') {
      this.game.sim.toast('Welcome, Warden. Start with a Building, add Doors, mark Rooms, then furnish them. Grants on the left show what to do next.', 'info');
    } else if (mode === 'starter') {
      this.game.sim.toast('Welcome, Warden. This prison is yours now. Click anyone to see how they are doing, and check Reports for the full picture.', 'info');
    }
  }

  // ================================================================== HUD
  private buildHud() {
    this.hud.innerHTML = `
      <div class="glass brand"><b>IRONVALE</b><span>Correctional</span></div>
      <div class="glass chips">
        <button class="chip" data-act="modal" data-arg="finance" data-hint="Cash in hand and today's running balance. Click for the ledger.">${ic('money')}<div><div class="k">Funds</div><div class="v" id="h-money"></div></div></button>
        <button class="chip" data-act="modal" data-arg="inmates" data-hint="Inmates held and bed capacity. Click for the roster.">${ic('inmate')}<div><div class="k">Inmates</div><div class="v" id="h-pop"></div></div></button>
        <button class="chip opt" data-act="modal" data-arg="staff" data-hint="Staff on the payroll.">${ic('staff')}<div><div class="k">Staff</div><div class="v" id="h-staff"></div></div></button>
        <button class="chip" data-act="modal" data-arg="overview" data-hint="Overall prison rating out of 100.">${ic('star')}<div><div class="k">Rating</div><div class="v" id="h-rating"></div></div></button>
        <button class="chip opt" data-act="modal" data-arg="overview" data-hint="Danger rises with fights and too few guards.">${ic('shield')}<div><div class="k">Danger</div><div class="meter"><i id="h-danger"></i></div></div></button>
      </div>
      <div class="spacer"></div>
      <div class="glass clock">
        <div><div class="day" id="h-day"></div><div class="time" id="h-time"></div></div>
        <button class="act" id="h-act" data-act="modal" data-arg="regime" data-hint="What the regime says inmates should be doing now. Click to edit the timetable."></button>
        <div class="speed">
          <button data-act="speed" data-arg="0" data-hint="Pause (Space)" aria-label="Pause">${ic('pause')}</button>
          <button data-act="speed" data-arg="1" data-hint="Normal speed (1)">1x</button>
          <button data-act="speed" data-arg="2" data-hint="Fast (2)">2x</button>
          <button data-act="speed" data-arg="5" data-hint="Very fast (3)">5x</button>
        </div>
      </div>
      <div class="glass chips side">
        <button class="chip icn" data-act="rot" data-arg="-1" data-hint="Rotate the camera (Q)" aria-label="Rotate left">${ic('rotl')}</button>
        <button class="chip icn" data-act="rot" data-arg="1" data-hint="Rotate the camera (E)" aria-label="Rotate right">${ic('rotr')}</button>
        <button class="chip icn" data-act="zones" id="h-zones" data-hint="Show or hide room colours and labels (Tab)" aria-label="Room overlay">${ic('eye')}</button>
        <button class="chip icn" data-act="modal" data-arg="overview" data-hint="Reports, grants, regime, finance and settings" aria-label="Reports">${ic('reports')}</button>
        <button class="chip icn" data-act="modal" data-arg="settings" data-hint="Save, load and settings" aria-label="Menu">${ic('menu')}</button>
      </div>`;
  }

  private el(id: string) {
    return document.getElementById(id)!;
  }

  private updateHud() {
    const s = this.game.sim;
    const net = Object.values(s.ledgerToday).reduce((a, b) => a + b, 0);
    this.el('h-money').innerHTML = `${fmtMoney(s.money)} <small class="${net >= 0 ? 'pos' : 'neg'}">${net >= 0 ? '+' : ''}${fmtMoney(net)}</small>`;
    this.el('h-pop').innerHTML = `${s.prisoners.length} <small>/ ${s.counts.capacity} beds</small>`;
    this.el('h-staff').textContent = String(s.staff.filter((a) => a.s!.role !== 'riot').length);
    const r = s.rating();
    this.el('h-rating').innerHTML = s.prisoners.length ? `${Math.round(r.overall)}<small> / 100</small>` : '<small>no inmates</small>';
    const d = this.el('h-danger');
    d.style.width = pct(s.danger) + '%';
    d.style.background = heat(s.danger);
    this.el('h-day').textContent = `Day ${s.day}`;
    this.el('h-time').textContent = fmtTime(s.time);
    const act = s.activity, a = this.el('h-act');
    a.textContent = s.lockdown ? 'Lockdown' : s.time < s.shakedownUntil ? 'Shakedown' : ACT_LABEL[act];
    a.style.background = ACT_COLOR[act];
    const cur = s.paused ? 0 : s.speed;
    this.hud.querySelectorAll('.speed button').forEach((b) => b.classList.toggle('on', +(b as HTMLElement).dataset.arg! === cur));
    this.el('h-zones').classList.toggle('on', this.game.showZones);
    (this.el('h-zones') as HTMLElement).style.color = this.game.showZones ? 'var(--accent)' : '';
    // banner
    if (s.riot) {
      this.banner.hidden = false;
      this.banner.className = '';
      this.banner.textContent = 'RIOT IN PROGRESS';
    } else if (s.lockdown) {
      this.banner.hidden = false;
      this.banner.className = 'lock';
      this.banner.textContent = 'LOCKDOWN';
    } else this.banner.hidden = true;
    // grant tracker
    const next = s.objectives.filter((o) => !s.objectivesDone.has(o.id)).slice(0, 2);
    if (next.length) {
      this.tracker.hidden = false;
      const html = `<h4><span>Next grants</span><span>${s.objectivesDone.size} / ${s.objectives.length}</span></h4>` +
        next.map((o) => `<div class="g" data-act="modal" data-arg="grants"><span><b>${esc(o.title)}</b> ${esc(o.desc)}</span><em>${fmtMoney(o.reward)}</em></div>`).join('');
      if (this.tracker.dataset.h !== html) {
        this.tracker.dataset.h = html;
        this.tracker.innerHTML = html;
      }
    } else this.tracker.hidden = true;
  }

  // ================================================================== toolbar + palette
  private buildToolbar() {
    this.toolbar.innerHTML = CATS.map((c, i) =>
      `${i === 1 || i === 8 || i === 9 ? '<span class="sep"></span>' : ''}<button class="tb ${c.id === 'emergency' ? 'alert' : ''} ${c.id === this.cat ? 'on' : ''}" data-act="cat" data-arg="${c.id}" data-hint="${esc(c.hint)}">${ic(c.icon)}${c.name}</button>`).join('');
  }

  private card(act: string, arg: string | number, img: string, name: string, cost: string, on: boolean, hint: string, extra = '') {
    return `<button class="card ${on ? 'on' : ''}" data-act="${act}" data-arg="${arg}" data-hint="${esc(hint)}">${img}<span class="n">${esc(name)}</span><span class="c">${cost}</span>${extra}</button>`;
  }

  renderPalette() {
    const g = this.game, t = g.tool, th = g.thumbs;
    const img = (k: string) => (th[k] ? `<img src="${th[k]}" alt="">` : '<span class="sw"></span>');
    let html = '';
    switch (this.cat) {
      case 'walls':
        html = '<div class="cards">' + WALLS.slice(1).map((w) => this.card('wall', w.id, img('wall:' + w.id), w.name, fmtMoney(w.cost), t.kind === 'wall' && t.id === w.id, w.desc)).join('') + '</div>';
        break;
      case 'doors':
        html = '<div class="cards">' + DOORS.slice(1).map((d) => this.card('door', d.id, img('door:' + d.id), d.name, fmtMoney(d.cost), t.kind === 'door' && t.id === d.id, d.desc)).join('') + '</div>';
        break;
      case 'floors':
        html = '<div class="cards">' + FLOORS.map((f) => this.card('floor', f.id, `<span class="sw" style="background-image:url(${this.swatches[f.key]})"></span>`, f.name, f.cost ? fmtMoney(f.cost) : 'Free', t.kind === 'floor' && t.id === f.id, f.desc)).join('') + '</div>';
        break;
      case 'rooms':
        html = '<div class="cards">' + ROOMS.slice(1).map((r) => this.card('zone', r.id, `<span class="dot" style="background:${hex(r.color)}"></span>`, r.name, '', t.kind === 'zone' && t.id === r.id, r.desc + (r.needs.length ? ' Needs: ' + r.needs.map((a) => a.map((o) => OBJ[o].name).join(' or ')).join(', ') + '.' : ''), '').replace('class="card', 'class="card room')).join('') +
          this.card('zone', 0, '<span class="dot" style="background:#3a1a16;box-shadow:inset 0 0 0 2px var(--bad)"></span>', 'Clear room', '', t.kind === 'zone' && t.id === 0, 'Remove a room designation.').replace('class="card', 'class="card room') + '</div>';
        break;
      case 'objects':
        html = '<div class="tabs">' + OBJ_CATS.map((c) => `<button class="tab ${c.id === this.objCat ? 'on' : ''}" data-act="objcat" data-arg="${c.id}">${c.name}</button>`).join('') + '</div><div class="cards">' +
          OBJECTS.filter((o) => o.cat === this.objCat).map((o) => this.card('object', o.id, img('obj:' + o.id), o.name, fmtMoney(o.cost), t.kind === 'object' && t.id === o.id, o.desc)).join('') + '</div>';
        break;
      case 'staff':
        html = '<div class="cards">' + STAFF.map((s) => {
          const n = g.sim.staffCount(s.role);
          return this.card('hire', s.role, img('staff:' + s.role), s.name, `${fmtMoney(s.hire)} <small>+${fmtMoney(s.wage)}/day</small>`, false, s.desc, n ? `<span class="cnt">${n}</span>` : '');
        }).join('') + '</div>';
        break;
      case 'emergency': {
        const s = g.sim;
        html = `<div class="row"><span class="lbl">Orders</span>
          <button class="btn ${s.lockdown ? 'on' : ''}" data-act="lockdown" data-hint="Send every inmate back to their cell until you lift it. Makes them angrier.">${s.lockdown ? 'Lift lockdown' : 'Lockdown'}</button>
          <button class="btn" data-act="shakedown" data-hint="Lock inmates up for an hour while guards search every cell for contraband.">Shakedown</button>
          <button class="btn danger" data-act="riotpolice" data-hint="Six armoured officers arrive at the gate and stay until order is restored.">Riot squad ${fmtMoney(3000)}</button></div>
          <div class="row"><span class="lbl">Intake</span>${INTAKE_NAME.map((n, i) => `<button class="btn sm ${s.intake === i ? 'on' : ''}" data-act="intake" data-arg="${i}" data-hint="How many new inmates the 08:00 bus may bring, if you have free beds.">${n}</button>`).join('')}</div>`;
        break;
      }
    }
    this.palette.hidden = !html;
    this.palette.innerHTML = html;
    this.renderHint();
  }

  private renderHint() {
    const c = CATS.find((x) => x.id === this.cat)!;
    this.hint.textContent = this.hoverHint || (this.cat === 'select' ? '' : c.hint);
  }

  onToolChange() {
    const k = this.game.tool.kind;
    // keep the dock in step when a tool is cancelled from the keyboard
    const map: Record<string, Cat> = { select: 'select', foundation: 'foundation', wall: 'walls', door: 'doors', floor: 'floors', zone: 'rooms', object: 'objects', bulldoze: 'bulldoze', station: 'select' };
    if (k === 'select' && (this.cat === 'staff' || this.cat === 'emergency')) { /* panels without a tool stay open */ }
    else this.cat = map[k];
    this.buildToolbar();
    this.renderPalette();
  }

  // ================================================================== clicks
  private onClick(e: Event) {
    const t = (e.target as HTMLElement).closest('[data-act]') as HTMLElement | null;
    if (!t) return;
    const g = this.game, s = g.sim, act = t.dataset.act!, arg = t.dataset.arg ?? '';
    sfx.click();
    switch (act) {
      case 'start': g.start(arg as any); break;
      case 'cat': {
        this.cat = arg as Cat;
        if (arg === 'select') g.setTool({ kind: 'select' });
        else if (arg === 'foundation') g.setTool({ kind: 'foundation' });
        else if (arg === 'bulldoze') g.setTool({ kind: 'bulldoze' });
        else if (arg === 'walls') g.setTool({ kind: 'wall', id: 1 });
        else if (arg === 'floors') g.setTool({ kind: 'floor', id: 2 });
        else if (arg === 'doors') g.setTool({ kind: 'door', id: 1 });
        else if (arg === 'rooms') g.setTool({ kind: 'zone', id: 1 });
        else if (arg === 'objects') g.setTool({ kind: 'object', id: OBJECTS.find((o) => o.cat === this.objCat)!.id });
        else {
          g.tool = { kind: 'select' };
          g.input.onToolChange();
          this.buildToolbar();
          this.renderPalette();
        }
        break;
      }
      case 'wall': g.setTool({ kind: 'wall', id: +arg }); break;
      case 'door': g.setTool({ kind: 'door', id: +arg }); break;
      case 'floor': g.setTool({ kind: 'floor', id: +arg }); break;
      case 'zone': g.setTool({ kind: 'zone', id: +arg }); break;
      case 'object': g.setTool({ kind: 'object', id: arg }); break;
      case 'objcat':
        this.objCat = arg as ObjCat;
        g.setTool({ kind: 'object', id: OBJECTS.find((o) => o.cat === this.objCat)!.id });
        break;
      case 'hire':
        if (s.hire(arg as StaffRole)) {
          sfx.cash();
          s.toast(`${STAFF_BY_ROLE[arg as StaffRole].name} hired. They are walking in from the gate.`, 'good');
        } else sfx.error();
        this.renderPalette();
        if (this.modalTab) this.renderModal();
        break;
      case 'lockdown': s.toggleLockdown(); this.renderPalette(); break;
      case 'shakedown': s.shakedown(); break;
      case 'riotpolice': s.callRiotPolice(); break;
      case 'intake': s.intake = +arg; this.renderPalette(); if (this.modalTab) this.renderModal(); break;
      case 'speed':
        if (+arg === 0) s.paused = !s.paused;
        else { s.paused = false; s.speed = +arg; }
        break;
      case 'rot': g.gfx.rotate(+arg); break;
      case 'zones': g.showZones = !g.showZones; break;
      case 'modal': this.openModal(arg); break;
      case 'close': this.closeModal(); break;
      case 'tab': this.modalTab = arg; this.renderModal(); break;
      case 'desel': g.select(null); break;
      case 'follow': g.follow = !g.follow; this.renderInspector(true); break;
      case 'fire': { const a = g.selectedAgent(); if (a) { s.fire(a); g.select(null); } break; }
      case 'station': { const a = g.selectedAgent(); if (a) g.setTool({ kind: 'station', guard: a.id }); break; }
      case 'patrol': { const a = g.selectedAgent(); if (a?.s) { a.s.station = -1; s.clearPlan(a); this.renderInspector(true); } break; }
      case 'punish': { const a = g.selectedAgent(); if (a?.p && !a.busy && a.p.mode === 'normal') { s.arrest(a, 6); this.renderInspector(true); } break; }
      case 'search': {
        const a = g.selectedAgent();
        if (a?.p) {
          if (a.p.contraband) {
            s.toast(`Search: ${a.name} was hiding ${a.p.contraband === 'weapon' ? 'a shank' : a.p.contraband === 'tools' ? 'digging tools' : a.p.contraband === 'drugs' ? 'drugs' : 'a mobile phone'}.`, 'good', a.x, a.z);
            a.p.contraband = '';
            a.p.dig = 0;
            a.p.misconduct++;
            s.stats.contraband++;
          } else s.toast(`Search: ${a.name} is clean.`, 'info');
          a.p.anger = Math.min(1, a.p.anger + 0.06);
        }
        break;
      }
      case 'sell': if (g.selection?.kind === 'object') { s.removeObject(g.selection.id); g.select(null); sfx.demolish(); } break;
      case 'clearroom': {
        if (g.selection?.kind === 'room') {
          const r = g.world.roomAtTile(g.selection.tile);
          if (r) for (const i of r.tiles) s.setZone(i, 0);
          g.select(null);
        }
        break;
      }
      case 'pick': {
        const a = s.byId.get(+arg);
        if (a) {
          this.closeModal();
          g.select({ kind: 'agent', id: a.id });
          g.focus(a.x, a.z);
        }
        break;
      }
      case 'brush': this.brush = arg as Activity; this.renderModal(); break;
      case 'hour': s.regime[+arg] = this.brush; this.renderModal(); break;
      case 'regreset': s.regime = [...DEFAULT_REGIME]; this.renderModal(); break;
      case 'quality': g.setQuality(arg as any); this.renderModal(); break;
      case 'mute': setMuted(!isMuted()); this.renderModal(); break;
      case 'instant': s.instantBuild = !s.instantBuild; if (s.instantBuild) s.finishAllPlans(); this.renderModal(); break;
      case 'save': g.save(); break;
      case 'load': if (g.load()) { this.closeModal(); this.onSelection(); s.toast('Saved prison loaded.', 'good'); } break;
      case 'quit':
        this.closeModal();
        g.inMenu = true;
        g.sim.paused = false;
        g.sim.speed = 1;
        this.buildMenu();
        this.setPlaying(false);
        break;
    }
  }

  // ================================================================== toasts & cost tag
  toast(e: LogEntry) {
    if (this.game.inMenu) return;
    const d = document.createElement('div');
    d.className = 'toast glass ' + e.kind;
    d.textContent = e.text;
    d.addEventListener('click', () => {
      if (e.x !== undefined) this.game.focus(e.x, e.z!);
      d.remove();
    });
    this.toasts.prepend(d);
    while (this.toasts.children.length > 5) this.toasts.lastElementChild!.remove();
    setTimeout(() => {
      d.classList.add('out');
      setTimeout(() => d.remove(), 400);
    }, e.kind === 'bad' ? 11000 : 7500);
    if (e.kind === 'bad') sfx.bad();
  }

  setCostTag(text: string | null, x = 0, y = 0, ok = true) {
    if (!text) {
      this.cost.hidden = true;
      return;
    }
    this.cost.hidden = false;
    this.cost.textContent = text;
    this.cost.className = ok ? '' : 'no';
    const w = this.root.clientWidth;
    this.cost.style.left = Math.min(x, w - 200) + 'px';
    this.cost.style.top = y + 'px';
  }

  // ================================================================== inspector
  onSelection() {
    this.renderInspector(true);
  }

  private bar(label: string, v: number, color: string) {
    return `<div class="bar"><span>${label}</span><span class="t"><i style="width:${pct(v)}%;background:${color}"></i></span><span>${pct(v)}</span></div>`;
  }

  private renderInspector(force = false) {
    const g = this.game, s = g.sim, sel = g.selection;
    if (!sel || g.inMenu) {
      this.insp.hidden = true;
      return;
    }
    let html = '';
    const close = `<button class="x" data-act="desel" aria-label="Close">${ic('x')}</button>`;
    if (sel.kind === 'agent') {
      const a = s.byId.get(sel.id);
      if (!a || a.dead) {
        g.select(null);
        return;
      }
      html = this.agentPanel(a, close);
    } else if (sel.kind === 'object') {
      const o = g.world.objects.get(sel.id);
      if (!o) {
        g.select(null);
        return;
      }
      const def = OBJ[o.type];
      const room = g.world.roomAtTile(g.world.idx(o.x, o.y));
      const users = o.users.filter((u) => u).length;
      html = `<div class="head"><img src="${g.thumbs['obj:' + o.type] ?? ''}" alt=""><div><h3>${esc(def.name)}</h3><div class="sub">${room ? esc(ROOMS[room.type].name) : 'Not in a room'}</div></div>${close}</div>
        <div class="sub">${esc(def.desc)}</div>
        <div class="status">${o.built ? (def.slots ? `${users} of ${def.slots} in use` : 'In place') : 'Waiting for a workman'}</div>
        <div class="row"><button class="btn sm" data-act="sell">${o.built ? `Sell for ${fmtMoney(Math.round(def.cost / 2))}` : 'Cancel order'}</button></div>`;
    } else {
      const r = g.world.roomAtTile(sel.tile);
      if (!r) {
        g.select(null);
        return;
      }
      const def = ROOMS[r.type];
      const inside = s.agents.filter((a) => s.roomOf(a) === r);
      html = `<div class="head"><span class="dot" style="width:40px;height:40px;border-radius:8px;background:${hex(def.color)};flex:none"></span><div><h3>${esc(def.name)}</h3><div class="sub">${r.tiles.length} tiles${r.capacity ? ` · sleeps ${r.capacity}` : ''}</div></div>${close}</div>
        <div class="sub">${esc(def.desc)}</div>
        ${r.valid ? '<div class="ok">Working as intended</div>' : `<div class="lbl">Still needed</div><ul class="missing">${r.missing.map((m) => `<li>${esc(m)}</li>`).join('')}</ul>`}
        ${r.outdoor ? '' : this.bar('Dirt', r.dirt, heat(r.dirt))}
        <div class="sub">${inside.filter((a) => a.kind === 'prisoner').length} inmates and ${inside.filter((a) => a.kind === 'staff').length} staff inside</div>
        <div class="row"><button class="btn sm" data-act="clearroom">Remove designation</button></div>`;
    }
    if (force || this.insp.dataset.h !== html) {
      // keep hover and focus stable: only replace when something changed
      this.insp.dataset.h = html;
      this.insp.innerHTML = html;
    }
    this.insp.hidden = false;
  }

  private agentPanel(a: Agent, close: string): string {
    const g = this.game;
    const follow = `<button class="btn sm ${g.follow ? 'on' : ''}" data-act="follow">${g.follow ? 'Following' : 'Follow'}</button>`;
    if (a.p) {
      const p = a.p;
      const modeTag: Record<string, string> = { solitary: 'Solitary', punished: 'Confined', escaping: 'Escaping', infirm: 'Infirmary', down: 'Unconscious', riot: 'Rioting', intake: 'New arrival', released: 'Released', fight: 'Fighting', cuffed: 'Restrained' };
      return `<div class="head"><img src="${g.thumbs['prisoner:' + p.sec] ?? ''}" alt=""><div><h3>${esc(a.name)}</h3><div class="sub">${SEC_NAME[p.sec]} security · ${esc(p.crime)} · age ${p.age}</div></div>${close}</div>
        <div class="status">${esc(a.status || 'Idle')}</div>
        <div class="tagrow">${modeTag[p.mode] ? `<span class="tag" style="background:#7a2a22">${modeTag[p.mode]}</span>` : ''}${p.bedId ? '' : '<span class="tag" style="background:#6b5416">No bed</span>'}${p.edu >= 1 ? '<span class="tag" style="background:#1f5a38">Educated</span>' : ''}${p.misconduct ? `<span class="tag">${p.misconduct} offence${p.misconduct > 1 ? 's' : ''}</span>` : ''}</div>
        ${this.bar('Anger', p.anger, heat(p.anger))}
        ${this.bar('Health', p.health, cool(p.health))}
        ${this.bar('Sentence', p.served / p.sentence, 'var(--info)')}
        <div class="sub">${Math.max(0, p.sentence - p.served).toFixed(1)} days left of ${p.sentence} · reform ${pct(p.reform)}%</div>
        <div class="lbl">Needs</div>
        <div class="needs">${NEEDS.map((n, i) => `<div class="need">${NEED_LABEL[n]}<div class="t"><i style="width:${pct(p.needs[i])}%;background:${heat(p.needs[i])}"></i></div></div>`).join('')}</div>
        <div class="row">${follow}<button class="btn sm" data-act="search" data-hint="Pat this inmate down for contraband. It annoys them.">Search</button><button class="btn sm" data-act="punish" data-hint="Six hours in solitary, or locked in their own cell if no solitary is free.">Solitary</button></div>`;
    }
    if (a.s) {
      const sd = a.s;
      const def = sd.role === 'riot' ? null : STAFF_BY_ROLE[sd.role];
      const station = sd.station >= 0 ? g.world.roomAtTile(sd.station) : undefined;
      return `<div class="head"><img src="${g.thumbs[sd.role === 'riot' ? 'riot' : 'staff:' + sd.role] ?? ''}" alt=""><div><h3>${esc(a.name)}</h3><div class="sub">${def ? def.name : 'Riot officer'}${def ? ` · ${fmtMoney(sd.wage)}/day` : ''}</div></div>${close}</div>
        <div class="status">${esc(a.status || 'Idle')}</div>
        ${sd.role === 'guard' ? `<div class="sub">${station ? `Posted to the ${esc(ROOMS[station.type].name)}` : 'On free patrol'}</div>` : ''}
        ${this.bar('Energy', sd.energy, cool(sd.energy))}
        ${this.bar('Health', sd.health, cool(sd.health))}
        <div class="row">${follow}${sd.role === 'guard' ? `<button class="btn sm" data-act="station" data-hint="Then click the room this guard should stay in.">Post to room</button>${station ? '<button class="btn sm" data-act="patrol">Patrol</button>' : ''}` : ''}${def ? '<button class="btn sm danger" data-act="fire">Dismiss</button>' : ''}</div>`;
    }
    return `<div class="head"><img src="${g.thumbs['visitor'] ?? ''}" alt=""><div><h3>${esc(a.name)}</h3><div class="sub">Visitor</div></div>${close}</div><div class="status">${esc(a.status || 'Visiting')}</div><div class="row">${follow}</div>`;
  }

  // ================================================================== modal
  openModal(tab: string) {
    this.modalTab = tab;
    this.modal.hidden = false;
    this.renderModal();
  }
  closeModal(): boolean {
    if (this.modal.hidden) return false;
    this.modal.hidden = true;
    this.modalTab = null;
    return true;
  }
  refreshSettings() {
    if (this.modalTab === 'settings') this.renderModal();
  }

  private renderModal() {
    const tab = this.modalTab;
    if (!tab) return;
    const inGame = !this.game.inMenu;
    const tabs: [string, string][] = inGame
      ? [['overview', 'Overview'], ['grants', 'Grants'], ['inmates', 'Inmates'], ['staff', 'Staff'], ['regime', 'Regime'], ['finance', 'Finance'], ['settings', 'Settings'], ['help', 'How to play']]
      : [['help', 'How to play']];
    let body = '';
    switch (tab) {
      case 'overview': body = this.tabOverview(); break;
      case 'grants': body = this.tabGrants(); break;
      case 'inmates': body = this.tabInmates(); break;
      case 'staff': body = this.tabStaff(); break;
      case 'regime': body = this.tabRegime(); break;
      case 'finance': body = this.tabFinance(); break;
      case 'settings': body = this.tabSettings(); break;
      default: body = this.tabHelp();
    }
    const sheet = this.modal.querySelector('.body');
    const scroll = sheet && this.modal.dataset.tab === tab ? sheet.scrollTop : 0;
    this.modal.dataset.tab = tab;
    this.modal.innerHTML = `<div class="sheet"><header><h2>${inGame ? esc(this.game.sim.name) : 'IRONVALE'}</h2><button class="btn sm" data-act="close">Close</button></header>
      <div class="tabs">${tabs.map(([id, n]) => `<button class="tab ${id === tab ? 'on' : ''}" data-act="tab" data-arg="${id}">${n}</button>`).join('')}</div>
      <div class="body">${body}</div></div>`;
    if (scroll) this.modal.querySelector('.body')!.scrollTop = scroll;
  }

  private tabOverview(): string {
    const s = this.game.sim, r = s.rating(), av = s.averages();
    const stars = Math.round(r.overall / 20);
    const alerts: string[] = [];
    const breach = [...new Set(s.breaches().map((room) => ROOMS[room.type].name))];
    if (breach.length) alerts.push(`<div class="alertline bad">Security breach: inmates can walk straight off the grounds from the ${esc(breach.slice(0, 5).join(', '))}. Close the gap with walls, fences and Staff Doors.</div>`);
    const invalid = [...s.world.rooms.values()].filter((x) => !x.valid);
    if (invalid.length) alerts.push(`<div class="alertline">${invalid.length} room${invalid.length > 1 ? 's are' : ' is'} not working yet: ${esc([...new Set(invalid.map((x) => ROOMS[x.type].name))].slice(0, 5).join(', '))}. Click a room to see what it needs.</div>`);
    const noBed = s.prisoners.filter((a) => !a.p!.bedId).length;
    if (noBed) alerts.push(`<div class="alertline">${noBed} inmate${noBed > 1 ? 's have' : ' has'} no bed.</div>`);
    if (s.prisoners.length && !s.counts.guards) alerts.push('<div class="alertline bad">You have no guards.</div>');
    if (s.prisoners.length && !s.counts.cooks) alerts.push('<div class="alertline bad">You have no cooks, so nobody is being fed.</div>');
    if (s.jobs().length && !s.counts.workmen) alerts.push('<div class="alertline">Construction is planned but you have no workmen.</div>');
    if (s.money < 0) alerts.push('<div class="alertline bad">You are in debt. Wages are still being paid.</div>');
    return `<div class="grid2">
      <div class="sec"><h3>Prison rating</h3><div class="big">${av.n ? Math.round(r.overall) : '<span style="font-family:var(--ui)">–</span>'}<small>out of 100</small></div><div class="stars">${'★'.repeat(stars)}${'☆'.repeat(5 - stars)}</div>
        <p style="margin-top:8px">Day ${s.day}. ${s.prisoners.length} inmates in ${s.counts.capacity} beds, ${s.staff.length} staff, ${fmtMoney(s.money)} in the bank.</p></div>
      <div class="sec"><h3>Breakdown</h3>${this.bar('Wellbeing', r.wellbeing, cool(r.wellbeing))}${this.bar('Order', r.order, cool(r.order))}${this.bar('Safety', r.safety, cool(r.safety))}${this.bar('Security', r.security, cool(r.security))}${this.bar('Health', r.health, cool(r.health))}${this.bar('Reform', r.reform, 'var(--info)')}</div>
    </div>
    ${alerts.length ? `<div class="sec"><h3>Needs your attention</h3><div style="display:flex;flex-direction:column;gap:6px">${alerts.join('')}</div></div>` : ''}
    <div class="grid2">
      <div class="sec"><h3>Unmet needs, prison average</h3>${NEEDS.map((n, i) => this.bar(NEED_LABEL[n], av.needs[i], heat(av.needs[i]))).join('')}${this.bar('Anger', av.anger, heat(av.anger))}</div>
      <div class="sec"><h3>Record</h3><table class="list"><tbody>
        <tr><td>Inmates received</td><td class="num">${s.stats.intake}</td></tr>
        <tr><td>Released</td><td class="num">${s.stats.released}</td></tr>
        <tr><td>Escapes</td><td class="num">${s.stats.escapes}</td></tr>
        <tr><td>Deaths</td><td class="num">${s.stats.deaths}</td></tr>
        <tr><td>Fights</td><td class="num">${s.stats.fights}</td></tr>
        <tr><td>Contraband seized</td><td class="num">${s.stats.contraband}</td></tr>
        <tr><td>Meals ready</td><td class="num">${Math.floor(s.meals)} / ${s.mealCap()}</td></tr>
      </tbody></table></div>
    </div>`;
  }

  private tabGrants(): string {
    const s = this.game.sim;
    return `<div class="sec"><h3>State grants</h3><p>The state pays out when the prison reaches each milestone. They also make a sensible build order.</p>
      <div style="display:flex;flex-direction:column;gap:6px">${s.objectives.map((o) => {
        const done = s.objectivesDone.has(o.id);
        return `<div class="grant ${done ? 'done' : ''}"><span class="tick">${done ? '✓' : ''}</span><div><b>${esc(o.title)}</b><span>${esc(o.desc)}</span></div><em>${fmtMoney(o.reward)}</em></div>`;
      }).join('')}</div></div>`;
  }

  private tabInmates(): string {
    const s = this.game.sim;
    if (!s.prisoners.length) return '<div class="sec"><h3>Inmates</h3><p>Nobody is locked up yet. The bus arrives at 08:00 each day once you have valid cells and the intake is open.</p></div>';
    const rows = [...s.prisoners].sort((a, b) => b.p!.anger - a.p!.anger).map((a) => {
      const p = a.p!;
      return `<tr class="click" data-act="pick" data-arg="${a.id}"><td><b>${esc(a.name)}</b></td><td>${SEC_NAME[p.sec]}</td><td>${esc(a.status || 'Idle')}</td>
        <td><span class="mini"><i style="width:${pct(p.anger)}%;background:${heat(p.anger)}"></i></span></td>
        <td><span class="mini"><i style="width:${pct(p.health)}%;background:${cool(p.health)}"></i></span></td>
        <td class="num">${Math.max(0, p.sentence - p.served).toFixed(1)} d</td></tr>`;
    }).join('');
    return `<div class="sec"><h3>${s.prisoners.length} inmates, angriest first</h3><div class="scroll-x"><table class="list"><thead><tr><th>Name</th><th>Security</th><th>Doing</th><th>Anger</th><th>Health</th><th class="num">Left</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
  }

  private tabStaff(): string {
    const s = this.game.sim, th = this.game.thumbs;
    const hire = STAFF.map((d) => this.card('hire', d.role, th['staff:' + d.role] ? `<img src="${th['staff:' + d.role]}" alt="">` : '', d.name, `${fmtMoney(d.hire)} <small>+${fmtMoney(d.wage)}/day</small>`, false, d.desc, s.staffCount(d.role) ? `<span class="cnt">${s.staffCount(d.role)}</span>` : '')).join('');
    const rows = s.staff.map((a) => `<tr class="click" data-act="pick" data-arg="${a.id}"><td><b>${esc(a.name)}</b></td><td>${a.s!.role === 'riot' ? 'Riot officer' : STAFF_BY_ROLE[a.s!.role as StaffRole].name}</td><td>${esc(a.status || 'Idle')}</td>
      <td><span class="mini"><i style="width:${pct(a.s!.energy)}%;background:${cool(a.s!.energy)}"></i></span></td><td class="num">${fmtMoney(a.s!.wage)}</td></tr>`).join('');
    const wages = s.staff.reduce((t, a) => t + a.s!.wage, 0);
    return `<div class="sec"><h3>Hire</h3><div class="cards" style="max-width:100%">${hire}</div></div>
      <div class="sec"><h3>${s.staff.length} on the payroll, ${fmtMoney(wages)} a day</h3><div class="scroll-x"><table class="list"><thead><tr><th>Name</th><th>Role</th><th>Doing</th><th>Energy</th><th class="num">Wage</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
  }

  private tabRegime(): string {
    const s = this.game.sim;
    return `<div class="sec"><h3>Daily regime</h3><p>Every inmate follows this timetable. Pick an activity, then click the hours it should cover. Meals need an Eat hour, showers a Shower hour, and the workshop and classroom only run during Work.</p>
      <div class="row" style="margin-bottom:12px">${ACTS.map((a) => `<button class="btn sm ${this.brush === a ? 'on' : ''}" data-act="brush" data-arg="${a}"><span style="width:10px;height:10px;border-radius:3px;background:${ACT_COLOR[a]}"></span>${ACT_LABEL[a]}</button>`).join('')}<button class="btn sm" data-act="regreset">Reset</button></div>
      <div class="regime">${s.regime.map((a, h) => `<button class="${h === s.hour ? 'now' : ''}" style="background:${ACT_COLOR[a]}" data-act="hour" data-arg="${h}"><b>${String(h).padStart(2, '0')}</b>${ACT_LABEL[a].split(' ')[0]}</button>`).join('')}</div></div>
      <div class="sec"><h3>Intake</h3><div class="row">${INTAKE_NAME.map((n, i) => `<button class="btn sm ${s.intake === i ? 'on' : ''}" data-act="intake" data-arg="${i}">${n}</button>`).join('')}</div><p style="margin-top:8px">The bus calls at 08:00 and only brings inmates you have beds for.</p></div>`;
  }

  private tabFinance(): string {
    const s = this.game.sim;
    const table = (l: Record<string, number>, title: string) => {
      const e = Object.entries(l).sort((a, b) => b[1] - a[1]);
      const net = e.reduce((t, [, v]) => t + v, 0);
      return `<div class="sec"><h3>${title}</h3><table class="list"><tbody>${e.map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num ${v >= 0 ? 'pos' : 'neg'}">${v >= 0 ? '+' : ''}${fmtMoney(v)}</td></tr>`).join('') || '<tr><td>Nothing yet</td><td></td></tr>'}
        <tr><td><b>Balance</b></td><td class="num ${net >= 0 ? 'pos' : 'neg'}"><b>${net >= 0 ? '+' : ''}${fmtMoney(net)}</b></td></tr></tbody></table></div>`;
    };
    let grant = 600;
    for (const a of s.prisoners) grant += [110, 150, 210][a.p!.sec];
    const wages = s.staff.reduce((t, a) => t + a.s!.wage, 0);
    // bar chart of daily balance
    const h = s.history.slice(-14);
    let chart = '';
    if (h.length) {
      const max = Math.max(1000, ...h.map((d) => Math.abs(d.net)));
      const bw = 100 / 14;
      chart = `<div class="sec"><h3>Daily balance, last ${h.length} day${h.length > 1 ? 's' : ''}</h3><svg viewBox="0 0 100 44" style="width:100%;max-width:520px;height:auto;display:block" role="img" aria-label="Daily balance chart">
        <line x1="0" x2="100" y1="20" y2="20" stroke="rgba(255,255,255,0.25)" stroke-width="0.3"/>
        ${h.map((d, i) => {
          const hh = (Math.abs(d.net) / max) * 18;
          return `<rect x="${(i * bw + 1).toFixed(2)}" y="${(d.net >= 0 ? 20 - hh : 20).toFixed(2)}" width="${(bw - 2).toFixed(2)}" height="${Math.max(0.4, hh).toFixed(2)}" rx="0.6" fill="${d.net >= 0 ? '#5fcf80' : '#ef5b4c'}"/><text x="${(i * bw + bw / 2).toFixed(2)}" y="43" font-size="3" fill="#9aa7b2" text-anchor="middle">${d.day}</text>`;
        }).join('')}</svg></div>`;
    }
    return `<div class="grid2"><div class="sec"><h3>Cash in hand</h3><div class="big">${fmtMoney(s.money)}</div><p style="margin-top:8px">At midnight the state pays about ${fmtMoney(Math.round(grant * (s.counts.wardenIn ? 1.1 : 1)))} and you pay ${fmtMoney(wages)} in wages. A Warden at their desk adds 10% to the grant.</p></div>${chart}</div>
      <div class="grid2">${table(s.ledgerToday, 'Today so far')}${table(s.ledgerYesterday, 'Yesterday')}</div>`;
  }

  private tabSettings(): string {
    const g = this.game, q = g.gfx.quality;
    return `<div class="grid2">
      <div class="sec"><h3>Graphics</h3><div class="row">${(['low', 'medium', 'high'] as const).map((k) => `<button class="btn sm ${q === k ? 'on' : ''}" data-act="quality" data-arg="${k}">${k[0].toUpperCase() + k.slice(1)}</button>`).join('')}</div><p style="margin-top:8px">High adds ambient occlusion and the sharpest shadows. The game drops a level by itself if the frame rate stays low. Currently ${Math.round(g.fps)} frames a second.</p></div>
      <div class="sec"><h3>Sound</h3><div class="row"><button class="btn sm ${isMuted() ? '' : 'on'}" data-act="mute">${isMuted() ? 'Sound off' : 'Sound on'}</button></div></div>
      <div class="sec"><h3>Save</h3><div class="row"><button class="btn sm pri" data-act="save">Save now</button><button class="btn sm" data-act="load" ${g.hasSave() ? '' : 'disabled style="opacity:.4"'}>Load last save</button></div><p style="margin-top:8px">The prison saves itself every midnight, in this browser only.</p></div>
      <div class="sec"><h3>Sandbox</h3><div class="row"><button class="btn sm ${g.sim.instantBuild ? 'on' : ''}" data-act="instant">Instant building ${g.sim.instantBuild ? 'on' : 'off'}</button></div><p style="margin-top:8px">Skip the workmen: everything you plan appears at once.</p></div>
      <div class="sec"><h3>Leave</h3><div class="row"><button class="btn sm" data-act="quit">Back to title</button></div><p style="margin-top:8px">Save first if you want to keep this prison.</p></div>
    </div>`;
  }

  private tabHelp(): string {
    const k = (s: string) => `<span class="kbd">${s}</span>`;
    return `<div class="grid2">
      <div class="sec"><h3>Your first prison</h3><ol class="steps">
        <li><b>Building</b>: drag a rectangle. Workmen pour the walls and floor.</li>
        <li><b>Walls</b> split it into rooms and <b>Doors</b> let people through. Cells need a Cell Door.</li>
        <li><b>Rooms</b>: paint each space with its purpose. A red label lists what is missing.</li>
        <li><b>Objects</b>: a cell needs a bed and a toilet, a canteen needs a serving counter and benches, a kitchen needs a cooker and a fridge.</li>
        <li><b>Staff</b>: guards, cooks and a warden at the very least.</li>
        <li><b>Fence it in.</b> Inmates walk out of any gap. Only staff can open Staff Doors and Security Gates.</li>
        <li>The bus brings inmates at 08:00 if you have free beds. Then keep them fed, clean, busy and calm.</li>
      </ol></div>
      <div class="sec"><h3>Controls</h3><div class="keys">
        <span>${k('W')}${k('A')}${k('S')}${k('D')}</span><span>Move the camera, or drag with the mouse</span>
        <span>Wheel</span><span>Zoom. Pinch on a touch screen</span>
        <span>${k('Q')} ${k('E')}</span><span>Rotate the view</span>
        <span>${k('R')}</span><span>Rotate the object being placed</span>
        <span>${k('Space')}</span><span>Pause</span>
        <span>${k('1')} ${k('2')} ${k('3')}</span><span>Game speed</span>
        <span>${k('Tab')}</span><span>Room overlay</span>
        <span>${k('Esc')}</span><span>Cancel the tool. Right-click does the same</span>
        <span>${k('Del')}</span><span>Demolish tool</span>
      </div></div>
      <div class="sec"><h3>Why inmates misbehave</h3><p>Each inmate has nine needs. Unmet needs build anger, anger starts fights, and a prison full of angry inmates riots. Hunger, sleep and safety matter most.</p><p>Guards calm things by being nearby and break up fights. Troublemakers go to Solitary. A Psychologist, a Chaplain and yard time bring anger down.</p></div>
      <div class="sec"><h3>Security</h3><p>Contraband comes in through visits, the workshop and the kitchen. Metal detectors catch weapons and tools, a Shakedown searches every cell, and inmates with tools dig tunnels at night.</p><p>CCTV needs a console with a guard at it. Guard towers stop runners in a wide radius.</p></div>
    </div>`;
  }

  // ================================================================== tick
  update(dt: number) {
    if (this.game.inMenu) return;
    this.acc += dt;
    this.slow += dt;
    if (this.acc >= 0.2) {
      this.acc = 0;
      this.updateHud();
      this.renderInspector();
    }
    if (this.slow >= 1) {
      this.slow = 0;
      if (this.modalTab && ['overview', 'inmates', 'staff', 'finance'].includes(this.modalTab)) this.renderModal();
      if (this.cat === 'staff') {
        // refresh head-counts without disturbing hover
        const want = STAFF.map((s) => this.game.sim.staffCount(s.role)).join(',');
        if (this.palette.dataset.cnt !== want) {
          this.palette.dataset.cnt = want;
          this.renderPalette();
        }
      }
    }
  }
}
