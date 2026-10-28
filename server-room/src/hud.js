// DOM overlay: loading/start screen, crosshair, DCIM asset card, prompts,
// the open ticket, toasts and touch controls.
const $ = (id) => document.getElementById(id);

export class Hud {
  constructor() {
    this.el = {
      overlay: $('overlay'), status: $('status'), enter: $('enter'),
      hud: $('hud'), card: $('card'), prompt: $('prompt'), toast: $('toast'),
      ticket: $('ticket'), touch: $('touch'), stick: $('stick'), knob: $('knob'),
      pause: $('pause'), help: $('help'), loot: $('loot'), breach: $('breach'),
    };
    this.toastTimer = 0;
    this.lastCard = '';
  }

  status(text) { this.el.status.textContent = text; }

  ready(onEnter) {
    const b = this.el.enter;
    b.disabled = false;
    b.textContent = 'Enter the hall';
    b.addEventListener('click', onEnter);
    this.status('Ready.');
  }

  enter(touch) {
    this.el.overlay.hidden = true;
    this.el.hud.hidden = false;
    this.el.touch.hidden = !touch;
    document.body.classList.toggle('touch', touch);
  }

  pause(show) { this.el.pause.hidden = !show; }
  toggleHelp() { this.el.help.hidden = !this.el.help.hidden; }

  stick(show, x = 0, y = 0, dx = 0, dy = 0) {
    const s = this.el.stick;
    s.classList.toggle('on', show);
    if (show) {
      s.style.left = `${x}px`;
      s.style.top = `${y}px`;
      this.el.knob.style.transform = `translate(${dx}px, ${dy}px)`;
    }
  }

  // info: { title, chip, chipKind, lines: [..], note } or null
  card(info) {
    const key = info ? JSON.stringify(info) : '';
    if (key === this.lastCard) return;
    this.lastCard = key;
    const c = this.el.card;
    if (!info) { c.hidden = true; return; }
    c.hidden = false;
    c.innerHTML = '';
    const head = document.createElement('div');
    head.className = 'card-head';
    const t = document.createElement('strong');
    t.textContent = info.title;
    head.append(t);
    if (info.chip) {
      const chip = document.createElement('span');
      chip.className = `chip ${info.chipKind ?? ''}`;
      chip.textContent = info.chip;
      head.append(chip);
    }
    c.append(head);
    for (const l of info.lines) {
      const p = document.createElement('div');
      p.className = 'card-line';
      p.textContent = l;
      c.append(p);
    }
    if (info.note) {
      const n = document.createElement('div');
      n.className = 'card-note';
      n.textContent = info.note;
      c.append(n);
    }
  }

  loot(count, gb) {
    const el = this.el.loot;
    el.hidden = false;
    el.innerHTML = `<span class="loot-ic">◈</span> ${count} breached <span class="loot-sep">·</span> ${gb} GB`;
  }

  breach(info) {
    const el = this.el.breach;
    if (!info) { el.hidden = true; return; }
    el.hidden = false;
    const pct = Math.round(info.pct * 100);
    el.innerHTML = `<div class="br-top"><span>${info.title}</span><span class="br-pct">${pct}%</span></div><div class="br-track"><i style="width:${pct}%"></i></div>`;
  }

  prompt(text, keyLabel = 'E') {
    const p = this.el.prompt;
    if (!text) { p.hidden = true; return; }
    p.hidden = false;
    const sig = `${keyLabel}|${text}`;
    if (p.dataset.t !== sig) {
      p.dataset.t = sig;
      p.innerHTML = '';
      const key = document.createElement('kbd');
      key.textContent = document.body.classList.contains('touch') ? 'Tap' : keyLabel;
      p.append(key, document.createTextNode(` ${text}`));
    }
  }

  toast(text, ms = 4200) {
    const t = this.el.toast;
    t.textContent = text;
    t.hidden = false;
    t.classList.remove('show');
    void t.offsetWidth;
    t.classList.add('show');
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => { t.hidden = true; }, ms);
  }

  // ticket: { id, sev, title, steps: [{ text, done }], resolved }
  ticket(tk) {
    const el = this.el.ticket;
    el.innerHTML = '';
    const head = document.createElement('div');
    head.className = 'tk-head';
    const id = document.createElement('span');
    id.className = 'tk-id';
    id.textContent = tk.id;
    const sev = document.createElement('span');
    sev.className = `chip ${tk.resolved ? 'ok' : 'warn'}`;
    sev.textContent = tk.resolved ? 'RESOLVED' : tk.sev;
    head.append(id, sev);
    const title = document.createElement('div');
    title.className = 'tk-title';
    title.textContent = tk.title;
    const ol = document.createElement('ol');
    tk.steps.forEach((s, i) => {
      const li = document.createElement('li');
      if (s.done) li.className = 'done';
      else if (tk.steps.findIndex((x) => !x.done) === i) li.className = 'current';
      li.textContent = s.text;
      ol.append(li);
    });
    el.append(head, title, ol);
  }
}
