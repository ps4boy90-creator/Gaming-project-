/**
 * Three passes: the sky, the farm, and the tape.
 *
 * The scene is lit the way the reference look is lit: almost nothing from the
 * sky, and a handful of warm practical lights that fall off fast. There are no
 * shadow maps. Each vertex instead carries how much sky it can see, which is
 * what keeps moonlight out of the barn and off the porch ceiling; the warm
 * lights are spots aimed away from the walls they hang on.
 *
 * Indoors the same trick needs one more piece. With no shadows, a lamp in the
 * dining room would light the grass outside and the room next door straight
 * through the walls. So every light has a mode: an outdoor light ignores
 * anything inside the house, and an indoor one lights only its own room's
 * rectangle, fading out over a short margin so that it spills a little way
 * through a doorway and no further.
 *
 * The scene pass writes square-rooted colour into an 8-bit target. A night
 * scene lives almost entirely in the bottom tenth of the range, and storing it
 * linearly would leave about twenty levels to draw the whole forest with.
 */

export const MAX_LIGHTS = 12;
export const MAX_PATHS = 6;
export const MAX_PATCHES = 4;
export const MAX_OCCLUDERS = 8;

export const SCENE_VS = `#version 300 es
layout(location=0) in vec3 aPos;
layout(location=1) in vec3 aNor;
layout(location=2) in vec2 aUV;
layout(location=3) in float aLayer;
layout(location=4) in vec3 aCol;
layout(location=5) in vec4 aMisc;   // sky occlusion, emission, sway, kind
uniform mat4 uVP;
uniform float uTime;
out vec3 vPos; out vec3 vNor; out vec2 vUV; out float vLayer; out vec3 vCol; out vec4 vMisc;
void main() {
  vec3 p = aPos;
  float s = aMisc.z;
  if (s > 0.0) {                      // wind: tree tops, grass, the washing
    float ph = uTime * 0.8 + p.x * 0.11 + p.z * 0.13;
    p.x += s * (sin(ph) * 0.22 + sin(ph * 2.7 + 1.7) * 0.07);
    p.z += s * (cos(ph * 0.83) * 0.18);
  }
  vPos = p; vNor = aNor; vUV = aUV; vLayer = aLayer; vCol = aCol; vMisc = aMisc;
  gl_Position = uVP * vec4(p, 1.0);
}`;

export const SCENE_FS = `#version 300 es
precision highp float;
precision highp sampler2DArray;
uniform sampler2DArray uTex;
uniform vec3 uCam, uMoonDir, uMoonCol, uAmbient, uFogCol;
uniform float uFogK, uDirtLayer;
uniform vec4 uLPos[${MAX_LIGHTS}];   // xyz, range
uniform vec4 uLCol[${MAX_LIGHTS}];
uniform vec4 uLDir[${MAX_LIGHTS}];   // xyz, cos of the cone edge (below -1: a point light)
uniform vec4 uLRoom[${MAX_LIGHTS}];  // an indoor light's room, in house space: x0, z0, x1, z1
uniform vec4 uHouse;                // house origin x, z, then cos and sin of its yaw
uniform vec4 uHouseBox;             // half width, half depth, ceiling height
uniform vec4 uLean;                 // the kitchen lean-to, in house space: x0, z0, x1, z1
uniform float uStaticLayer, uTime;
uniform vec4 uTorch;                // on, cos of the cone edge
uniform vec3 uTorchPos, uTorchDir;
uniform vec4 uPath[${MAX_PATHS}];
uniform float uPathW[${MAX_PATHS}];
uniform vec4 uPatch[${MAX_PATCHES}];
uniform vec4 uOccA[${MAX_OCCLUDERS}];   // centre x, centre z, half x, half z
uniform vec4 uOccB[${MAX_OCCLUDERS}];   // cos yaw, sin yaw, bottom, top
uniform int uOccCount;
in vec3 vPos; in vec3 vNor; in vec2 vUV; in float vLayer; in vec3 vCol; in vec4 vMisc;
out vec4 frag;

// How much of this piece of ground is a dirt track. Tracks keep a strip of
// grass down the middle, between the wheel ruts.
float dirtAmount(vec2 p, float n) {
  float m = 0.0;
  for (int i = 0; i < ${MAX_PATHS}; i++) {
    float w = uPathW[i];
    if (w <= 0.0) continue;
    vec2 a = uPath[i].xy, b = uPath[i].zw, ab = b - a;
    float d = length(p - a - ab * clamp(dot(p - a, ab) / dot(ab, ab), 0.0, 1.0));
    float edge = 1.0 - smoothstep(w * 0.5 - 0.45, w * 0.5 + 0.35, d + n * 1.1);
    float strip = w > 2.0 ? mix(0.3, 1.0, smoothstep(0.1, 0.55, d + n * 0.5)) : 1.0;
    m = max(m, edge * strip);
  }
  for (int i = 0; i < ${MAX_PATCHES}; i++) {
    float d = length(p - uPatch[i].xy);
    m = max(m, (1.0 - smoothstep(uPatch[i].z * 0.45, uPatch[i].z, d + n * 2.0)) * 0.9);
  }
  return m;
}

// Does a ray from p along dir pass through any of the shadow boxes? Each is
// turned into its own axes and tested as three pairs of slabs.
float blocked(vec3 p, vec3 dir) {
  for (int i = 0; i < ${MAX_OCCLUDERS}; i++) {
    if (i >= uOccCount) break;
    vec2 d = p.xz - uOccA[i].xy, cs = uOccB[i].xy;
    vec3 o = vec3(d.x * cs.x - d.y * cs.y, p.y, d.x * cs.y + d.y * cs.x);
    vec3 r = vec3(dir.x * cs.x - dir.z * cs.y, dir.y, dir.x * cs.y + dir.z * cs.x);
    r = mix(vec3(1e-5), r, step(vec3(1e-5), abs(r)));
    vec3 lo = vec3(-uOccA[i].z, uOccB[i].z, -uOccA[i].w), hi = vec3(uOccA[i].z, uOccB[i].w, uOccA[i].w);
    vec3 t1 = (lo - o) / r, t2 = (hi - o) / r;
    vec3 tn = min(t1, t2), tf = min(max(t1, t2), vec3(1e4));
    float near = max(max(tn.x, tn.y), tn.z), far = min(min(tf.x, tf.y), tf.z);
    if (far > max(near, 0.03)) return 1.0;
  }
  return 0.0;
}

void main() {
  float kind = vMisc.w;
  vec2 uv = vUV;
  if (abs(vLayer - uStaticLayer) < 0.5) {      // the television: a new frame of snow, twenty times a second
    float f = floor(uTime * 20.0);
    uv = uv * 0.6 + fract(sin(vec2(f, f + 7.0)) * vec2(43758.5, 24634.6));
  }
  vec4 t = texture(uTex, vec3(uv, vLayer));
  if (t.a < 0.5) discard;
  vec3 albedo = t.rgb;
  if (kind > 0.5 && kind < 1.5) {
    float n = texture(uTex, vec3(vUV * 0.21, uDirtLayer)).r * 2.6 - 0.5;
    vec3 dirt = texture(uTex, vec3(vPos.xz / 2.5, uDirtLayer)).rgb;
    albedo = mix(albedo, dirt, dirtAmount(vPos.xz, n));
  }
  albedo *= vCol;

  bool foliage = kind > 1.5;
  float gloss = kind < 0.5 ? kind * 2.5 : 0.0;
  vec3 V = normalize(uCam - vPos);
  vec3 N = normalize(vNor);
  if (!foliage && dot(N, V) < 0.0) N = -N;     // every surface is lit from whichever side is looked at
  float sky = vMisc.x;

  vec2 hd = vPos.xz - uHouse.xy;
  vec2 hl = vec2(hd.x * uHouse.z - hd.y * uHouse.w, hd.x * uHouse.w + hd.y * uHouse.z);
  bool indoors = vPos.y < uHouseBox.z && ((abs(hl.x) < uHouseBox.x && abs(hl.y) < uHouseBox.y)
    || (hl.x > uLean.x && hl.x < uLean.z && hl.y > uLean.y && hl.y < uLean.w));
  if (indoors) sky = min(sky, 0.05);
  vec3 spec = vec3(0.0);

  // Moon shadows, and the dark under anything parked on the grass. Foliage
  // skips both: the cards overlap too much for the cost to buy anything.
  // Indoors there is no moon to block, so those pixels skip the test too.
  float moon = indoors ? 0.0 : 1.0;
  if (!foliage && !indoors) {
    moon = 1.0 - blocked(vPos, uMoonDir);
    sky *= 1.0 - 0.7 * blocked(vPos, vec3(0.0, 1.0, 0.0));
  }
  vec3 light = uAmbient * sky * (0.65 + 0.35 * N.y);
  light += uMoonCol * sky * moon * (foliage ? 0.55 : max(dot(N, uMoonDir), 0.0));

  for (int i = 0; i < ${MAX_LIGHTS}; i++) {
    vec3 d = uLPos[i].xyz - vPos;
    float dist = length(d), range = uLPos[i].w;
    if (dist > range) continue;
    float mode = uLCol[i].w, w = 1.0;
    if (mode > 1.5) {
      if (indoors) continue;
    } else if (mode > 0.5) {
      if (!indoors) continue;
      vec2 q = max(uLRoom[i].xy - hl, hl - uLRoom[i].zw);
      w = 1.0 - smoothstep(0.0, 0.9, max(q.x, q.y));
      if (w <= 0.0) continue;
    }
    vec3 l = d / dist;
    float fall = 1.0 - dist / range;
    float att = fall * fall / (1.0 + dist * dist * 0.12) * w;
    float cone = uLDir[i].w < -1.0 ? 1.0 : smoothstep(uLDir[i].w, uLDir[i].w + 0.4, dot(-l, uLDir[i].xyz));
    float ndl = foliage ? 0.6 : max(dot(N, l) * 0.9 + 0.1, 0.0);
    light += uLCol[i].rgb * att * cone * ndl;
    // A lit room is never black in its corners: a little of every lamp
    // arrives from all directions, standing in for light off the walls.
    if (mode > 0.5 && mode < 1.5) light += uLCol[i].rgb * fall * 0.035 * w;
    spec += uLCol[i].rgb * att * cone * pow(max(dot(N, normalize(l + V)), 0.0), 48.0);
  }

  if (uTorch.x > 0.5) {
    // A cheap torch: a hard-edged disc, brighter toward the middle, with the
    // faint ring every reflector throws.
    vec3 d = vPos - uTorchPos;
    float dist = length(d);
    float c = dot(d / dist, uTorchDir);
    float disc = smoothstep(uTorch.y, uTorch.y + 0.006, c);
    float hot = smoothstep(uTorch.y, 1.0, c);
    float ring = smoothstep(0.012, 0.0, abs(c - (uTorch.y + 0.028))) * 0.25;
    float ndl = foliage ? 0.7 : max(dot(N, -d / dist) * 0.75 + 0.25, 0.0);
    float att = 1.0 / (1.0 + dist * dist * 0.012) * clamp(1.0 - dist / 60.0, 0.0, 1.0);
    vec3 beam = vec3(1.0, 0.93, 0.78) * 2.4 * disc * (0.4 + 0.6 * hot * hot + ring) * att;
    light += beam * ndl;
    spec += beam * pow(max(dot(N, normalize(V - d / dist)), 0.0), 48.0);
  }

  vec3 col = albedo * light + spec * gloss * 0.6 + t.rgb * vCol * vMisc.y * 1.5;

  float dist = length(vPos - uCam);
  float fog = 1.0 - exp(-pow(dist * uFogK, 1.5));
  col = mix(col, uFogCol, fog);
  frag = vec4(sqrt(max(col, 0.0)), 1.0);
}`;

/** One triangle that covers the screen; used by the sky and the tape pass. */
export const FULLSCREEN_VS = `#version 300 es
out vec2 vUV;
void main() {
  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  vUV = p;
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}`;

export const SKY_FS = `#version 300 es
precision highp float;
uniform vec3 uFwd, uRight, uUp, uMoonDir, uHorizon, uZenith;
uniform vec2 uTan;
uniform float uTime;
in vec2 vUV;
out vec4 frag;
float hash(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  float a = hash(vec3(i, 1.0)), b = hash(vec3(i + vec2(1, 0), 1.0));
  float c = hash(vec3(i + vec2(0, 1), 1.0)), d = hash(vec3(i + vec2(1, 1), 1.0));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
void main() {
  vec2 ndc = vUV * 2.0 - 1.0;
  vec3 dir = normalize(uFwd + uRight * ndc.x * uTan.x + uUp * ndc.y * uTan.y);
  float h = max(dir.y, 0.0);
  // Lighter at the horizon than overhead: that is what the tree line is cut out of.
  vec3 col = mix(uHorizon, uZenith, pow(h, 0.42));

  // Thin high cloud drifting over, lit from behind by the moon.
  vec2 cp = dir.xz / (dir.y + 0.22) * 1.6 + vec2(uTime * 0.004, 0.0);
  float cloud = noise(cp) * 0.6 + noise(cp * 2.3 + 4.0) * 0.3 + noise(cp * 5.1) * 0.1;
  cloud = smoothstep(0.42, 0.78, cloud) * smoothstep(0.0, 0.25, dir.y);
  float md = max(dot(dir, uMoonDir), 0.0);
  col = mix(col, uHorizon * 0.7 + vec3(0.02, 0.028, 0.045) * pow(md, 8.0) * 0.9, cloud * 0.65);

  // Stars, where the cloud lets them through.
  vec3 q = dir * 260.0, cell = floor(q);
  float star = step(0.9965, hash(cell)) * smoothstep(0.5, 0.0, length(fract(q) - 0.5));
  col += vec3(0.5, 0.56, 0.7) * star * (1.0 - cloud) * smoothstep(0.04, 0.4, dir.y) * 0.35;

  // The moon: a disc, a tight glare, and a wide bloom in the haze.
  col += vec3(0.75, 0.82, 1.0) * (smoothstep(0.99955, 0.9997, md) * 1.6 * (1.0 - cloud * 0.6)
       + pow(md, 900.0) * 0.22 + pow(md, 40.0) * 0.018);
  frag = vec4(sqrt(col), 1.0);
}`;

/** Camera-facing glows on the bare bulbs. */
export const HALO_VS = `#version 300 es
layout(location=0) in vec3 aPos;
layout(location=1) in vec2 aCorner;
layout(location=2) in vec4 aCol;
uniform mat4 uVP;
out vec2 vCorner; out vec4 vCol;
void main() { vCorner = aCorner; vCol = aCol; gl_Position = uVP * vec4(aPos, 1.0); }`;
export const HALO_FS = `#version 300 es
precision highp float;
in vec2 vCorner; in vec4 vCol;
out vec4 frag;
void main() {
  float r = length(vCorner);
  float g = exp(-r * r * 7.0) * 0.9 + exp(-r * 2.6) * 0.16;
  g *= smoothstep(1.0, 0.7, r);
  frag = vec4(vCol.rgb * g * vCol.a, 1.0);
}`;

/**
 * The tape. In order: lens bulge, line jitter, colour resolved far more
 * coarsely than brightness and dragged to the right (which is what VHS
 * actually does, as opposed to splitting the image into red and blue copies),
 * a little glow off the bright lamps, edge ringing, grain in both brightness
 * and colour, a vignette, and blacks lifted off zero into blue.
 */
export const TAPE_FS = `#version 300 es
precision highp float;
uniform sampler2D uScene;
uniform vec2 uRes;       // size of the scene target, in its own pixels
uniform float uTime, uAmount;
in vec2 vUV;
out vec4 frag;
float hash(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
vec3 scene(vec2 uv) { vec3 c = texture(uScene, uv).rgb; return c * c; }
const mat3 RGB2YIQ = mat3(0.299, 0.596, 0.211, 0.587, -0.274, -0.523, 0.114, -0.322, 0.312);
const mat3 YIQ2RGB = mat3(1.0, 1.0, 1.0, 0.956, -0.272, -1.106, 0.621, -0.647, 1.703);
void main() {
  vec2 uv = vUV;
  if (uAmount <= 0.0) { frag = vec4(pow(scene(uv), vec3(1.0 / 2.2)), 1.0); return; }

  vec2 c = uv - 0.5;
  uv = 0.5 + c * (1.0 + dot(c, c) * 0.07) * 0.985;
  float line = floor(uv.y * uRes.y);
  float frame = floor(uTime * 30.0);
  uv.x += (hash(vec2(line, frame)) - 0.5) * 0.0007 * uAmount;
  // A band of mistracking that wanders up the picture now and then.
  float roll = fract(uTime * 0.045);
  float tear = smoothstep(0.016, 0.0, abs(uv.y - (1.1 - roll * 4.0))) * step(roll, 0.3);
  uv.x += tear * (hash(vec2(line, frame + 7.0)) - 0.5) * 0.012 * uAmount;

  vec2 px = 1.0 / uRes;
  vec3 sharp = scene(uv) * 0.5 + scene(uv + vec2(px.x, 0.0)) * 0.25 + scene(uv - vec2(px.x, 0.0)) * 0.25;
  vec3 smear = vec3(0.0);
  for (int i = 0; i < 7; i++) smear += scene(uv + vec2((float(i) - 4.0) * 1.6 * px.x, 0.0));
  smear /= 7.0;
  vec3 yiq = RGB2YIQ * sharp;
  yiq.yz = (RGB2YIQ * smear).yz * 1.12;
  // Ringing: a dark fringe leading each bright edge.
  float ahead = dot(scene(uv + vec2(px.x * 2.5, 0.0)), vec3(0.299, 0.587, 0.114));
  yiq.x += (yiq.x - ahead) * 0.22 * uAmount;
  vec3 col = YIQ2RGB * yiq;

  // Glow: bright things bleed into the dark round them.
  vec3 glow = vec3(0.0);
  for (int i = 0; i < 12; i++) {
    float a = float(i) * 2.399963, r = sqrt(float(i) + 0.5) * 3.2;
    glow += max(scene(uv + vec2(cos(a), sin(a)) * r * px) - 0.18, 0.0);
  }
  col += glow / 12.0 * 0.7;

  col = pow(max(col, 0.0), vec3(1.0 / 2.2));

  float g = hash(vec2(floor(uv.x * uRes.x), line) + frame * 17.0) - 0.5;
  float gc = hash(vec2(floor(uv.x * uRes.x * 0.5), line) + frame * 29.0) - 0.5;
  col += (g * 0.07 + vec3(gc, -gc * 0.5, -gc) * 0.035) * uAmount * (0.55 + 0.45 * (1.0 - dot(col, vec3(0.33))));
  col += tear * 0.05 * hash(vec2(uv.x * 90.0, line + frame));

  col *= 1.0 - 0.04 * uAmount * mod(line, 2.0);
  col *= mix(1.0, smoothstep(1.05, 0.25, length(c * vec2(1.0, 0.9))), 0.75 * uAmount);
  col = col * 0.97 + vec3(0.007, 0.011, 0.022) * uAmount;
  frag = vec4(col, 1.0);
}`;
