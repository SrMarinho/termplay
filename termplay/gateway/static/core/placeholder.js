// core/placeholder.js — generic "web UI coming soon" view for games that are
// playable on the server but don't yet have a browser renderer. Lets the
// per-game folders stay uniform (each game registers a view) without dead UI.

import { registerView } from "./registry.js";

export function registerPlaceholder(tag, label) {
  let overlay = null;

  function remove() {
    overlay?.remove();
    overlay = null;
  }

  registerView(tag, {
    init() {},
    reset() { remove(); },
    gameOver() {},
    render() {
      if (overlay) return;
      overlay = document.createElement("div");
      overlay.className = "placeholder-view";
      overlay.innerHTML =
        `<div class="ph-card">` +
        `<div class="ph-title">${label}</div>` +
        `<div class="ph-sub">Interface web em breve — jogue pelo terminal.</div>` +
        `</div>`;
      document.getElementById("screen-game").appendChild(overlay);
    },
  });
}
