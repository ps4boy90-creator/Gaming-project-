// Shader patches on top of MeshStandardMaterial.
import * as THREE from 'three';
import { pbr } from './painter.js';

const UV_PATCH =
  'vec4 aRR = aFace < 0.5 ? aRect0 : ( aFace < 1.5 ? aRect1 : aRect2 );\n' +
  'vec2 aUV = aRR.xy + uv * aRR.zw;\n' +
  THREE.ShaderChunk.uv_vertex
    .replace(/\b[A-Z_]*MAP_UV\b/g, 'aUV')
    .replace(/vec3\( uv, 1 \)/g, 'vec3( aUV, 1 )');

// Instanced atlas material: each instance carries up to three UV rects
// (front face, rear face, everything else) selected by the aFace attribute.
export function atlasMaterial(tex, extra = {}) {
  const mat = tex.isTexture
    ? new THREE.MeshStandardMaterial({ map: tex, ...extra })
    : pbr(tex, extra);
  mat.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace(
        '#include <common>',
        '#include <common>\nattribute vec4 aRect0;\nattribute vec4 aRect1;\nattribute vec4 aRect2;\nattribute float aFace;',
      )
      .replace('#include <uv_vertex>', UV_PATCH);
  };
  mat.customProgramCacheKey = () => 'atlas';
  return mat;
}

// Unit cube whose +z face is aFace 0, -z face aFace 1, the rest aFace 2.
export function faceBoxGeometry() {
  const g = new THREE.BoxGeometry(1, 1, 1);
  const face = new Float32Array(24);
  for (let i = 0; i < 24; i++) {
    const f = Math.floor(i / 4); // px nx py ny pz nz
    face[i] = f === 4 ? 0 : f === 5 ? 1 : 2;
  }
  g.setAttribute('aFace', new THREE.BufferAttribute(face, 1));
  return g;
}

export function setRects(geometry, count) {
  const mk = () => new THREE.InstancedBufferAttribute(new Float32Array(count * 4), 4);
  const a = [mk(), mk(), mk()];
  geometry.setAttribute('aRect0', a[0]);
  geometry.setAttribute('aRect1', a[1]);
  geometry.setAttribute('aRect2', a[2]);
  if (!geometry.getAttribute('aFace')) {
    geometry.setAttribute('aFace', new THREE.BufferAttribute(new Float32Array(geometry.getAttribute('position').count), 1));
  }
  return a;
}

// Floor: direct light is scaled by a baked visibility mask (G) and indirect
// light by baked ambient occlusion (R), both sampled from world XZ.
export function maskedFloorMaterial(mat, maskTex, bounds) {
  const uniforms = {
    uMask: { value: maskTex },
    uMaskBounds: { value: new THREE.Vector4(bounds.minX, bounds.minZ, bounds.maxX - bounds.minX, bounds.maxZ - bounds.minZ) },
  };
  mat.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nuniform vec4 uMaskBounds;\nvarying vec2 vMaskUv;')
      .replace(
        '#include <project_vertex>',
        '#include <project_vertex>\nvec4 mwp = modelMatrix * vec4( transformed, 1.0 );\nvMaskUv = vec2( ( mwp.x - uMaskBounds.x ) / uMaskBounds.z, 1.0 - ( mwp.z - uMaskBounds.y ) / uMaskBounds.w );',
      );
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform sampler2D uMask;\nvarying vec2 vMaskUv;')
      .replace(
        '#include <aomap_fragment>',
        '#include <aomap_fragment>\n' +
          'vec4 lmk = texture2D( uMask, vMaskUv );\n' +
          'reflectedLight.directDiffuse *= lmk.g;\n' +
          'reflectedLight.directSpecular *= lmk.g;\n' +
          'reflectedLight.indirectDiffuse *= lmk.r;\n' +
          'reflectedLight.indirectSpecular *= mix( 1.0, lmk.r, 0.8 );',
      );
  };
  mat.customProgramCacheKey = () => 'floor-mask';
  return mat;
}
