export type FlagValue = boolean | number | string;

export interface SaveData {
  version: 1;
  savedAt: number;
  shipMinutes: number;
  player: { x: number; y: number; z: number; yaw: number; pitch: number };
  flags: Record<string, FlagValue>;
}

export interface Settings {
  quality: 'low' | 'medium' | 'high';
  sensitivity: number;
  fov: number;
  headBob: boolean;
  volume: number;
}

const SAVE_KEY = 'seedfall.save.v1';
const SETTINGS_KEY = 'seedfall.settings.v1';

export const defaultSettings: Settings = {
  quality: 'medium',
  sensitivity: 1,
  fov: 75,
  headBob: true,
  volume: 0.8,
};

function read(key: string): unknown {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown): boolean {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function loadSave(): SaveData | null {
  const d = read(SAVE_KEY) as SaveData | null;
  return d && d.version === 1 ? d : null;
}

export function writeSave(data: SaveData): boolean {
  return write(SAVE_KEY, data);
}

export function clearSave(): void {
  try {
    localStorage.removeItem(SAVE_KEY);
  } catch {
    /* storage unavailable */
  }
}

export function loadSettings(): Settings {
  const stored = read(SETTINGS_KEY);
  return { ...defaultSettings, ...(stored && typeof stored === 'object' ? stored : {}) };
}

export function saveSettings(s: Settings): void {
  write(SETTINGS_KEY, s);
}
