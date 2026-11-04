import * as THREE from 'three';
import { SIMPLEX, FAR_VERTEX } from './noise.glsl';

/*  KX-7c "Verdance" seen from a 410 km orbit, plus its moons, the sun and the stars.
 *  The surface and cloud deck are baked once into cubemaps at boot, then sampled cheaply.
 *  Everything lives in a group that follows the camera and draws at the far plane. */

const R = 1000; // planet radius in backdrop units
const ANG = THREE.MathUtils.degToRad(58); // angular radius seen from orbit
const DIST = R / Math.sin(ANG);
const PERIOD = 40 * 60; // seconds per orbit (real time)
const BETA = THREE.MathUtils.degToRad(40);

const SURFACE_BAKE = /* glsl */ `
varying vec3 vDir;
void main(){
  vec3 p = normalize(vDir);
  vec3 warp = p + 0.35*vec3(snoise(p*1.3+3.0), snoise(p*1.3+11.0), snoise(p*1.3+19.0));
  float h = fbm(warp*1.4, 8) + 0.32*ridged(p*3.0, 6) - 0.13;
  float lat = abs(p.y);
  float moist = fbm(p*2.6 + 40.0, 5);
  float land = smoothstep(0.0, 0.015, h);
  vec3 deep = vec3(0.004,0.018,0.032);
  vec3 shallow = vec3(0.012,0.065,0.075);
  vec3 ocean = mix(deep, shallow, smoothstep(-0.22, 0.0, h));
  vec3 gold = vec3(0.34,0.23,0.075);
  vec3 dry = vec3(0.22,0.17,0.09);
  vec3 forest = vec3(0.035,0.065,0.03);
  vec3 rock = vec3(0.045,0.042,0.04);
  vec3 snow = vec3(0.72,0.76,0.8);
  float grassVar = fbm(p*11.0+5.0, 4);
  vec3 col = mix(gold, dry, smoothstep(-0.2, 0.4, grassVar));
  col = mix(col, forest, smoothstep(-0.05, 0.22, moist));
  col = mix(col, rock, smoothstep(0.32, 0.58, h + grassVar*0.05));
  col = mix(col, snow, smoothstep(0.8, 0.93, lat + h*0.18));
  float bloom = smoothstep(0.55, 0.78, fbm(p*7.0+80.0, 4)*0.5+0.5) * smoothstep(0.0, 0.3, moist);
  col = mix(col, vec3(0.2,0.21,0.18), bloom*0.45);
  // rivers: thin ridged lines in the lowlands
  float river = smoothstep(0.93, 0.985, ridged(p*6.0+21.0, 3)) * land * (1.0 - smoothstep(0.1, 0.3, h));
  col = mix(col, shallow*1.4, river*0.8);
  vec3 albedo = mix(ocean, col, land);
  albedo = mix(albedo, snow, smoothstep(0.87, 0.96, lat));
  float veins = pow(clamp(ridged(p*9.0 + 5.0, 5), 0.0, 1.0), 3.0) * smoothstep(0.0, 0.4, moist);
  float a = land > 0.5 ? 0.5 + 0.5*clamp(veins, 0.0, 1.0) : 0.0;
  gl_FragColor = vec4(sqrt(albedo), a);
}`;

const CLOUD_BAKE = /* glsl */ `
varying vec3 vDir;
void main(){
  vec3 q = normalize(vDir);
  vec3 w = q*2.2 + 0.55*vec3(snoise(q*1.7+1.0), snoise(q*1.7+7.0), snoise(q*1.7+13.0));
  float c = fbm(w*1.6, 7)*0.5+0.5;
  float lat = q.y;
  float bands = 0.5+0.5*sin(lat*11.0 + snoise(q*3.0)*2.5);
  c = c*0.82 + bands*0.14;
  // a few cyclones
  for (int i = 0; i < 3; i++) {
    vec3 cc = normalize(vec3(sin(float(i)*2.4+0.7), 0.35*cos(float(i)*3.1), cos(float(i)*2.4+0.7)));
    float d = acos(clamp(dot(q, cc), -1.0, 1.0));
    float swirl = smoothstep(0.35, 0.0, d);
    float ang = atan(dot(cross(cc, q), vec3(0.0,1.0,0.0)), dot(q - cc*dot(q,cc), vec3(1.0,0.0,0.0)));
    c += swirl * 0.25 * (0.5 + 0.5*sin(ang*2.0 + d*40.0));
  }
  float dens = smoothstep(0.55, 0.86, c);
  float fine = fbm(q*24.0, 3)*0.5+0.5;
  dens *= 0.75 + 0.35*fine;
  gl_FragColor = vec4(clamp(dens,0.0,1.0), fine, 0.0, 1.0);
}`;

function bakeCube(renderer: THREE.WebGLRenderer, frag: string, size: number): THREE.CubeTexture {
  const rt = new THREE.WebGLCubeRenderTarget(size, {
    type: THREE.UnsignedByteType,
    generateMipmaps: true,
    minFilter: THREE.LinearMipmapLinearFilter,
    magFilter: THREE.LinearFilter,
  });
  const cam = new THREE.CubeCamera(0.1, 10, rt);
  const scene = new THREE.Scene();
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthTest: false,
    depthWrite: false,
    vertexShader: 'varying vec3 vDir; void main(){ vDir = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: SIMPLEX + frag,
  });
  scene.add(new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), mat));
  const prevTarget = renderer.getRenderTarget();
  const prevTone = renderer.toneMapping;
  renderer.toneMapping = THREE.NoToneMapping;
  cam.update(renderer, scene);
  renderer.toneMapping = prevTone;
  renderer.setRenderTarget(prevTarget);
  mat.dispose();
  return rt.texture as unknown as THREE.CubeTexture;
}

const PLANET_FRAG = /* glsl */ `
uniform samplerCube uSurface;
uniform samplerCube uClouds;
uniform vec3 uSunDir;
uniform mat3 uRot;
uniform mat3 uCloudRot;
uniform float uDetail;
varying vec3 vN;
varying vec3 vW;
varying vec3 vL;
void main(){
  vec3 N = normalize(vN);
  vec3 p = uRot * N;
  vec3 V = normalize(cameraPosition - vW);
  vec4 s = textureCube(uSurface, p);
  vec3 albedo = s.rgb * s.rgb;
  float land = step(0.25, s.a);
  float glow = max(s.a - 0.5, 0.0) * 2.0;
  if (uDetail > 0.0) {
    float d = snoise(p * 160.0) * 0.5 + snoise(p * 420.0) * 0.3 + snoise(p * 1100.0) * 0.2;
    albedo *= 1.0 + d * 0.45 * uDetail * (0.4 + land);
  }
  float ndl = dot(N, uSunDir);
  float diff = max(ndl, 0.0);
  float day = smoothstep(-0.12, 0.12, ndl);
  float cs = textureCube(uClouds, uCloudRot * normalize(N + uSunDir * 0.01)).r;
  vec3 lit = albedo * diff * 2.1 * (1.0 - cs * 0.6);
  vec3 H = normalize(uSunDir + V);
  float spec = pow(max(dot(N, H), 0.0), 500.0) * (1.0 - land) * 2.4 * diff * (1.0 - cs);
  lit += vec3(1.0, 0.86, 0.62) * spec;
  float term = smoothstep(0.28, 0.0, ndl) * day;
  lit *= mix(vec3(1.0), vec3(1.3, 0.62, 0.36), term * 0.85);
  lit += vec3(0.04, 0.15, 0.1) * glow * (1.0 - day) * 0.35;
  float mu = max(dot(N, V), 0.0);
  float rim = pow(1.0 - mu, 3.0);
  float scatter = smoothstep(-0.25, 0.45, ndl);
  vec3 sky = vec3(0.2, 0.44, 0.95);
  lit = mix(lit, sky * 1.4 * scatter, rim * 0.68);
  lit += sky * 0.05 * scatter;
  gl_FragColor = vec4(lit, 1.0);
}`;

const CLOUD_FRAG = /* glsl */ `
uniform samplerCube uClouds;
uniform vec3 uSunDir;
uniform mat3 uCloudRot;
varying vec3 vN;
varying vec3 vW;
varying vec3 vL;
void main(){
  vec3 N = normalize(vN);
  vec4 c = textureCube(uClouds, uCloudRot * N);
  float d = c.r;
  float ndl = dot(N, uSunDir);
  float diff = max(ndl, 0.0);
  float day = smoothstep(-0.15, 0.1, ndl);
  vec3 col = vec3(0.92, 0.94, 0.96) * (diff * 1.9 * (0.7 + 0.3 * c.g) + 0.015);
  float term = smoothstep(0.3, 0.0, ndl) * day;
  col *= mix(vec3(1.0), vec3(1.35, 0.6, 0.35), term);
  vec3 V = normalize(cameraPosition - vW);
  float rim = pow(1.0 - max(dot(N, V), 0.0), 2.5);
  gl_FragColor = vec4(col, d * (1.0 - rim * 0.6));
}`;

const ATMO_FRAG = /* glsl */ `
uniform vec3 uSunDir;
uniform vec3 uCenter;
uniform float uR;
varying vec3 vN;
varying vec3 vW;
varying vec3 vL;
void main(){
  vec3 rd = normalize(vW - cameraPosition);
  vec3 oc = uCenter - cameraPosition;
  float t = dot(oc, rd);
  vec3 closest = cameraPosition + rd * t;
  float d = length(closest - uCenter);
  float h = (d - uR) / (uR * 0.022);
  float inten = d > uR ? exp(-h) : 0.0;
  vec3 cd = normalize(closest - uCenter);
  float sl = dot(cd, uSunDir);
  float lit = smoothstep(-0.35, 0.35, sl);
  vec3 col = mix(vec3(1.0, 0.45, 0.2), vec3(0.3, 0.55, 1.0), smoothstep(-0.1, 0.4, sl));
  gl_FragColor = vec4(col * inten * lit * 1.6, 1.0);
}`;

const SUN_FRAG = /* glsl */ `
varying vec2 vUv;
void main(){
  float r = length(vUv - 0.5) * 2.0;
  float core = smoothstep(0.12, 0.09, r) * 60.0;
  float glow = exp(-r * 6.0) * 4.0 + exp(-r * 2.2) * 0.6;
  vec3 col = vec3(1.0, 0.93, 0.82) * (core + glow);
  gl_FragColor = vec4(col, 1.0);
}`;

const MOON_FRAG = /* glsl */ `
uniform vec3 uSunDir;
uniform float uSeed;
uniform vec3 uTint;
varying vec3 vN;
varying vec3 vW;
varying vec3 vL;
void main(){
  vec3 N = normalize(vN);
  vec3 p = normalize(vL) * 3.0 + uSeed;
  float mare = smoothstep(0.1, 0.5, fbm(p * 0.7, 4));
  float craters = ridged(p * 2.5, 4);
  vec3 alb = uTint * (0.55 - mare * 0.25 + craters * 0.12);
  float diff = max(dot(N, uSunDir), 0.0);
  gl_FragColor = vec4(alb * diff * 2.0 + alb * 0.01, 1.0);
}`;

const STAR_VERT = /* glsl */ `
attribute float aSize;
attribute vec3 aColor;
varying vec3 vColor;
uniform float uPixel;
void main(){
  vColor = aColor;
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  gl_Position.z = gl_Position.w * 0.9999995;
  gl_PointSize = aSize * uPixel;
}`;

const STAR_FRAG = /* glsl */ `
varying vec3 vColor;
void main(){
  vec2 c = gl_PointCoord - 0.5;
  float a = exp(-dot(c, c) * 18.0);
  gl_FragColor = vec4(vColor * a, 1.0);
}`;

const SKY_FRAG = /* glsl */ `
varying vec3 vN;
varying vec3 vW;
varying vec3 vL;
void main(){
  vec3 d = normalize(vL);
  vec3 axis = normalize(vec3(0.3, 0.85, -0.42));
  float band = exp(-pow(dot(d, axis) * 3.2, 2.0));
  float n = fbm(d * 3.0, 5) * 0.5 + 0.5;
  float dust = smoothstep(0.45, 0.75, fbm(d * 6.0 + 9.0, 4) * 0.5 + 0.5);
  vec3 col = vec3(0.05, 0.055, 0.075) * band * n * (1.0 - dust * 0.7);
  col += vec3(0.008, 0.009, 0.014);
  gl_FragColor = vec4(col * 0.6, 1.0);
}`;

function rotAround(axis: THREE.Vector3, angle: number): THREE.Matrix3 {
  const m4 = new THREE.Matrix4().makeRotationAxis(axis, angle);
  return new THREE.Matrix3().setFromMatrix4(m4);
}

export class OrbitView {
  group = new THREE.Group();
  planetDir = new THREE.Vector3(0, Math.sin(THREE.MathUtils.degToRad(-35)), Math.cos(THREE.MathUtils.degToRad(-35))).normalize();
  orbitNormal = new THREE.Vector3();
  sunDir = new THREE.Vector3();
  /** 0..1: how much direct sunlight reaches the ship (0 inside the planet's shadow). */
  sunVisible = 1;
  /** Fraction of the visible disc that is day-lit (for planetshine). */
  litFraction = 1;
  time = 0;
  private sun0 = new THREE.Vector3();
  private moons: { mesh: THREE.Mesh; dir0: THREE.Vector3; dist: number }[] = [];
  private stars: THREE.Points;
  private sky: THREE.Mesh;
  private sun: THREE.Mesh;
  private planetMat: THREE.ShaderMaterial;
  private cloudMat: THREE.ShaderMaterial;
  private atmoMat: THREE.ShaderMaterial;
  private moonMats: THREE.ShaderMaterial[] = [];
  private center = new THREE.Vector3();

  constructor(renderer: THREE.WebGLRenderer, quality: 'low' | 'medium' | 'high') {
    const size = quality === 'low' ? 512 : quality === 'medium' ? 1024 : 1536;
    const surface = bakeCube(renderer, SURFACE_BAKE, size);
    const clouds = bakeCube(renderer, CLOUD_BAKE, Math.min(1024, size));
    this.orbitNormal.crossVectors(this.planetDir.clone().negate(), new THREE.Vector3(1, 0, 0)).normalize();
    const phi = THREE.MathUtils.degToRad(60);
    const inPlane = new THREE.Vector3(1, 0, 0).multiplyScalar(Math.cos(phi)).addScaledVector(this.planetDir.clone().negate(), Math.sin(phi));
    this.sun0.copy(inPlane).multiplyScalar(Math.cos(BETA)).addScaledVector(this.orbitNormal, -Math.sin(BETA)).normalize();

    this.center.copy(this.planetDir).multiplyScalar(DIST);
    const common = { uSunDir: { value: new THREE.Vector3() } };

    // sky + stars first, then sun, moons, planet, clouds, atmosphere (painter's order)
    this.sky = new THREE.Mesh(
      new THREE.SphereGeometry(4800, 48, 24),
      new THREE.ShaderMaterial({ vertexShader: FAR_VERTEX, fragmentShader: SIMPLEX + SKY_FRAG, side: THREE.BackSide, depthWrite: false, transparent: true }),
    );
    this.sky.renderOrder = -10;
    this.group.add(this.sky);

    this.stars = this.makeStars();
    this.stars.renderOrder = -9;
    this.group.add(this.stars);

    this.sun = new THREE.Mesh(
      new THREE.PlaneGeometry(1, 1),
      new THREE.ShaderMaterial({
        vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); gl_Position.z = gl_Position.w * 0.9999995; }',
        fragmentShader: SUN_FRAG,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    );
    this.sun.scale.setScalar(420);
    this.sun.renderOrder = -8;
    this.group.add(this.sun);

    const moonDefs = [
      { dir: new THREE.Vector3(-0.55, 0.4, 0.7), dist: 3600, r: 44, seed: 3, tint: new THREE.Vector3(0.62, 0.6, 0.57) },
      { dir: new THREE.Vector3(0.7, 0.15, 0.55), dist: 3900, r: 20, seed: 11, tint: new THREE.Vector3(0.6, 0.5, 0.42) },
    ];
    for (const m of moonDefs) {
      const mat = new THREE.ShaderMaterial({
        vertexShader: FAR_VERTEX,
        fragmentShader: SIMPLEX + MOON_FRAG,
        uniforms: { uSunDir: common.uSunDir, uSeed: { value: m.seed }, uTint: { value: m.tint } },
        depthWrite: false,
        transparent: true,
      });
      this.moonMats.push(mat);
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(m.r, 32, 20), mat);
      mesh.renderOrder = -7;
      this.group.add(mesh);
      this.moons.push({ mesh, dir0: m.dir.normalize(), dist: m.dist });
    }

    this.planetMat = new THREE.ShaderMaterial({
      vertexShader: FAR_VERTEX,
      fragmentShader: SIMPLEX + PLANET_FRAG,
      uniforms: {
        uDetail: { value: 0 },
        uSurface: { value: surface },
        uClouds: { value: clouds },
        uSunDir: common.uSunDir,
        uRot: { value: new THREE.Matrix3() },
        uCloudRot: { value: new THREE.Matrix3() },
      },
      depthWrite: false,
      transparent: true,
    });
    const planet = new THREE.Mesh(new THREE.SphereGeometry(R, 160, 96), this.planetMat);
    planet.position.copy(this.center);
    planet.renderOrder = -6;
    this.group.add(planet);

    this.cloudMat = new THREE.ShaderMaterial({
      vertexShader: FAR_VERTEX,
      fragmentShader: CLOUD_FRAG,
      uniforms: { uClouds: { value: clouds }, uSunDir: common.uSunDir, uCloudRot: { value: new THREE.Matrix3() } },
      transparent: true,
      depthWrite: false,
    });
    const cloudMesh = new THREE.Mesh(new THREE.SphereGeometry(R * 1.006, 160, 96), this.cloudMat);
    cloudMesh.position.copy(this.center);
    cloudMesh.renderOrder = -5;
    this.group.add(cloudMesh);

    this.atmoMat = new THREE.ShaderMaterial({
      vertexShader: FAR_VERTEX,
      fragmentShader: ATMO_FRAG,
      uniforms: { uSunDir: common.uSunDir, uCenter: { value: new THREE.Vector3() }, uR: { value: R } },
      transparent: true,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide,
      depthWrite: false,
    });
    const atmo = new THREE.Mesh(new THREE.SphereGeometry(R * 1.09, 128, 64), this.atmoMat);
    atmo.position.copy(this.center);
    atmo.renderOrder = -4;
    this.group.add(atmo);

    this.group.traverse((o) => (o.frustumCulled = false));
    this.update(0, new THREE.Vector3());
  }

  private makeStars(): THREE.Points {
    const n = 5200;
    const pos = new Float32Array(n * 3);
    const size = new Float32Array(n);
    const col = new Float32Array(n * 3);
    let s = 12345;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    const axis = new THREE.Vector3(0.3, 0.85, -0.42).normalize();
    for (let i = 0; i < n; i++) {
      let v = new THREE.Vector3();
      // bias a third of the stars toward the galactic band
      for (let tries = 0; tries < 6; tries++) {
        v.set(rnd() * 2 - 1, rnd() * 2 - 1, rnd() * 2 - 1);
        if (v.lengthSq() > 1 || v.lengthSq() < 0.01) continue;
        v.normalize();
        if (i % 3 !== 0 || Math.abs(v.dot(axis)) < 0.25) break;
      }
      v = v.normalize().multiplyScalar(4500);
      pos.set([v.x, v.y, v.z], i * 3);
      const mag = Math.pow(rnd(), 6);
      size[i] = 1.2 + mag * 4.5;
      const temp = rnd();
      const bright = 0.35 + mag * 6;
      const c = temp < 0.15 ? [1.0, 0.75, 0.55] : temp < 0.7 ? [1, 0.96, 0.9] : [0.75, 0.85, 1.0];
      col.set([c[0] * bright, c[1] * bright, c[2] * bright], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
    g.setAttribute('aColor', new THREE.BufferAttribute(col, 3));
    const m = new THREE.ShaderMaterial({
      vertexShader: STAR_VERT,
      fragmentShader: STAR_FRAG,
      uniforms: { uPixel: { value: Math.min(window.devicePixelRatio, 2) } },
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    return new THREE.Points(g, m);
  }

  /** Extra procedural surface detail for the telescope. */
  setDetail(v: number): void {
    this.planetMat.uniforms.uDetail.value = v;
  }

  setPixelRatio(pr: number): void {
    (this.stars.material as THREE.ShaderMaterial).uniforms.uPixel.value = pr;
  }

  /** Advance the orbit; keep the backdrop centred on the camera. */
  update(dt: number, camPos: THREE.Vector3): void {
    this.time += dt;
    const w = (Math.PI * 2) / PERIOD;
    const a = w * this.time;
    const Q = new THREE.Quaternion().setFromAxisAngle(this.orbitNormal, -a);
    this.sunDir.copy(this.sun0).applyQuaternion(Q);
    (this.planetMat.uniforms.uSunDir.value as THREE.Vector3).copy(this.sunDir);
    this.planetMat.uniforms.uRot.value = rotAround(this.orbitNormal, a);
    // clouds drift a little faster than the ground, plus a slow shear
    const cr = rotAround(this.orbitNormal, a * 1.04).multiply(rotAround(new THREE.Vector3(0, 1, 0), this.time * 0.0004));
    this.planetMat.uniforms.uCloudRot.value = cr;
    this.cloudMat.uniforms.uCloudRot.value = cr;
    this.group.position.copy(camPos);
    (this.atmoMat.uniforms.uCenter.value as THREE.Vector3).copy(camPos).add(this.center);
    this.sun.position.copy(this.sunDir).multiplyScalar(4200);
    const up = Math.abs(this.sunDir.y) > 0.98 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0);
    this.sun.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(new THREE.Vector3(), this.sun.position, up));
    for (const m of this.moons) m.mesh.position.copy(m.dir0).applyQuaternion(Q).multiplyScalar(m.dist);
    this.stars.quaternion.copy(Q);
    this.sky.quaternion.copy(Q);
    // sunlight blocked by the planet?
    const ang = Math.acos(THREE.MathUtils.clamp(this.sunDir.dot(this.planetDir), -1, 1));
    this.sunVisible = THREE.MathUtils.smoothstep(ang, ANG - 0.01, ANG + 0.025);
    this.litFraction = THREE.MathUtils.clamp(0.5 - this.sunDir.dot(this.planetDir) * 0.5, 0, 1);
  }
}
