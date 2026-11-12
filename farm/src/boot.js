/**
 * The page around the scene: title card, tape counter, touch buttons.
 *
 * Kept apart from main.js so the renderer knows nothing about the DOM beyond
 * its canvas, and so the whole thing can be bundled into one file and dropped
 * somewhere that has no server behind it.
 */
import { Farm } from './main.js';

const $ = (id) => document.getElementById(id);

// ?pose=x,z,yaw,pitch  ?time=12  ?torch=1  ?tape=0  ?manual=1 -- for
// repeatable captures and for the test harness, which drives frames itself.
const q = new URLSearchParams(location.search);
const num = (k) => (q.has(k) ? Number(q.get(k)) : undefined);

function start(saved = {}) {
  const farm = new Farm($('view'), {
    pose: q.has('pose') ? q.get('pose').split(',').map(Number) : saved.pose || null,
    time: num('time'), torch: num('torch') || saved.torch, tape: num('tape'),
    manual: q.has('manual'), autostart: q.has('pose') || q.has('manual'),
  });
  window.farm = farm;
  try {
    farm.boot();
  } catch (e) {
    farm.state = 'error'; farm.error = String(e.message || e);
  }
  if (farm.state === 'error') {
    $('title').hidden = true;
    $('error').hidden = false;
    $('error').textContent = farm.error;
    return;
  }

  // Buttons exist for thumbs; they stay hidden until the screen is touched.
  const root = document.documentElement;
  window.addEventListener('touchstart', () => root.classList.add('touch'), { once: true, passive: true });
  window.addEventListener('keydown', () => farm.begin(), { once: true });
  $('torch').addEventListener('click', () => { farm.begin(); farm.torch = !farm.torch; });
  $('run').addEventListener('click', () => { farm.begin(); farm.running = !farm.running; });
  $('tape').addEventListener('click', () => { farm.begin(); farm.tape = farm.tape ? 0 : 1; });

  const stick = $('stick'), knob = $('knob');
  farm.onStick = (x, y, dx, dy) => {
    stick.hidden = x === null;
    if (x === null) return;
    stick.style.left = `${x}px`; stick.style.top = `${y}px`;
    knob.style.transform = `translate(${dx}px, ${dy}px)`;
  };

  // A camcorder's tape counter, running only while you are walking about.
  let played = 0, last = performance.now();
  setInterval(() => {
    const now = performance.now();
    if (farm.state === 'playing') played += (now - last) / 1000;
    last = now;
    const s = Math.floor(played), pad = (n) => String(n).padStart(2, '0');
    $('counter').textContent = `${Math.floor(s / 3600)}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}`;
    $('title').classList.toggle('gone', farm.state !== 'title');
    $('osd').classList.toggle('on', farm.state === 'playing');
    $('torch').setAttribute('aria-pressed', String(!!farm.torch));
    $('run').setAttribute('aria-pressed', String(!!farm.running));
    $('tape').setAttribute('aria-pressed', String(!!farm.tape));
  }, 200);

  // Where the page is hosted somewhere that can swap in a new version under a
  // running game, hand it where the player is standing so they stay there.
  const hot = window.claude && window.claude.hot;
  if (hot && hot.snapshot) {
    hot.snapshot(() => ({ pose: [farm.player.x, farm.player.z, farm.player.yaw, farm.player.pitch], torch: farm.torch ? 1 : 0 }));
  }
}

const hot = window.claude && window.claude.hot;
if (hot && hot.ready) hot.ready(start); else start((hot && hot.data) || {});
