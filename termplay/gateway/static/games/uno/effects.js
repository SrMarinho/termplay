// games/uno/effects.js — turn timer, toast flash, and the game-over overlay.

import { ctx, els, esc } from "./context.js";

// ── turn timer ────────────────────────────────────────────────────────────────

let timerRaf = null;
let _timerDeadline = 0;
let _timerTotal = 0;

export function startTimer(deadlineUnix) {
  const now = Date.now() / 1000;
  _timerDeadline = deadlineUnix;
  _timerTotal = deadlineUnix - now;
  els.timer.classList.remove("hidden");
  stopTimer();
  function tick() {
    const remaining = _timerDeadline - Date.now() / 1000;
    const frac = Math.max(0, Math.min(1, remaining / _timerTotal));
    const secs = Math.ceil(Math.max(0, remaining));
    const urgent = remaining < 8;
    els.timerBar.style.transform = `scaleX(${frac})`;
    els.timerBar.classList.toggle("urgent", urgent);
    els.timerLabel.textContent = secs;
    els.timerLabel.classList.toggle("urgent", urgent);
    if (remaining > 0) timerRaf = requestAnimationFrame(tick);
  }
  timerRaf = requestAnimationFrame(tick);
}

export function stopTimer() {
  if (timerRaf !== null) { cancelAnimationFrame(timerRaf); timerRaf = null; }
}

// ── toast / game over ─────────────────────────────────────────────────────────

let flashTimer = null;

export function flash(text) {
  if (!text) return;
  els.message.textContent = text;
  els.message.classList.add("flash");
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => {
    els.message.classList.remove("flash");
    if (ctx.prev) {
      els.message.textContent =
        ctx.prev.message || (ctx.prev.your_turn ? "Sua vez" : "Aguardando…");
    }
  }, 2500);
}

export function renderOver(state) {
  els.picker.classList.add("hidden");
  const overlay = document.createElement("div");
  overlay.className = "uno-over";
  overlay.innerHTML =
    `<div class="over-card">` +
    `<div class="over-title">${state.winner ? `🏆 ${esc(state.winner)} wins!` : "Game over"}</div>` +
    `<button class="over-btn" id="over-leave">Voltar ao lobby</button>` +
    `</div>`;
  document.getElementById("screen-game").appendChild(overlay);
  document.getElementById("over-leave").addEventListener("click", () => {
    overlay.remove();
    ctx.actions.backToLobby();
  });
}
