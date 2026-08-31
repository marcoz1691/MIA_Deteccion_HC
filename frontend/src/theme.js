export const THEME_STORAGE_KEY = "mia-theme";
export const EGG_UNLOCK_STORAGE_KEY = "mia-theme-unlocked";

export function getStoredTheme() {
  const v = globalThis.localStorage?.getItem(THEME_STORAGE_KEY);
  return v === "dark" ? "dark" : "light";
}

export function applyTheme(theme) {
  const next = theme === "dark" ? "dark" : "light";
  globalThis.localStorage?.setItem(THEME_STORAGE_KEY, next);
  globalThis.document?.documentElement?.setAttribute("data-theme", next);
}

export function toggleTheme() {
  const next = getStoredTheme() === "dark" ? "light" : "dark";
  applyTheme(next);
  return next;
}

export function isThemeUnlocked() {
  return globalThis.localStorage?.getItem(EGG_UNLOCK_STORAGE_KEY) === "1";
}

export function markThemeUnlocked() {
  globalThis.localStorage?.setItem(EGG_UNLOCK_STORAGE_KEY, "1");
}

export function createEggTracker({ clicksNeeded = 5, windowMs = 2000 } = {}) {
  let count = 0;
  let windowStart = 0;
  return {
    registerClick(now = Date.now()) {
      if (!windowStart || now - windowStart > windowMs) {
        windowStart = now;
        count = 1;
        return false;
      }
      count += 1;
      if (count >= clicksNeeded) {
        count = 0;
        windowStart = 0;
        return true;
      }
      return false;
    },
  };
}
