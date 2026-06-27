// games/uno/index.js — UnoView: orchestrates the Uno render modules and registers
// itself with the game-view registry. Renders the `uno.state` snapshot as native
// HTML with deal/play animations.

import { registerView } from "../../core/registry.js";
import { ctx, els } from "./context.js";
import { flash, renderOver, startTimer, stopTimer } from "./effects.js";
import { renderHand } from "./hand.js";
import { removeMinigame, renderMinigame, renderTargetPicker } from "./minigame.js";
import { renderCenter, renderOpponents } from "./table.js";

function init(actions) {
  ctx.actions = actions;
  els.stage = document.getElementById("uno-stage");
  els.opponents = document.getElementById("uno-opponents");
  els.drawpile = document.getElementById("uno-drawpile");
  els.discard = document.getElementById("uno-discard");
  els.badge = document.getElementById("uno-colorbadge");
  els.direction = document.getElementById("uno-direction");
  els.message = document.getElementById("uno-message");
  els.picker = document.getElementById("uno-color-picker");
  els.hand = document.getElementById("uno-hand");
  els.handinfo = document.getElementById("uno-handinfo");
  els.handZone = document.querySelector(".hand-zone");
  els.discardWrap = document.querySelector(".discard-wrap");
  els.timer = document.getElementById("uno-timer");
  els.timerBar = document.getElementById("uno-timer-bar");
  els.timerLabel = document.getElementById("uno-timer-label");

  for (const btn of els.picker.querySelectorAll("button")) {
    btn.addEventListener("click", () => {
      ctx.actions.chooseColor(btn.dataset.color);
      els.picker.classList.add("hidden");
    });
  }
}

function reset() {
  ctx.prev = null;
  stopTimer();
  els.stage?.classList.add("hidden");
  els.opponents.replaceChildren();
  els.discard.replaceChildren();
  els.hand.replaceChildren();
  els.message.textContent = "";
  els.badge.textContent = "";
  els.picker.classList.add("hidden");
  els.timer.classList.add("hidden");
  if (els.handZone) els.handZone.classList.remove("your-turn");
  els.discardWrap?.querySelector(".pending-draws-badge")?.remove();
  document.querySelectorAll(".uno-over").forEach((o) => o.remove());
  document.getElementById("uno-minigame")?.remove();
  document.getElementById("uno-target-picker")?.remove();
}

function render(state) {
  if (state.phase === "toast") { flash(state.message); return; }
  if (state.phase === "over") { removeMinigame(); renderOver(state); return; }
  if (state.phase === "minigame") { renderMinigame(state); return; }

  els.stage?.classList.remove("hidden");
  removeMinigame();

  const handGrew = ctx.prev && state.hand.length > ctx.prev.hand.length;
  const newCount = handGrew ? state.hand.length - ctx.prev.hand.length : 0;
  const topChanged = !ctx.prev || ctx.prev.top !== state.top;

  renderOpponents(state);
  renderCenter(state, topChanged);
  renderHand(state, newCount);

  const isMyTurn = state.current === state.you;
  if (els.handZone) els.handZone.classList.toggle("your-turn", isMyTurn);

  els.message.textContent = state.message || (state.your_turn ? "Your turn" : "Waiting…");
  els.message.classList.toggle("active", !!state.your_turn);
  els.picker.classList.toggle("hidden", !state.need_color);
  renderTargetPicker(state);

  if (state.your_turn && state.deadline) {
    startTimer(state.deadline);
  } else {
    stopTimer();
    els.timer.classList.add("hidden");
  }

  ctx.prev = state;
}

function gameOver() {
  // game_over arrives after the final uno.state(phase:over); nothing extra needed.
}

const UnoView = { init, reset, render, gameOver };
registerView("uno.state", UnoView);
export default UnoView;
