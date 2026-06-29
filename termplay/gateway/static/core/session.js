// core/session.js — browser session persistence (survives page reload).

const SESSION_KEY = "termplay.session";

export function save(code, nick) {
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify({ code, nick })); } catch { /* quota or private mode */ }
}

export function clear() {
  try { sessionStorage.removeItem(SESSION_KEY); } catch { /* ignore */ }
}

export function load() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null"); } catch { return null; }
}
