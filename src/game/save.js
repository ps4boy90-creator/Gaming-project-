const KEY = 'veridian.save.v1';

/**
 * Progress lives in localStorage. There is no fail state, so a save is only
 * ever a convenience for closing the tab -- which is why it stores position
 * rather than a checkpoint id.
 */
export const Save = {
  write(state) {
    try {
      localStorage.setItem(KEY, JSON.stringify({ version: 1, savedAt: Date.now(), ...state }));
      return true;
    } catch (err) {
      // Private browsing and blocked storage both throw here. Losing a save is
      // not worth taking the game down for.
      console.warn('Could not write save:', err);
      return false;
    }
  },

  read() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      return data && data.version === 1 ? data : null;
    } catch (err) {
      console.warn('Could not read save:', err);
      return null;
    }
  },

  clear() {
    try { localStorage.removeItem(KEY); } catch (err) { /* nothing to do */ }
  },

  exists() {
    return !!Save.read();
  },
};
