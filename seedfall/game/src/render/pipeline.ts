import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { GTAOPass } from 'three/examples/jsm/postprocessing/GTAOPass.js';

/** Film finish: grain, vignette, slight chromatic fringing, a gentle teal/amber grade. */
const FinishShader = {
  uniforms: {
    tDiffuse: { value: null as THREE.Texture | null },
    uTime: { value: 0 },
    uGrain: { value: 0.045 },
    uVignette: { value: 0.32 },
    uAberration: { value: 0.0015 },
  },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform float uTime, uGrain, uVignette, uAberration;
    varying vec2 vUv;
    float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233)) + uTime * 3.7) * 43758.5453); }
    void main(){
      vec2 c = vUv - 0.5;
      float r2 = dot(c, c);
      vec2 off = c * r2 * uAberration * 8.0;
      vec3 col;
      col.r = texture2D(tDiffuse, vUv + off).r;
      col.g = texture2D(tDiffuse, vUv).g;
      col.b = texture2D(tDiffuse, vUv - off).b;
      float l = dot(col, vec3(0.299, 0.587, 0.114));
      col = mix(col, col * vec3(0.94, 1.0, 1.04), smoothstep(0.5, 0.0, l) * 0.6);
      col = mix(col, col * vec3(1.04, 1.0, 0.95), smoothstep(0.4, 1.0, l) * 0.5);
      col *= 1.0 - uVignette * smoothstep(0.1, 0.75, r2 * 2.0);
      col += (hash(vUv * 1000.0) - 0.5) * uGrain;
      gl_FragColor = vec4(col, 1.0);
    }`,
};

export type Quality = 'low' | 'medium' | 'high';

export class Pipeline {
  composer!: EffectComposer;
  finish!: ShaderPass;
  private gtao: GTAOPass | null = null;
  private bloom!: UnrealBloomPass;

  constructor(
    private renderer: THREE.WebGLRenderer,
    private interior: THREE.Scene,
    private over: THREE.Scene,
    private camera: THREE.PerspectiveCamera,
  ) {}

  build(quality: Quality): void {
    this.composer?.dispose();
    const w = window.innerWidth;
    const h = window.innerHeight;
    const pr = this.renderer.getPixelRatio();
    const rt = new THREE.WebGLRenderTarget(w * pr, h * pr, {
      type: THREE.HalfFloatType,
      samples: quality === 'low' ? 0 : 4,
    });
    this.composer = new EffectComposer(this.renderer, rt);
    this.composer.setPixelRatio(pr);
    this.composer.setSize(w, h);
    this.composer.addPass(new RenderPass(this.interior, this.camera));
    const overPass = new RenderPass(this.over, this.camera);
    overPass.clear = false;
    this.composer.addPass(overPass);
    this.gtao = null;
    if (quality === 'high') {
      const g = new GTAOPass(this.interior, this.camera, w, h);
      g.output = GTAOPass.OUTPUT.Default;
      g.blendIntensity = 0.85;
      g.updateGtaoMaterial({ radius: 0.45, distanceExponent: 1, thickness: 1, scale: 1, samples: 12 });
      this.composer.addPass(g);
      this.gtao = g;
    }
    const div = quality === 'low' ? 2 : 1;
    this.bloom = new UnrealBloomPass(new THREE.Vector2(w / div, h / div), 0.42, 0.55, 0.92);
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());
    this.finish = new ShaderPass(FinishShader);
    this.composer.addPass(this.finish);
  }

  resize(): void {
    const w = window.innerWidth;
    const h = window.innerHeight;
    this.composer.setPixelRatio(this.renderer.getPixelRatio());
    this.composer.setSize(w, h);
    this.gtao?.setSize(w, h);
  }

  render(t: number): void {
    this.finish.uniforms.uTime.value = t % 100;
    this.composer.render();
  }
}
