// games/truco/index.js — TrucoView

import { registerView } from "../../core/registry.js";
import { buildPalette, playerColor } from "../../core/colors.js";

const SUIT_LABEL = { C: "♣", H: "♥", S: "♠", D: "♦" };
const SUIT_COLOR  = { C: "#2a2", H: "#d44", S: "#555", D: "#d44" };
const RANK_DISPLAY = { Q: "Q", J: "J", K: "K", A: "A" };

let _ctx = { actions: {}, root: null };
let _timerRaf = null;
let _palette = [];

function init(actions) {
  _ctx.actions = actions;
}

function reset() {
  if (_timerRaf) { cancelAnimationFrame(_timerRaf); _timerRaf = null; }
  _ctx.root?.remove();
  _ctx.root = null;
  _palette = [];
}

function render(state) {
  if (!_ctx.root) _build(state);
  const root = _ctx.root;
  _palette = buildPalette(state.players.length);

  _renderScore(root, state);
  _renderVira(root, state);
  _renderTable(root, state);
  _renderTricks(root, state);
  _renderHand(root, state);
  _renderActions(root, state);
  _renderMessage(root, state);
  _renderEnvite(root, state);

  if (state.deadline && state.your_turn) {
    _startTimer(root, state.deadline);
  } else {
    _stopTimer(root);
  }
}

function gameOver() {}

// ── build DOM ──────────────────────────────────────────────────────────────

function _build(state) {
  const root = document.createElement("div");
  root.className = "tc-root";
  root.innerHTML = `
    <header class="tc-header">
      <div class="tc-score" id="tc-score"></div>
      <div class="tc-vira-wrap">
        <span class="tc-vira-label">Vira</span>
        <div class="tc-vira-card" id="tc-vira"></div>
      </div>
      <div class="tc-timer hidden" id="tc-timer"><span>20</span></div>
    </header>
    <main class="tc-table" id="tc-table"></main>
    <div class="tc-tricks-row" id="tc-tricks"></div>
    <footer class="tc-footer">
      <div class="tc-hand" id="tc-hand"></div>
      <div class="tc-actions" id="tc-actions"></div>
    </footer>
    <div class="tc-message" id="tc-message"></div>
    <div class="tc-envite-overlay hidden" id="tc-envite">
      <div class="tc-envite-box">
        <p class="tc-envite-title" id="tc-envite-title">Truco!</p>
        <div class="tc-envite-btns">
          <button class="btn primary" id="tc-accept">Aceitar</button>
          <button class="btn secondary" id="tc-raise">Aumentar</button>
          <button class="btn ghost" id="tc-run">Correr</button>
        </div>
      </div>
    </div>
  `;
  document.getElementById("screen-game").appendChild(root);

  root.querySelector("#tc-accept").addEventListener("click", () => _ctx.actions.send("a"));
  root.querySelector("#tc-raise").addEventListener("click", () => _ctx.actions.send("r"));
  root.querySelector("#tc-run").addEventListener("click", () => _ctx.actions.send("c"));

  _ctx.root = root;
}

// ── render sections ────────────────────────────────────────────────────────

function _renderScore(root, state) {
  const el = root.querySelector("#tc-score");
  const teamNames = state.teams.map(
    (members) => members.map((i) => state.players[i]).join(" & ")
  );
  el.innerHTML =
    `<span class="tc-team tc-team-a">${teamNames[0]}</span>` +
    `<span class="tc-pts tc-pts-a">${state.score[0]}</span>` +
    `<span class="tc-sep">–</span>` +
    `<span class="tc-pts tc-pts-b">${state.score[1]}</span>` +
    `<span class="tc-team tc-team-b">${teamNames[1]}</span>`;
}

function _renderVira(root, state) {
  const el = root.querySelector("#tc-vira");
  el.replaceChildren();
  el.appendChild(_makeCardEl(state.vira));
}

function _renderTable(root, state) {
  const el = root.querySelector("#tc-table");
  el.replaceChildren();
  const n = state.players.length;
  // slot positions: bottom=you, top=across, left/right=sides
  const positions = _tablePositions(state.you, n);

  for (let i = 0; i < n; i++) {
    const pos = positions[i];
    const slot = document.createElement("div");
    slot.className = `tc-slot tc-slot-${pos}`;
    slot.style.setProperty("--player-color", playerColor(_palette, i));

    const label = document.createElement("span");
    label.className = "tc-slot-name";
    label.textContent = state.players[i];
    if (i === state.current && state.phase === "play") label.classList.add("tc-active");

    const cardWrap = document.createElement("div");
    cardWrap.className = "tc-slot-card";
    if (state.table[i] !== null) {
      cardWrap.appendChild(_makeCardEl(state.table[i]));
    } else {
      cardWrap.innerHTML = `<div class="bj-card bj-card-placeholder"></div>`;
    }

    slot.appendChild(label);
    slot.appendChild(cardWrap);
    el.appendChild(slot);
  }
}

function _renderTricks(root, state) {
  const el = root.querySelector("#tc-tricks");
  el.replaceChildren();
  for (let t = 0; t < 3; t++) {
    const pip = document.createElement("div");
    pip.className = "tc-trick-pip";
    const result = state.tricks[t] ?? null;
    const myTeam = state.teams.findIndex((m) => m.includes(state.you));
    if (result === null) {
      pip.classList.add(t < state.tricks.length ? "tc-pip-tie" : "tc-pip-pending");
    } else {
      pip.classList.add(result === myTeam ? "tc-pip-win" : "tc-pip-loss");
    }
    el.appendChild(pip);
  }
}

function _renderHand(root, state) {
  const el = root.querySelector("#tc-hand");
  el.replaceChildren();
  const hand = state.your_hand ?? [];
  hand.forEach((face, idx) => {
    const card = _makeCardEl(face);
    card.classList.add("tc-hand-card");
    if (state.your_turn && state.phase === "play") {
      card.classList.add("clickable");
      card.addEventListener("click", () => _ctx.actions.send(String(idx + 1)));
    }
    el.appendChild(card);
  });

  // Partner hand (2v2)
  if (state.partner_hand) {
    const sep = document.createElement("div");
    sep.className = "tc-partner-sep";
    sep.textContent = "parceiro";
    el.appendChild(sep);
    state.partner_hand.forEach((face) => {
      const card = _makeCardEl(face);
      card.classList.add("tc-partner-card");
      el.appendChild(card);
    });
  }
}

function _renderActions(root, state) {
  const el = root.querySelector("#tc-actions");
  el.replaceChildren();
  if (!state.your_turn || state.phase !== "play") return;
  if (state.envite !== null) return; // envite overlay takes over

  if (!state.envite) {
    const btn = document.createElement("button");
    btn.className = "btn secondary";
    btn.textContent = "Truco!";
    btn.addEventListener("click", () => _ctx.actions.send("t"));
    el.appendChild(btn);
  }
}

function _renderMessage(root, state) {
  const el = root.querySelector("#tc-message");
  el.textContent = state.message ?? "";
}

function _renderEnvite(root, state) {
  const overlay = root.querySelector("#tc-envite");
  const isEnvite = state.phase === "envite" && state.envite !== null;
  overlay.classList.toggle("hidden", !isEnvite);
  if (!isEnvite) return;

  const { offer, asker } = state.envite;
  const isAsker = asker === state.you;
  const NAMES = { 3: "Truco", 6: "Seis", 9: "Nove", 12: "Doze" };
  root.querySelector("#tc-envite-title").textContent =
    isAsker
      ? `Você pediu ${NAMES[offer] ?? offer}! Aguardando…`
      : `${state.players[asker]} pediu ${NAMES[offer] ?? offer}!`;

  root.querySelector("#tc-accept").classList.toggle("hidden", isAsker);
  root.querySelector("#tc-raise").classList.toggle("hidden", isAsker || offer >= 12);
  root.querySelector("#tc-run").classList.toggle("hidden", isAsker);
}

// ── timer ──────────────────────────────────────────────────────────────────

function _startTimer(root, deadline) {
  const el = root.querySelector("#tc-timer");
  el.classList.remove("hidden");
  const label = el.querySelector("span");
  const tick = () => {
    const left = Math.max(0, Math.ceil(deadline - Date.now() / 1000));
    label.textContent = left;
    if (left > 0) _timerRaf = requestAnimationFrame(tick);
    else el.classList.add("tc-timer-urgent");
  };
  tick();
}

function _stopTimer(root) {
  if (_timerRaf) { cancelAnimationFrame(_timerRaf); _timerRaf = null; }
  root?.querySelector("#tc-timer")?.classList.add("hidden");
}

// ── helpers ────────────────────────────────────────────────────────────────

function _makeCardEl(face) {
  const str = String(face);
  const suitCode = str.slice(-1);           // C, H, S, D
  const rank = str.slice(0, -1);
  const suitSym = SUIT_LABEL[suitCode] ?? suitCode;
  const isRed = suitCode === "H" || suitCode === "D";
  const el = document.createElement("div");
  el.className = "bj-card" + (isRed ? " red" : "");
  el.innerHTML =
    `<span class="bj-corner bj-corner-tl"><span class="bj-c-suit">${suitSym}</span></span>` +
    `<span class="bj-rank">${RANK_DISPLAY[rank] ?? rank}</span>` +
    `<span class="bj-corner bj-corner-br"><span class="bj-c-suit">${suitSym}</span></span>`;
  return el;
}

function _tablePositions(you, n) {
  // Returns position string per player: "bottom","top","left","right"
  const order = ["bottom", "left", "top", "right"];
  const result = {};
  for (let i = 0; i < n; i++) {
    result[(you + i) % n] = order[i] ?? "top";
  }
  return result;
}

registerView("truco.state", { init, reset, render, gameOver });
