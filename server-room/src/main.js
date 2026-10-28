// Data Hall B — entry point: renderer, scene assembly, post-processing, loop.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { RectAreaLightUniformsLib } from 'three/addons/lights/RectAreaLightUniformsLib.js';
import { buildDeviceAtlas } from './atlas.js';
import { buildRacks } from './racks.js';
import { buildRoom, ROOM } from './room.js';
import { bakeFloorMask } from './lightbake.js';
import { maskedFloorMaterial } from './materials.js';
import { Player } from './player.js';
import { Ambience } from './audio.js';
import { Hud } from './hud.js';
import { Tickets } from './tickets.js';
import { Heist } from './heist.js';
import { nextFrame } from './util.js';

const params = new URLSearchParams(location.search);
const touch = matchMedia('(pointer: coarse)').matches;
const quality = params.get('q') ?? (touch ? 'low' : 'high');
const still = Number(params.get('still') ?? 0); // test hook: stop after N frames
const hud = new Hud();

const FinishShader = {
  uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uVignette: { value: 0.32 }, uGrain: { value: 0.018 } },
  vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float uTime, uVignette, uGrain; varying vec2 vUv;
    float h(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    void main() {
      vec4 c = texture2D(tDiffuse, vUv);
      vec2 d = vUv - 0.5;
      c.rgb *= 1.0 - uVignette * dot(d, d) * 2.0;
      c.rgb += (h(vUv * 1931.0 + fract(uTime) * 97.0) - 0.5) * uGrain;
      gl_FragColor = c;
    }`,
};

const T0 = performance.now();
const mark = (label) => { if (params.has('cam')) console.log(`[t] ${label} ${Math.round(performance.now() - T0)}ms`); };

async function boot() {
  const canvas = document.getElementById('view');
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
  } catch (e) {
    hud.status('This browser could not start WebGL 2, which the hall needs. Try a current Chrome, Edge, Firefox or Safari.');
    return;
  }
  const dpr = Math.min(devicePixelRatio || 1, quality === 'high' ? 1.5 : 1.25);
  renderer.setPixelRatio(dpr);
  renderer.setSize(innerWidth, innerHeight);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = Number(params.get('exp') ?? 1.6);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  RectAreaLightUniformsLib.init();

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0d10);
  const camera = new THREE.PerspectiveCamera(68, innerWidth / innerHeight, 0.03, 60);
  scene.add(camera);

  hud.status('Painting server faceplates…');
  await nextFrame();
  const atlas = buildDeviceAtlas();
  mark('atlas');
  const aniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());

  hud.status('Racking 56 cabinets and patching cables…');
  await nextFrame();
  const racks = buildRacks(atlas, { quality });
  mark('racks');

  hud.status('Building the hall…');
  await nextFrame();
  const room = buildRoom({ quality });
  mark('room');

  hud.status('Baking light onto the raised floor…');
  await nextFrame();
  const mask = bakeFloorMask(room.occluders);
  mark('bake');
  for (const m of room.floorMats) maskedFloorMaterial(m, mask, ROOM);
  scene.add(room.group, racks.group);
  scene.traverse((o) => {
    const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
    for (const m of mats) for (const k of ['map', 'normalMap', 'roughnessMap', 'emissiveMap', 'alphaMap']) if (m[k]) m[k].anisotropy = aniso;
  });

  // ---- lights that toggle: torch on the camera, emergency fixtures ----
  const torch = new THREE.SpotLight(0xfff1dc, 0, 22, 0.38, 0.55, 2);
  torch.position.set(0.12, -0.12, 0);
  camera.add(torch);
  torch.target.position.set(0.05, -0.1, -1);
  camera.add(torch.target);
  const emergency = [[-5.6, 2.6, 6.95], [5.6, 2.6, -6.95], [6.9, 2.6, 6.95]].map(([x, y, z]) => {
    const s = new THREE.SpotLight(0xfff0d8, 0, 18, 0.9, 0.8, 2);
    s.position.set(x, y, z);
    s.target.position.set(x * 0.4, 0, z * 0.4);
    scene.add(s, s.target);
    return s;
  });

  // fixture output for the aisle luminaires (set before the env capture below)
  for (const l of room.areaLights) { l.userData.base = 11; l.intensity = 11; }

  // ---- reflections and bounce light: capture the lit room into an env map ----
  hud.status('Capturing reflections…');
  await nextFrame();
  const cubeRT = new THREE.WebGLCubeRenderTarget(256, { type: THREE.HalfFloatType });
  const cubeCam = new THREE.CubeCamera(0.05, 40, cubeRT);
  cubeCam.position.set(0, 1.6, -2.7);
  scene.add(cubeCam);
  const pmrem = new THREE.PMREMGenerator(renderer);
  let envRT = null;
  const envPasses = params.get('env') === '0' ? 0 : 2; // debug hook: skip the costly capture
  for (let pass = 0; pass < envPasses; pass++) {
    cubeCam.update(renderer, scene);
    const next = pmrem.fromCubemap(cubeRT.texture);
    envRT?.dispose();
    envRT = next;
    scene.environment = envRT.texture;
  }
  scene.environmentIntensity = 0.85;
  scene.remove(cubeCam);
  mark('env');

  // ---- post ----
  const size = new THREE.Vector2();
  renderer.getDrawingBufferSize(size);
  const rt = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType, samples: quality === 'high' ? 4 : 2 });
  const composer = new EffectComposer(renderer, rt);
  composer.addPass(new RenderPass(scene, camera));
  let gtao = null;
  if (quality === 'high' && params.get('ao') !== '0') {
    gtao = new GTAOPass(scene, camera, size.x, size.y);
    gtao.updateGtaoMaterial({ radius: 0.45, distanceExponent: 1.4, thickness: 1.2, scale: 1.0, samples: 12 });
    gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 12 });
    gtao.blendIntensity = 0.85;
    const orig = gtao.overrideVisibility.bind(gtao);
    gtao.overrideVisibility = function () {
      orig();
      scene.traverse((o) => { if (o.userData.noAO) o.visible = false; });
    };
    composer.addPass(gtao);
  }
  const bloom = new UnrealBloomPass(new THREE.Vector2(size.x / 2, size.y / 2), 0.32, 0.12, 3.0);
  if (params.get('bloom') !== '0') composer.addPass(bloom);
  composer.addPass(new OutputPass());
  const finish = new ShaderPass(FinishShader);
  composer.addPass(finish);

  racks.ledMesh.material.uniforms.uViewportH.value = size.y;

  // ---- player, audio, interaction ----
  const colliders = [...room.colliders, ...racks.colliders];
  const player = new Player(camera, canvas, colliders, hud);
  player.attach();
  const audio = new Ambience();
  const tickets = new Tickets(hud, racks.fault);
  const heist = new Heist(camera, scene, hud, audio);

  const cam = params.get('cam');
  if (cam) {
    const [x, y, z, yaw = 0, pitch = 0] = cam.split(',').map(Number);
    player.place(x, z, yaw, pitch);
    player.eye = player.fixedEye = y;
  } else {
    player.place(room.spawn.x, room.spawn.z, room.spawn.yaw, -0.04);
  }
  for (const id of (params.get('open') ?? '').split(',').filter(Boolean)) {
    const r = racks.racks.find((rk) => rk.id === id);
    if (r) r.door = r.doorTarget = 1.75;
  }

  let lightsOn = true, torchOn = false;
  const setLights = (on) => {
    lightsOn = on;
    for (const l of room.areaLights) l.intensity = on ? l.userData.base : 0;
    room.lightMat.emissiveIntensity = on ? 9 : 0;
    room.hemi.intensity = on ? 0.55 : 0.02;
    scene.environmentIntensity = on ? 0.85 : 0.04;
    for (const s of emergency) s.intensity = on ? 0 : 3.5;
    racks.ledMesh.material.uniforms.uGain.value = on ? 1 : 1.35;
  };
  const setTorch = (on) => { torchOn = on; torch.intensity = on ? 45 : 0; };
  if (params.get('lights') === 'off') setLights(false);
  if (params.get('torch') === '1') setTorch(true);

  const raycaster = new THREE.Raycaster();
  const center = new THREE.Vector2(0, 0);
  let target = null;
  const _h = new THREE.Vector3();

  const describe = (t) => {
    if (!t) return null;
    if (t.kind === 'crac') {
      return { title: t.name, chip: 'RUNNING', chipKind: 'ok', lines: ['Downflow DX precision cooling', `Supply ${t.sup.toFixed(1)} °C  ·  Return ${t.ret.toFixed(1)} °C`, 'Fan 68%  ·  RH 46%'] };
    }
    if (t.kind === 'epo') {
      return { title: 'Emergency Power Off', chip: 'ARMED', chipKind: 'crit', lines: ['Drops every UPS output in the hall', 'Use only for fire or electrocution'] };
    }
    const d = t.device;
    if (!d) return { title: `Rack ${t.rack.id}`, lines: ['600 × 1200 mm · 42U', t.rack.profile === 'e' ? 'Empty, reserved for install' : `${t.rack.devices.filter((x) => x.def.kind !== 'blank').length} devices`] };
    if (d.def.kind === 'blank') return { title: `Rack ${t.rack.id} · U${d.u}`, lines: ['1U blanking panel', 'Keeps hot exhaust from recirculating'] };
    if (d.def.kind === 'cable') return { title: `Rack ${t.rack.id} · U${d.u}`, lines: ['1U horizontal cable manager'] };
    const span = d.def.u > 1 ? `U${d.u}–U${d.u + d.def.u - 1}` : `U${d.u}`;
    const chip = d.status === 'fault' ? 'FAULT' : d.status === 'warn' ? 'WARM' : 'OK';
    const lines = [d.def.model, `${t.rack.id} · ${span}`];
    if (d.watts) lines.push(`Inlet ${d.temp.toFixed(1)} °C  ·  Draw ${d.status === 'fault' ? Math.round(d.watts * 0.97) : d.watts} W`);
    return { title: d.hostname ?? d.def.model, chip, chipKind: d.status === 'fault' ? 'crit' : d.status === 'warn' ? 'warn' : 'ok', lines, note: d.note };
  };

  const interact = () => {
    if (!target) return;
    if (target.rack) {
      const r = target.rack;
      r.doorTarget = r.doorTarget > 0.5 ? 0 : 1.75;
      audio.click(r.doorTarget > 0.5);
    } else if (target.kind === 'epo') {
      hud.toast('You leave the cover down. EPO would drop the whole hall.');
    }
  };
  player.on('interact', interact);
  player.on('breach', () => heist.tryBreach(target));
  player.on('torch', () => setTorch(!torchOn));
  player.on('lights', () => {
    setLights(!lightsOn);
    if (!lightsOn) hud.toast('Lights off. Emergency fixtures only. Press F for your torch.');
  });
  player.on('mute', () => hud.toast(audio.toggleMute() ? 'Sound off' : 'Sound on', 1500));
  player.on('help', () => hud.toggleHelp());
  let lockRefused = false;
  player.on('lock', (locked) => hud.pause(!locked && player.enabled && !touch && !lockRefused));
  player.on('lockerror', () => {
    if (lockRefused) return;
    lockRefused = true;
    hud.pause(false);
    hud.toast('Hold the mouse button and drag to look around.', 5000);
  });
  document.getElementById('t-use')?.addEventListener('click', interact);
  document.getElementById('t-torch')?.addEventListener('click', () => setTorch(!torchOn));
  document.getElementById('t-lights')?.addEventListener('click', () => setLights(!lightsOn));
  document.getElementById('t-hack')?.addEventListener('click', () => heist.tryBreach(target));
  document.getElementById('help-btn')?.addEventListener('click', () => hud.toggleHelp());

  const pickTarget = () => {
    camera.updateMatrixWorld();
    raycaster.setFromCamera(center, camera);
    const ray = raycaster.ray;
    let best = racks.pick(ray, 3.0);
    let bestD = best ? (best.device?.box ?? best.rack.doorBox).distanceToPoint(ray.origin) : 3.0;
    for (const it of room.interactables) {
      if (ray.intersectBox(it.box, _h)) {
        const d = _h.distanceTo(ray.origin);
        if (d < bestD + 0.05) { bestD = d; best = it; }
      }
    }
    return best;
  };

  const resize = () => {
    renderer.setSize(innerWidth, innerHeight);
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.getDrawingBufferSize(size);
    composer.setSize(innerWidth, innerHeight);
    racks.ledMesh.material.uniforms.uViewportH.value = size.y;
  };
  addEventListener('resize', resize);

  hud.status('Compiling shaders…');
  await nextFrame();
  try { await renderer.compileAsync(scene, camera); } catch { /* compile lazily */ }
  mark('compile');

  // ---- loop ----
  const clock = new THREE.Clock();
  let frames = 0, slow = 0, time = 0, downgrade = gtao ? 0 : 1;
  const step = (dt) => {
    time += dt;
    player.update(dt);
    racks.update(dt, time);
    room.update(dt, player);
    if (player.enabled || cam) {
      target = pickTarget();
      hud.card(describe(target));
      heist.update(dt, time, target, player);
      const r = target?.rack;
      const breachPrompt = heist.prompt(target);
      if (breachPrompt) hud.prompt(breachPrompt, 'R');
      else hud.prompt(
        r ? (r.doorTarget > 0.5 ? `Close door · ${r.id}` : `Open door · ${r.id}`)
        : target?.kind === 'epo' ? 'Lift cover' : null,
        'E',
      );
      tickets.update(target, player);
    }
    audio.listen(camera.position.x, camera.position.y, camera.position.z, player.yaw);
    finish.uniforms.uTime.value = time;
    composer.render(dt);
  };
  const loop = () => {
    const dt = Math.min(0.05, clock.getDelta());
    step(dt);
    // if the device can't hold ~30 fps: first drop ambient occlusion, then resolution
    if (!still && frames > 60 && downgrade < 2) {
      slow = dt > 0.04 ? slow + 1 : Math.max(0, slow - 1);
      if (slow > 90) {
        slow = 0;
        downgrade++;
        if (gtao) { gtao.enabled = false; gtao = null; }
        else downgrade = 2;
        if (downgrade === 2) {
          renderer.setPixelRatio(1);
          composer.setPixelRatio(1);
          resize();
        }
        hud.toast('Reduced effects for smoother motion.', 2500);
      }
    }
    frames++;
    if (frames === 3) { window.__ready = true; mark('3 frames'); }
    if (still && frames >= still) return;
    requestAnimationFrame(loop);
  };

  window.__app = {
    scene, camera, renderer, racks, room, player, heist, setLights, setTorch, composer, stats: racks.stats,
    // test hook: jump the camera and render one frame
    view(x, y, z, yaw, pitch = 0, frames = 2) {
      player.place(x, z, yaw, pitch);
      player.eye = player.fixedEye = y;
      for (let i = 0; i < frames; i++) {
        renderer.info.autoReset = false;
        renderer.info.reset();
        step(1 / 60);
      }
      const r = renderer.info.render;
      renderer.info.autoReset = true;
      return { calls: r.calls, tris: r.triangles };
    },
  };
  window.__stats = { ...racks.stats, calls: 0 };
  requestAnimationFrame(loop);

  const start = () => {
    player.enabled = true;
    hud.enter(touch);
    heist.show();
    audio.start(room.interactables.filter((i) => i.kind === 'crac').map((i) => ({ x: i.box.min.x, z: (i.box.min.z + i.box.max.z) / 2 })));
    if (!touch) {
      try {
        const p = canvas.requestPointerLock?.();
        if (p && p.catch) p.catch(() => player.emit('lockerror'));
      } catch { player.emit('lockerror'); }
    }
    hud.toast('Ticket INC-48213 assigned to you. Check the panel top left.', 5000);
  };
  if (cam) { player.enabled = false; hud.enter(touch); heist.show(); }
  else hud.ready(start);
}

boot().catch((e) => {
  console.error(e);
  hud.status(`Something went wrong while building the hall: ${e.message}`);
});
