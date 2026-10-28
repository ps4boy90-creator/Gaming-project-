// Thousands of status LEDs as one instanced billboard draw with HDR output
// so the bloom pass picks them up. Each LED animates in the vertex shader.
import * as THREE from 'three';

export const LED_COLORS = {
  green: [0.18, 1.0, 0.28],
  blue: [0.2, 0.45, 1.0],
  amber: [1.0, 0.42, 0.04],
  white: [0.9, 0.95, 1.0],
  red: [1.0, 0.08, 0.05],
};

// mode: 0 steady, 1 activity flicker, 2 blink, 3 heartbeat/breathe
export const LED_MODE = { steady: 0, flicker: 1, blink: 2, beat: 3 };

export class LedBatch {
  constructor() { this.data = []; }
  add(pos, color, mode = 0, rate = 1, intensity = 1, phase = Math.random()) {
    const c = LED_COLORS[color] ?? LED_COLORS.green;
    this.data.push(pos.x, pos.y, pos.z, c[0], c[1], c[2], mode, phase, rate, intensity);
  }
  get count() { return this.data.length / 10; }

  build() {
    const n = this.count;
    const quad = new THREE.PlaneGeometry(1, 1);
    const g = new THREE.InstancedBufferGeometry();
    g.index = quad.index;
    g.setAttribute('position', quad.getAttribute('position'));
    g.setAttribute('uv', quad.getAttribute('uv'));
    const buf = new THREE.InstancedInterleavedBuffer(new Float32Array(this.data), 10, 1);
    g.setAttribute('aPos', new THREE.InterleavedBufferAttribute(buf, 3, 0));
    g.setAttribute('aColor', new THREE.InterleavedBufferAttribute(buf, 3, 3));
    g.setAttribute('aParams', new THREE.InterleavedBufferAttribute(buf, 4, 6));
    g.instanceCount = n;
    this.uniforms = {
      uTime: { value: 0 },
      uSize: { value: 0.0085 },
      uMinPx: { value: 2.2 },
      uViewportH: { value: 1080 },
      uGain: { value: 1 },
    };
    const mat = new THREE.ShaderMaterial({
      uniforms: this.uniforms,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexShader: /* glsl */ `
        attribute vec3 aPos;
        attribute vec3 aColor;
        attribute vec4 aParams; // mode, phase, rate, intensity
        uniform float uTime, uSize, uMinPx, uViewportH, uGain;
        varying vec3 vColor;
        varying vec2 vUv;
        float hash(float n) { return fract(sin(n) * 43758.5453123); }
        void main() {
          float mode = aParams.x, phase = aParams.y, rate = aParams.z;
          float on = 1.0;
          if (mode > 0.5 && mode < 1.5) {
            // bursty disk / network activity
            float t = floor(uTime * rate + phase * 97.0);
            float busy = step(0.35, hash(floor(uTime * 0.7 + phase * 13.0) + phase));
            on = mix(0.0, 1.0, step(0.5, hash(t * 1.37 + phase * 311.0))) * busy + (1.0 - busy) * step(0.93, hash(t + 5.0));
          } else if (mode > 1.5 && mode < 2.5) {
            on = step(0.5, fract(uTime * rate + phase));
          } else if (mode > 2.5) {
            float c = fract(uTime * rate + phase);
            on = 0.15 + 0.85 * (exp(-pow((c - 0.1) * 18.0, 2.0)) + 0.7 * exp(-pow((c - 0.3) * 18.0, 2.0)));
          }
          vec4 mv = modelViewMatrix * vec4(aPos, 1.0);
          float dist = max(0.05, -mv.z);
          float pxPerM = projectionMatrix[1][1] * uViewportH * 0.5 / dist;
          float px = uSize * pxPerM;
          float grow = max(1.0, uMinPx / px);
          vColor = aColor * aParams.w * on * uGain / grow;
          vUv = uv;
          mv.xy += position.xy * uSize * grow;
          mv.z += 0.004; // nudge toward the camera so the face plane never clips it
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: /* glsl */ `
        varying vec3 vColor;
        varying vec2 vUv;
        void main() {
          float r = length(vUv - 0.5) * 2.0;
          float core = smoothstep(0.42, 0.18, r);
          float halo = exp(-r * r * 6.0) * 0.45;
          float a = (core * 3.0 + halo) * smoothstep(1.0, 0.85, r);
          gl_FragColor = vec4(vColor * a * 2.2, 1.0);
        }`,
    });
    const mesh = new THREE.Mesh(g, mat);
    mesh.frustumCulled = false;
    mesh.renderOrder = 5;
    mesh.userData.noAO = true;
    return mesh;
  }
}
