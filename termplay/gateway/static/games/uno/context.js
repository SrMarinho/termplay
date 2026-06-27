// games/uno/context.js — shared state for the Uno view modules: cached DOM
// element refs, the action callbacks, and the previous snapshot used for diffing.

export const els = {};
export const ctx = { actions: {}, prev: null };

export const COLOR_BG = { R: "#e63946", G: "#2a9d8f", B: "#457b9d", Y: "#e9c46a", W: "#888" };
export const COLOR_ORDER = { R: 0, G: 1, B: 2, Y: 3, W: 4 };

export function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]
  );
}
