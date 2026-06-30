// games/uno/index.js — UnoView: orchestrates the Uno render modules and registers
// itself with the game-view registry. Renders the `uno.state` snapshot as native
// HTML with deal/play animations.

import { registerView } from "../../core/registry.js";
import { buildPalette } from "../../core/colors.js";
import { ctx, els } from "./context.js";
import { flash, renderOver, startTimer, stopTimer } from "./effects.js";
import { renderHand } from "./hand.js";
import { removeMinigame, renderMinigame, renderTargetPicker } from "./minigame.js";
import { renderCenter, renderOpponents } from "./table.js";
import * as Uno3DRenderer from "../uno3d/renderer.js";

let _use3D      = localStorage.getItem("termplay.uno3d") === "1";
let _lastState  = null;
let _toggleBtn  = null;

function init(actions) {
  ctx.actions = actions;
  els.stage = document.getElementById("uno-stage");
  els.opponents = document.getElementById("uno-opponents");
  els.drawpile = document.getElementById("uno-drawpile");
  els.discard = document.getElementById("uno-discard");
  els.badge = document.getElementById("uno-colorbadge");
  els.direction = document.getElementById("uno-direction");
  els.message = document.getElementById("uno-message");
  els.colorModal = document.getElementById("uno-color-modal");
  els.hand = document.getElementById("uno-hand");
  els.handinfo = document.getElementById("uno-handinfo");
  els.handZone = document.querySelector(".hand-zone");
  els.discardWrap = document.querySelector(".discard-wrap");
  els.timer = document.getElementById("uno-timer");
  els.timerBar = document.getElementById("uno-timer-bar");
  els.timerLabel = document.getElementById("uno-timer-label");

  for (const btn of els.colorModal.querySelectorAll(".color-btn")) {
    btn.addEventListener("click", () => {
      ctx.actions.chooseColor(btn.dataset.color);
      els.colorModal.classList.remove("open");
      setTimeout(() => els.colorModal.classList.add("hidden"), 200);
    });
  }

  _toggleBtn = document.getElementById("uno-3d-toggle");
  _toggleBtn?.classList.remove("hidden");
  _toggleBtn.textContent = _use3D ? "2D" : "3D";
  _toggleBtn?.addEventListener("click", _doToggle3D);
  if (_use3D) _start3D(actions);
}

function _start3D(actions) {
  const canvas = document.getElementById("uno-3d-canvas");
  canvas?.classList.remove("hidden");
  document.getElementById("uno-3d-hud")?.classList.remove("hidden");
  Uno3DRenderer.init(canvas, actions);
}

function _doToggle3D() {
  _use3D = !_use3D;
  localStorage.setItem("termplay.uno3d", _use3D ? "1" : "0");
  _toggleBtn.textContent = _use3D ? "2D" : "3D";
  const canvas = document.getElementById("uno-3d-canvas");
  const hud    = document.getElementById("uno-3d-hud");
  if (_use3D) {
    canvas?.classList.remove("hidden");
    hud?.classList.remove("hidden");
    Uno3DRenderer.init(canvas, ctx.actions);
  } else {
    Uno3DRenderer.reset();
    canvas?.classList.add("hidden");
    hud?.classList.add("hidden");
  }
  if (_lastState) render(_lastState);
}

function _renderHUD3D(state) {
  const hud = document.getElementById("uno-3d-hud");
  if (!hud) return;
  hud.replaceChildren();

  const inMulti          = state.your_turn && state.multi_played?.length > 0;
  const inDraw           = state.draws_remaining > 0;
  const inStack          = state.your_turn && (state.pending_draws ?? 0) > 0 && !inMulti && !inDraw;
  const inDrewUnplayable = state.your_turn && state.drew_unplayable === true;

  const info = document.createElement("div");
  info.className = "hud-info";
  const hand = state.hand?.length ?? 0;
  const pd   = state.pending_draws ?? 0;
  info.textContent = `${hand} cartas · ` + (
    inDrewUnplayable ? "sem carta jogável — próxima ou passe"
    : inStack   ? `+${pd} acumulados — empilhe ou aceite`
    : inMulti   ? `${state.multi_played.length}× jogadas — continue ou pare`
    : state.may_play_drawn ? "jogue a carta comprada ou passe"
    : state.your_turn ? "sua vez" : "aguardando…"
  );
  hud.appendChild(info);

  if (!state.your_turn) return;

  const btn = (label, cls, onClick) => {
    const b = document.createElement("button");
    b.className = `btn ${cls}`; b.textContent = label;
    b.addEventListener("click", onClick);
    hud.appendChild(b);
  };

  if (inDraw) {
    btn(`Comprar (${state.draws_remaining} restantes)`, "primary small", () => ctx.actions.draw());
  } else if (inDrewUnplayable) {
    btn("Próxima carta", "primary small", () => ctx.actions.draw());
    btn("Passar", "ghost small", () => ctx.actions.pass());
  } else if (inMulti) {
    btn(`Terminar turno (${state.multi_played.length}×)`, "secondary small", () => ctx.actions.pass());
  } else if (state.may_play_drawn) {
    btn("Passar", "ghost small", () => ctx.actions.pass());
  } else if (!state.need_color) {
    btn(pd > 0 ? `Aceitar (+${pd} cartas)` : "Comprar",
        pd > 0 ? "primary small stack-accept" : "primary small",
        () => ctx.actions.draw());
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
  els.colorModal?.classList.add("hidden");
  els.colorModal?.classList.remove("open");
  els.timer.classList.add("hidden");
  if (els.handZone) els.handZone.classList.remove("your-turn");
  els.discardWrap?.querySelector(".pending-draws-badge")?.remove();
  document.querySelectorAll(".uno-over").forEach((o) => o.remove());
  document.getElementById("uno-minigame")?.remove();
  document.getElementById("uno-target-picker")?.remove();
  // 3D cleanup
  Uno3DRenderer.reset();
  document.getElementById("uno-3d-canvas")?.classList.add("hidden");
  document.getElementById("uno-3d-hud")?.classList.add("hidden");
  _toggleBtn?.classList.add("hidden");
  _lastState = null;
}

function render(state) {
  if (state.phase === "toast") { flash(state.message); return; }
  if (state.phase === "over") { removeMinigame(); renderOver(state); return; }
  if (state.phase === "minigame") { renderMinigame(state); return; }
  buildPalette(state.players.length);
  _lastState = state;

  if (_use3D) {
    els.stage?.classList.add("hidden");
    removeMinigame();

    Uno3DRenderer.render(state);
    _renderHUD3D(state);

    if (els.handZone) els.handZone.classList.toggle("your-turn", state.current === state.you);
    if (state.need_color) {
      els.colorModal.classList.remove("hidden");
      requestAnimationFrame(() => els.colorModal.classList.add("open"));
    } else {
      els.colorModal.classList.remove("open");
      els.colorModal.classList.add("hidden");
    }
    if (state.deadline) startTimer(state.deadline);
    else { stopTimer(); els.timer.classList.add("hidden"); }
    ctx.prev = state;
    return;
  }

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

  els.message.textContent = state.message || (state.your_turn ? "Sua vez" : "Aguardando…");
  els.message.classList.toggle("active", !!state.your_turn);
  if (state.need_color) {
    els.colorModal.classList.remove("hidden");
    requestAnimationFrame(() => els.colorModal.classList.add("open"));
  } else {
    els.colorModal.classList.remove("open");
    els.colorModal.classList.add("hidden");
  }
  renderTargetPicker(state);

  if (state.deadline) {
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
