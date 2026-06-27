// games/blackjack/index.js — BlackjackView: renders the `blackjack.state` snapshot
// for player-vs-player Blackjack and registers itself with the view registry.

import { registerView } from "../../core/registry.js";
import { makeCard } from "./assets/cards.js";

const ctx = { actions: {}, root: null };
let timerRaf = null;

const STATUS_LABEL = {
  bust: "ESTOUROU", stand: "PAROU", blackjack: "BLACKJACK", out: "saiu",
};

function init(actions) {
  ctx.actions = actions;
}

function reset() {
  stopTimer();
  ctx.root?.remove();
  ctx.root = null;
}

function ensureRoot() {
  if (ctx.root) return ctx.root;
  const root = document.createElement("div");
  root.className = "bj-root";
  root.innerHTML =
    `<div class="bj-others"></div>` +
    `<div class="bj-center">` +
    `<div class="bj-target"></div>` +
    `<div class="bj-message"></div>` +
    `<div class="bj-timer hidden"><span class="bj-timer-label">30</span></div>` +
    `</div>` +
    `<div class="bj-me">` +
    `<div class="bj-me-cards"></div>` +
    `<div class="bj-me-info"></div>` +
    `<div class="bj-actions">` +
    `<button class="btn primary bj-hit">Comprar (Hit)</button>` +
    `<button class="btn secondary bj-stand">Parar (Stand)</button>` +
    `</div></div>`;
  document.getElementById("screen-game").appendChild(root);
  root.querySelector(".bj-hit").addEventListener("click", () => ctx.actions.hit());
  root.querySelector(".bj-stand").addEventListener("click", () => ctx.actions.stand());
  ctx.root = root;
  return root;
}

function render(state) {
  if (state.phase === "over") { renderOver(state); return; }
  const root = ensureRoot();
  root.querySelector(".bj-over")?.remove();

  renderOthers(root, state);

  root.querySelector(".bj-target").textContent =
    `Primeiro a ${state.target_score} pontos vence`;
  const msg = root.querySelector(".bj-message");
  msg.textContent = state.message || (state.your_turn ? "Sua vez!" : "Aguardando…");
  msg.classList.toggle("active", !!state.your_turn);

  // Your hand.
  const meCards = root.querySelector(".bj-me-cards");
  meCards.replaceChildren();
  for (const face of state.hand || []) meCards.appendChild(makeCard(face));
  const me = state.players[state.you] || ["você", [], 0, 0, ""];
  root.querySelector(".bj-me-info").textContent =
    `${me[0]} · total ${state.hand_value} · ${me[3]} pts`;

  // Actions only on your turn.
  const canAct = !!state.your_turn;
  root.querySelector(".bj-hit").disabled = !canAct;
  root.querySelector(".bj-stand").disabled = !canAct;
  root.querySelector(".bj-actions").classList.toggle("hidden", !canAct);

  if (state.your_turn && state.deadline) startTimer(root, state.deadline);
  else { stopTimer(); root.querySelector(".bj-timer").classList.add("hidden"); }
}

function renderOthers(root, state) {
  const wrap = root.querySelector(".bj-others");
  wrap.replaceChildren();
  state.players.forEach((p, i) => {
    if (i === state.you) return;
    const [name, cards, value, score, status] = p;
    const seat = document.createElement("div");
    seat.className = "bj-seat" + (i === state.current ? " active" : "");
    if (status === "bust") seat.classList.add("bust");

    const head = document.createElement("div");
    head.className = "bj-seat-head";
    head.innerHTML =
      `<span class="bj-name">${esc(name)}</span>` +
      `<span class="bj-score">${score} pts</span>`;

    const hand = document.createElement("div");
    hand.className = "bj-seat-cards";
    for (const face of cards) hand.appendChild(makeCard(face));

    const foot = document.createElement("div");
    foot.className = "bj-seat-foot";
    const label = STATUS_LABEL[status];
    foot.innerHTML =
      `<span class="bj-value">${value}</span>` +
      (label ? `<span class="bj-badge ${status}">${label}</span>` : "");

    seat.append(head, hand, foot);
    wrap.appendChild(seat);
  });
}

function renderOver(state) {
  const root = ensureRoot();
  stopTimer();
  if (root.querySelector(".bj-over")) return;
  const overlay = document.createElement("div");
  overlay.className = "bj-over";
  overlay.innerHTML =
    `<div class="over-card">` +
    `<div class="over-title">${state.winner ? `🏆 ${esc(state.winner)} venceu!` : "Fim de jogo"}</div>` +
    `<button class="over-btn" id="bj-over-leave">Voltar ao lobby</button>` +
    `</div>`;
  root.appendChild(overlay);
  document.getElementById("bj-over-leave").addEventListener("click", () => {
    overlay.remove();
    ctx.actions.backToLobby();
  });
}

function gameOver() {
  // game_over arrives after the final blackjack.state(phase:over); nothing to do.
}

// ── timer ──────────────────────────────────────────────────────────────────────

function startTimer(root, deadlineUnix) {
  const timer = root.querySelector(".bj-timer");
  const label = root.querySelector(".bj-timer-label");
  timer.classList.remove("hidden");
  stopTimer();
  function tick() {
    const remaining = Math.max(0, deadlineUnix - Date.now() / 1000);
    label.textContent = Math.ceil(remaining);
    label.classList.toggle("urgent", remaining < 8);
    if (remaining > 0) timerRaf = requestAnimationFrame(tick);
  }
  timerRaf = requestAnimationFrame(tick);
}

function stopTimer() {
  if (timerRaf !== null) { cancelAnimationFrame(timerRaf); timerRaf = null; }
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]
  );
}

const BlackjackView = { init, reset, render, gameOver };
registerView("blackjack.state", BlackjackView);
export default BlackjackView;
