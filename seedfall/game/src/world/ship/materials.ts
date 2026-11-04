import * as THREE from 'three';
import * as T from './textures';
import { Atlas } from './atlas';

export type Pass = 'interior' | 'over';

export interface MatDef {
  mat: THREE.Material;
  /** World-space tile size in metres for box-projected UVs; 0 = keep geometry UVs. */
  tileU: number;
  tileV: number;
  cast: boolean;
  receive: boolean;
  pass: Pass;
}

export const DECK_COLORS: Record<string, string> = {
  command: '#4a78b5',
  crew: '#e0912b',
  science: '#4c9a68',
  spine: '#e0662a',
  aft: '#b8352a',
};

/** The ship's material library. Everything is MeshStandardMaterial with procedural maps. */
export class Materials {
  defs = new Map<string, MatDef>();
  signs = new Atlas(2048);
  screens = new Atlas(2048);
  lightEmissive: THREE.MeshStandardMaterial[] = [];
  glowTex = T.radialGlow();
  mistTex = T.mist();

  constructor(onProgress: (label: string) => void = () => {}) {
    onProgress('wall cladding');
    const wall = T.wallPanels(1);
    onProgress('deck plating');
    const floor = T.floorTiles(2);
    const ceil = T.ceilingPanels(3);
    onProgress('metals');
    const metal = T.brushedMetal(4, 0.085);
    const steel = T.brushedMetal(14, 0.5);
    const paintSet = T.paint(5, [0.8, 0.81, 0.79]);
    const hull = T.paint(15, [0.74, 0.75, 0.73], true);
    onProgress('fabrics');
    const fab = T.fabric(6, [0.16, 0.19, 0.23]);
    const fabLight = T.fabric(16, [0.6, 0.61, 0.6]);
    const fabAmber = T.fabric(26, [0.5, 0.3, 0.12]);
    onProgress('collector film');
    const sail = T.sailFoil(7);
    const frost = T.frost(8);
    const hazard = T.hazard(9);
    const door = T.doorLeaf(10);

    const std = (p: THREE.MeshStandardMaterialParameters) => new THREE.MeshStandardMaterial(p);
    const fromSet = (s: T.PBRSet, extra: THREE.MeshStandardMaterialParameters = {}) =>
      std({ map: s.map, normalMap: s.normalMap, roughnessMap: s.roughnessMap, roughness: 1, ...extra });

    const add = (key: string, mat: THREE.Material, tileU = 1, tileV = tileU, opts: Partial<MatDef> = {}) => {
      mat.name = key;
      this.defs.set(key, { mat, tileU, tileV, cast: true, receive: true, pass: 'interior', ...opts });
    };

    add('wall', fromSet(wall, { envMapIntensity: 0.6 }), 2, 4);
    add('wallDark', fromSet(wall, { color: new THREE.Color(0.42, 0.44, 0.46), envMapIntensity: 0.5 }), 2, 4);
    add('floor', fromSet(floor, { envMapIntensity: 0.5 }), 2, 2);
    add('ceil', fromSet(ceil, { envMapIntensity: 0.3 }), 2, 2);
    add('metal', fromSet(metal, { metalness: 0.75, envMapIntensity: 0.9 }), 1, 1);
    add('steel', fromSet(steel, { metalness: 0.9, envMapIntensity: 1.0 }), 1, 1);
    add('paint', fromSet(paintSet, { envMapIntensity: 0.6 }), 1, 1);
    add('paintGrey', fromSet(paintSet, { color: new THREE.Color(0.42, 0.44, 0.46) }), 1, 1);
    add('paintDark', fromSet(paintSet, { color: new THREE.Color(0.16, 0.17, 0.18) }), 1, 1);
    add('hullExt', fromSet(hull, { envMapIntensity: 0.7, fog: false }), 4, 4);
    add('hullDark', fromSet(hull, { color: new THREE.Color(0.3, 0.31, 0.32), fog: false }), 4, 4);
    add('fabric', fromSet(fab), 0.5, 0.5);
    add('fabricLight', fromSet(fabLight), 0.5, 0.5);
    add('fabricAmber', fromSet(fabAmber), 0.5, 0.5);
    add('rubber', std({ color: 0x151719, roughness: 0.85 }), 1, 1);
    add('hazard', fromSet(hazard), 1, 1);

    const accent = (hex: string) => fromSet(paintSet, { color: new THREE.Color(hex).multiplyScalar(1.25) });
    for (const [k, hex] of Object.entries(DECK_COLORS)) add(`accent-${k}`, accent(hex), 1, 1);

    const emissive = (hex: number, intensity: number) => {
      const m = std({ color: 0x050505, emissive: hex, emissiveIntensity: intensity, roughness: 0.4 });
      return m;
    };
    const light = emissive(0xfff4e8, 4.5);
    const lightCold = emissive(0xbfe6ff, 3.5);
    const lightWarm = emissive(0xffc98a, 3.5);
    this.lightEmissive.push(light, lightWarm);
    add('light', light, 0, 0, { cast: false });
    add('lightCold', lightCold, 0, 0, { cast: false });
    add('lightWarm', lightWarm, 0, 0, { cast: false });
    add('growLight', emissive(0xff5ad2, 5), 0, 0, { cast: false });
    add('podGlow', emissive(0x6fe0ff, 2.2), 0, 0, { cast: false });
    add('podFail', emissive(0xff2a1a, 2.5), 0, 0, { cast: false });
    add('statusGreen', emissive(0x3dff7a, 3), 0, 0, { cast: false });
    add('statusRed', emissive(0xff2a1a, 3), 0, 0, { cast: false });
    add('statusAmber', emissive(0xffa020, 3), 0, 0, { cast: false });
    add('engineGlow', emissive(0x9fd8ff, 6), 0, 0, { cast: false });

    add(
      'screen',
      std({ color: 0x000000, emissive: 0xffffff, emissiveMap: this.screens.texture, emissiveIntensity: 1.25, roughness: 0.12, metalness: 0 }),
      0, 0, { cast: false },
    );
    add(
      'sign',
      std({
        map: this.signs.texture,
        emissive: 0xffffff,
        emissiveMap: this.signs.texture,
        emissiveIntensity: 0.25,
        roughness: 0.6,
        transparent: true,
        depthWrite: false,
        polygonOffset: true,
        polygonOffsetFactor: -2,
        polygonOffsetUnits: -2,
      }),
      0, 0, { cast: false, receive: true },
    );

    const glassParams: THREE.MeshStandardMaterialParameters = {
      color: new THREE.Color(0.55, 0.65, 0.7),
      transparent: true,
      opacity: 0.06,
      roughness: 0.03,
      metalness: 0.0,
      envMapIntensity: 1.0,
      depthWrite: false,
    };
    add('glass', std(glassParams), 0, 0, { cast: false, receive: false, pass: 'over' });
    add('glassInner', std({ ...glassParams, opacity: 0.14, envMapIntensity: 0.35 }), 0, 0, { cast: false, receive: false });
    add('blackGlass', std({ color: 0x020304, roughness: 0.06, metalness: 0.4, envMapIntensity: 1.4 }), 0, 0);
    add('chrome', std({ color: 0xc8ccd0, roughness: 0.18, metalness: 1, envMapIntensity: 1.2 }), 0, 0);
    add(
      'frost',
      std({
        map: frost.map,
        normalMap: frost.normalMap,
        roughnessMap: frost.roughnessMap,
        alphaMap: frost.alphaMap,
        transparent: true,
        depthWrite: false,
        roughness: 1,
        envMapIntensity: 1.2,
        emissive: 0x2a6070,
        emissiveIntensity: 0.25,
      }),
      1, 1, { cast: false },
    );
    add('sleeper', std({ color: 0x0b0d0f, roughness: 0.9 }), 0, 0);
    add('plant', std({ color: 0x2c4a1c, roughness: 0.75, side: THREE.DoubleSide }), 0, 0);
    add('plantDark', std({ color: 0x18301a, roughness: 0.8, side: THREE.DoubleSide }), 0, 0);
    add('soil', std({ color: 0x1a120c, roughness: 1 }), 0, 0);
    add(
      'sail',
      std({
        map: sail.map,
        normalMap: sail.normalMap,
        roughnessMap: sail.roughnessMap,
        roughness: 1,
        metalness: 0.85,
        color: new THREE.Color(1, 0.8, 0.5),
        emissive: new THREE.Color(0.42, 0.27, 0.08),
        emissiveIntensity: 0.35,
        side: THREE.DoubleSide,
        envMapIntensity: 0.5,
        fog: false,
      }),
      120, 120, { cast: false, receive: false },
    );
    add('door', fromSet(door, { envMapIntensity: 0.7 }), 0, 0);
  }

  get(key: string): MatDef {
    const d = this.defs.get(key);
    if (!d) throw new Error(`Unknown material ${key}`);
    return d;
  }

  /** Day/night shift: ceiling panels dim and warm at night. */
  setShift(night: number): void {
    for (const m of this.lightEmissive) {
      m.emissiveIntensity = (m.name === 'lightWarm' ? 3.5 : 4.5) * (1 - night * 0.72);
    }
    const light = this.lightEmissive[0];
    light.emissive.setRGB(1, 0.957 - night * 0.2, 0.91 - night * 0.42);
  }
}
