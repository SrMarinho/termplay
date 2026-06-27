// games/uno/minigame.js — Brazilian-rule prompts: the card-0 swap-target picker
// and the card-1 tap-the-dot minigame overlay.

import { ctx } from "./context.js";

// ── card 0: pick a player to swap hands with ───────────────────────────────────

export function renderTargetPicker(state) {
  let picker = document.getElementById("uno-target-picker");
  if (!state.need_target) {
    picker?.remove();
    return;
  }
  if (!picker) {
    picker = document.createElement("div");
    picker.id = "uno-target-picker";
    picker.className = "target-picker";
    document.getElementById("screen-game").appendChild(picker);
  }
  picker.replaceChildren();
  const title = document.createElement("div");
  title.className = "target-title";
  title.textContent = "🔄 Trocar de mão com:";
  picker.appendChild(title);
  for (const gi of state.targets || []) {
    const [name, count] = state.players[gi] || [`P${gi + 1}`, 0];
    const btn = document.createElement("button");
    btn.className = "btn secondary target-btn";
    btn.textContent = `${name} (${count})`;
    btn.addEventListener("click", () => { ctx.actions.chooseTarget(gi); picker.remove(); });
    picker.appendChild(btn);
  }
}

// ── card 1: tap-the-dot minigame ────────────────────────────────────────────────

export function renderMinigame(state) {
  let overlay = document.getElementById("uno-minigame");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "uno-minigame";
    overlay.className = "minigame-overlay";
    overlay.innerHTML =
      `<div class="mini-head">⚡ Clique no ponto!</div>` +
      `<div class="mini-status"></div>` +
      `<div class="mini-field"><button class="mini-dot" type="button"></button></div>`;
    document.getElementById("screen-game").appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add("open"));
  }
  const dot = overlay.querySelector(".mini-dot");
  const status = overlay.querySelector(".mini-status");
  const youSafe = !!state.you_safe;
  const left = Math.round((state.dot?.x ?? 0.5) * 100);
  const top = Math.round((state.dot?.y ?? 0.5) * 100);
  dot.style.left = `${left}%`;
  dot.style.top = `${top}%`;
  dot.classList.toggle("safe", youSafe);
  dot.onclick = youSafe ? null : () => ctx.actions.tap();

  const total = (state.participants || []).length;
  const safeCount = (state.safe || []).length;
  const remaining = total - safeCount;
  status.textContent = youSafe
    ? `✓ você clicou — faltam ${remaining} jogador(es)`
    : `clique rápido! ${safeCount}/${total} já clicaram`;
  overlay.classList.toggle("you-safe", youSafe);
}

export function removeMinigame() {
  document.getElementById("uno-minigame")?.remove();
}
