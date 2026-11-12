/**
 * Boot, render loop and input for the farm.
 *
 * A frame is: sky, then the whole farm in one draw call, then glows on the
 * bare bulbs, all into a 480-line target; then the tape pass takes that to the
 * screen. The low internal resolution is part of the look, not an economy --
 * a camcorder resolves about that much, and the softness is what lets hard
 * low-poly edges pass for something photographed.
 */
import { paintLayers, LAYERS, L, SIZE } from './textures.js';
import { build, SPAWN, SITE, PATHS, PATCHES, insideBarn, floorHeight, inBounds } from './world.js';
import { STRIDE } from './geom.js';
import { Player } from './player.js';
import { Ambience } from './audio.js';
import {
  SCENE_VS, SCENE_FS, FULLSCREEN_VS, SKY_FS, HALO_VS, HALO_FS, TAPE_FS,
  MAX_LIGHTS, MAX_PATHS, MAX_PATCHES,
} from './shaders.js';
import { perspective, viewMatrix, cameraBasis, mul, normalize } from './math.js';

const SCENE_HEIGHT = 540;
const FOV = (64 * Math.PI) / 180;

// Linear-light colours. The horizon is the brightest thing in the sky and the
// fog fades to exactly that, so distant trees dissolve into it instead of
// ending in a line.
const MOON_DIR = normalize([0.42, 0.52, -0.75]);
const MOON_COL = [0.043, 0.062, 0.108];
const AMBIENT = [0.0078, 0.0117, 0.0225];
const HORIZON = [0.0027, 0.0048, 0.0105];
// Fog is darker than the sky it fades toward, so a far tree line stays a
// silhouette against the horizon instead of melting into it.
const FOG_COL = [0.0021, 0.0038, 0.0085];
const ZENITH = [0.0007, 0.0013, 0.0037];
const FOG_K = 1 / 150;

function program(gl, vs, fs) {
  const p = gl.createProgram();
  for (const [type, src] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    gl.attachShader(p, s);
  }
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  const u = {};
  const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < n; i++) {
    const name = gl.getActiveUniform(p, i).name.replace(/\[0\]$/, '');
    u[name] = gl.getUniformLocation(p, name);
  }
  return { p, u };
}

/** Deterministic 1D noise for the lamp's flicker. */
function flicker(t) {
  const h = (n) => { const s = Math.sin(n * 127.1) * 43758.5453; return s - Math.floor(s); };
  const dip = h(Math.floor(t * 11)) > 0.93 ? 0.45 : 0;
  return 1 - dip - 0.06 * h(Math.floor(t * 47));
}

export class Farm {
  constructor(canvas, opts = {}) {
    this.canvas = canvas;
    this.opts = opts;
    this.state = 'loading';
    this.torch = !!opts.torch;
    this.tape = opts.tape === undefined ? 1 : opts.tape;
    this.frozen = opts.time;                 // fixed clock, for repeatable captures
    this.time = opts.time || 0;
    this.keys = new Set();
    this.audio = new Ambience();
  }

  boot() {
    const gl = (this.gl = this.canvas.getContext('webgl2', { antialias: false, alpha: false }));
    if (!gl) { this.state = 'error'; this.error = 'This scene needs WebGL 2.'; return; }

    // Textures: one array, mipmapped, filtered smoothly.
    const pixels = paintLayers();
    this.tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D_ARRAY, this.tex);
    gl.texStorage3D(gl.TEXTURE_2D_ARRAY, Math.log2(SIZE) + 1, gl.SRGB8_ALPHA8, SIZE, SIZE, LAYERS.length);
    pixels.forEach((px, i) => gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, i, SIZE, SIZE, 1, gl.RGBA, gl.UNSIGNED_BYTE, px));
    gl.generateMipmap(gl.TEXTURE_2D_ARRAY);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    const aniso = gl.getExtension('EXT_texture_filter_anisotropic');
    if (aniso) gl.texParameterf(gl.TEXTURE_2D_ARRAY, aniso.TEXTURE_MAX_ANISOTROPY_EXT, 4);

    const world = (this.world = build());
    this.player = new Player(startPose(this.opts) || SPAWN);
    this.player.onStep = (surface, run) => this.audio.step(surface, run);
    this.lamp = world.lights.find((l) => l.flicker);

    this.vao = gl.createVertexArray();
    gl.bindVertexArray(this.vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, world.vertices, gl.STATIC_DRAW);
    const B = STRIDE * 4;
    [[0, 3, 0], [1, 3, 12], [2, 2, 24], [3, 1, 32], [4, 3, 36], [5, 4, 48]].forEach(([loc, size, off]) => {
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, B, off);
    });

    this.haloVao = gl.createVertexArray();
    gl.bindVertexArray(this.haloVao);
    this.haloBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.haloBuf);
    [[0, 3, 0], [1, 2, 12], [2, 4, 20]].forEach(([loc, size, off]) => {
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 36, off);
    });
    this.emptyVao = gl.createVertexArray();
    gl.bindVertexArray(null);

    this.scene = program(gl, SCENE_VS, SCENE_FS);
    this.sky = program(gl, FULLSCREEN_VS, SKY_FS);
    this.halo = program(gl, HALO_VS, HALO_FS);
    this.tapeProg = program(gl, FULLSCREEN_VS, TAPE_FS);

    // The tracks never move, so they are handed to the shader once.
    const paths = new Float32Array(MAX_PATHS * 4), widths = new Float32Array(MAX_PATHS);
    PATHS.slice(0, MAX_PATHS).forEach((p, i) => { paths.set(p.slice(0, 4), i * 4); widths[i] = p[4]; });
    const patches = new Float32Array(MAX_PATCHES * 4);
    PATCHES.slice(0, MAX_PATCHES).forEach((p, i) => patches.set([p[0], p[1], p[2], 0], i * 4));
    gl.useProgram(this.scene.p);
    gl.uniform4fv(this.scene.u.uPath, paths);
    gl.uniform1fv(this.scene.u.uPathW, widths);
    gl.uniform4fv(this.scene.u.uPatch, patches);
    this.lightBuf = { pos: new Float32Array(MAX_LIGHTS * 4), col: new Float32Array(MAX_LIGHTS * 4), dir: new Float32Array(MAX_LIGHTS * 4) };

    // Drawn multisampled, then resolved into a texture the tape pass can read.
    // Smoothing the polygon edges matters more here than it usually would:
    // stair-stepped roof lines are the quickest way for this to look like a
    // 3D render instead of footage.
    this.target = {
      draw: gl.createFramebuffer(), msColor: gl.createRenderbuffer(), depth: gl.createRenderbuffer(),
      fbo: gl.createFramebuffer(), color: gl.createTexture(), w: 0, h: 0,
    };
    this.resize();
    this.bind();
    this.state = this.opts.autostart ? 'playing' : 'title';
    this.last = performance.now();
    if (!this.opts.manual) requestAnimationFrame((t) => this.frame(t));
  }

  resize() {
    const { gl, canvas, target } = this;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cw = Math.max(2, Math.round(canvas.clientWidth * dpr)), ch = Math.max(2, Math.round(canvas.clientHeight * dpr));
    if (canvas.width !== cw || canvas.height !== ch) { canvas.width = cw; canvas.height = ch; }
    const h = SCENE_HEIGHT, w = Math.round((h * cw) / ch / 2) * 2;
    if (target.w === w && target.h === h) return;
    Object.assign(target, { w, h });
    gl.bindTexture(gl.TEXTURE_2D, target.color);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
    const samples = Math.min(4, gl.getParameter(gl.MAX_SAMPLES));
    gl.bindRenderbuffer(gl.RENDERBUFFER, target.msColor);
    gl.renderbufferStorageMultisample(gl.RENDERBUFFER, samples, gl.RGBA8, w, h);
    gl.bindRenderbuffer(gl.RENDERBUFFER, target.depth);
    gl.renderbufferStorageMultisample(gl.RENDERBUFFER, samples, gl.DEPTH_COMPONENT24, w, h);
    gl.bindFramebuffer(gl.FRAMEBUFFER, target.draw);
    gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.RENDERBUFFER, target.msColor);
    gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, target.depth);
    gl.bindFramebuffer(gl.FRAMEBUFFER, target.fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, target.color, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  bind() {
    const c = this.canvas;
    window.addEventListener('resize', () => this.resize());
    window.addEventListener('keydown', (e) => {
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(e.code)) e.preventDefault();
      if (e.repeat) return;
      this.keys.add(e.code);
      if (e.code === 'KeyF') this.torch = !this.torch;
      if (e.code === 'KeyV') this.tape = this.tape ? 0 : 1;
    });
    window.addEventListener('keyup', (e) => this.keys.delete(e.code));
    window.addEventListener('blur', () => this.keys.clear());
    c.addEventListener('click', () => {
      this.audio.start();
      if (this.state === 'title') this.state = 'playing';
      if (c.requestPointerLock && document.pointerLockElement !== c) c.requestPointerLock();
    });
    document.addEventListener('mousemove', (e) => {
      if (document.pointerLockElement !== c) return;
      this.player.look(-e.movementX * 0.0022, -e.movementY * 0.0022);
    });
  }

  /** Advance the simulation. Split from drawing so tests can step it exactly. */
  step(dt, move, run) {
    if (this.frozen === undefined) this.time += dt;
    this.player.update(dt, move, run, this.world);
    const lamp = this.lamp.pos;
    this.audio.update(dt, {
      inside: insideBarn(this.player.x, this.player.z),
      lampDistance: Math.hypot(this.player.x - lamp[0], this.player.z - lamp[2]),
    });
  }

  frame(now) {
    const dt = Math.min(0.05, (now - this.last) / 1000);
    this.last = now;
    const k = this.keys, has = (...c) => c.some((x) => k.has(x));
    if (this.state === 'playing') {
      const turn = (has('ArrowLeft') ? 1 : 0) - (has('ArrowRight') ? 1 : 0);
      if (turn) this.player.look(turn * 1.8 * dt, 0);
      this.step(dt, {
        fwd: (has('KeyW', 'ArrowUp') ? 1 : 0) - (has('KeyS', 'ArrowDown') ? 1 : 0),
        strafe: (has('KeyD') ? 1 : 0) - (has('KeyA') ? 1 : 0),
      }, has('ShiftLeft', 'ShiftRight'));
    } else if (this.frozen === undefined) {
      this.time += dt;
    }
    this.render();
    requestAnimationFrame((t) => this.frame(t));
  }

  render() {
    const { gl, target, world, player } = this;
    const eye = player.eye, t = this.time;
    const aspect = target.w / target.h;
    const proj = perspective(FOV, aspect, 0.08, 600);
    const vp = mul(proj, viewMatrix(eye, player.yaw, player.pitch));
    const cam = cameraBasis(player.yaw, player.pitch);
    const tan = Math.tan(FOV / 2);
    const lampNow = flicker(t);

    gl.bindFramebuffer(gl.FRAMEBUFFER, target.draw);
    gl.viewport(0, 0, target.w, target.h);
    gl.disable(gl.BLEND);
    gl.disable(gl.CULL_FACE);
    gl.depthMask(true);
    gl.clear(gl.DEPTH_BUFFER_BIT);

    // Sky.
    gl.disable(gl.DEPTH_TEST);
    gl.useProgram(this.sky.p);
    gl.bindVertexArray(this.emptyVao);
    let u = this.sky.u;
    gl.uniform3fv(u.uFwd, cam.fwd); gl.uniform3fv(u.uRight, cam.right); gl.uniform3fv(u.uUp, cam.up);
    gl.uniform3fv(u.uMoonDir, MOON_DIR); gl.uniform3fv(u.uHorizon, HORIZON); gl.uniform3fv(u.uZenith, ZENITH);
    gl.uniform2f(u.uTan, tan * aspect, tan);
    gl.uniform1f(u.uTime, t);
    gl.drawArrays(gl.TRIANGLES, 0, 3);

    // The farm.
    gl.enable(gl.DEPTH_TEST);
    gl.useProgram(this.scene.p);
    gl.bindVertexArray(this.vao);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D_ARRAY, this.tex);
    u = this.scene.u;
    gl.uniformMatrix4fv(u.uVP, false, vp);
    gl.uniform1i(u.uTex, 0);
    gl.uniform1f(u.uTime, t);
    gl.uniform3fv(u.uCam, eye);
    gl.uniform3fv(u.uMoonDir, MOON_DIR); gl.uniform3fv(u.uMoonCol, MOON_COL);
    gl.uniform3fv(u.uAmbient, AMBIENT); gl.uniform3fv(u.uFogCol, FOG_COL);
    gl.uniform1f(u.uFogK, FOG_K);
    gl.uniform1f(u.uDirtLayer, L.dirt);
    const { pos: lp, col: lc, dir: ld } = this.lightBuf;
    world.lights.slice(0, MAX_LIGHTS).forEach((l, i) => {
      const k = l.flicker ? lampNow : 1;
      lp.set([...l.pos, l.range], i * 4);
      lc.set([l.color[0] * k, l.color[1] * k, l.color[2] * k, 0], i * 4);
      ld.set([...l.dir, l.cos], i * 4);
    });
    gl.uniform4fv(u.uLPos, lp); gl.uniform4fv(u.uLCol, lc); gl.uniform4fv(u.uLDir, ld);
    // The torch is held low and to the right, so its disc sits off-centre up close.
    const hand = [eye[0] + cam.right[0] * 0.22 - cam.up[0] * 0.2, eye[1] + cam.right[1] * 0.22 - cam.up[1] * 0.2, eye[2] + cam.right[2] * 0.22 - cam.up[2] * 0.2];
    gl.uniform4f(u.uTorch, this.torch ? 1 : 0, Math.cos(0.3), 0, 0);
    gl.uniform3fv(u.uTorchPos, hand); gl.uniform3fv(u.uTorchDir, cam.fwd);
    gl.drawArrays(gl.TRIANGLES, 0, world.vertexCount);

    // Glows.
    const hv = [];
    for (const h of world.halos) {
      const s = h.size, k = h.flicker ? lampNow : 1;
      for (const [cx, cy] of [[-1, -1], [1, -1], [1, 1], [-1, -1], [1, 1], [-1, 1]]) {
        hv.push(
          h.pos[0] + (cam.right[0] * cx + cam.up[0] * cy) * s,
          h.pos[1] + (cam.right[1] * cx + cam.up[1] * cy) * s,
          h.pos[2] + (cam.right[2] * cx + cam.up[2] * cy) * s,
          cx, cy, h.color[0], h.color[1], h.color[2], 0.55 * k,
        );
      }
    }
    gl.useProgram(this.halo.p);
    gl.bindVertexArray(this.haloVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.haloBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(hv), gl.DYNAMIC_DRAW);
    gl.uniformMatrix4fv(this.halo.u.uVP, false, vp);
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE); gl.depthMask(false);
    gl.drawArrays(gl.TRIANGLES, 0, hv.length / 9);
    gl.depthMask(true); gl.disable(gl.BLEND);

    gl.bindFramebuffer(gl.READ_FRAMEBUFFER, target.draw);
    gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, target.fbo);
    gl.blitFramebuffer(0, 0, target.w, target.h, 0, 0, target.w, target.h, gl.COLOR_BUFFER_BIT, gl.NEAREST);

    // Tape, to the screen.
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.disable(gl.DEPTH_TEST);
    gl.useProgram(this.tapeProg.p);
    gl.bindVertexArray(this.emptyVao);
    gl.bindTexture(gl.TEXTURE_2D, target.color);
    u = this.tapeProg.u;
    gl.uniform1i(u.uScene, 0);
    gl.uniform2f(u.uRes, target.w, target.h);
    gl.uniform1f(u.uTime, t);
    gl.uniform1f(u.uAmount, this.tape);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  /**
   * Draw a frame and measure it, in display values: mean brightness, the
   * share of pixels under 10%, the 95th percentile, and the hue of the mean
   * colour. These are the numbers the look is tuned against.
   */
  measure() {
    const { gl, canvas } = this;
    this.render();
    const px = new Uint8Array(canvas.width * canvas.height * 4);
    gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, px);
    const n = px.length / 4, hist = new Uint32Array(256);
    let sum = 0, dark = 0, r = 0, g = 0, b = 0;
    for (let i = 0; i < px.length; i += 4) {
      const y = 0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2];
      sum += y; hist[y | 0]++; if (y < 25.5) dark++;
      r += px[i]; g += px[i + 1]; b += px[i + 2];
    }
    let acc = 0, p95 = 0;
    for (let i = 0; i < 256; i++) { acc += hist[i]; if (acc >= n * 0.95) { p95 = i; break; } }
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn || 1;
    let hue = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    hue = (hue * 60 + 360) % 360;
    return { mean: sum / n / 255, dark: dark / n, p95: p95 / 255, hue };
  }

  /** Put the camera somewhere exactly: used by ?pose= and by the test harness. */
  setPose(x, z, yaw, pitch = 0) {
    Object.assign(this.player, { x, z, yaw, pitch, vx: 0, vz: 0, floor: floorHeight(x, z) });
  }
  /** World queries, exposed for the console and the tests. */
  get query() { return { insideBarn, floorHeight, inBounds }; }
  get site() { return SITE; }
}

function startPose(o) {
  return o.pose ? { x: o.pose[0], z: o.pose[1], yaw: o.pose[2] || 0, pitch: o.pose[3] || 0 } : null;
}
