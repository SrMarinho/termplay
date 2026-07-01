// games/blackjack/index.js — BlackjackView

import { registerView } from "../../core/registry.js";
import { makeCard, makeCardBack } from "../../core/card.js";
import { buildPalette, playerColor } from "../../core/colors.js";
import { createTurnTimer } from "../../core/timer.js";

const ctx = { actions: {}, root: null };
const turnTimer = createTurnTimer({
  onTick: (remaining) => {
    const label = ctx.root?.querySelector(".bj-timer-label");
    if (!label) return;
    label.textContent = Math.ceil(remaining);
    label.classList.toggle("urgent", remaining < 8);
  },
});
let prevCounts = []; // card count per player index

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
  prevCounts = [];
}

function ensureRoot() {
  if (ctx.root) return ctx.root;
  const root = document.createElement("div");
  root.className = "bj-root";
  root.innerHTML =
    `<div class="bj-main">` +
    `<button class="bj-score-toggle btn ghost small">Placar ▸</button>` +
    `<div class="bj-others"></div>` +
    `<div class="bj-center">` +
    `<div class="bj-deck">` +
    `<div class="bj-deck-card"></div>` +
    `<div class="bj-deck-card"></div>` +
    `<div class="bj-deck-card bj-deck-top"></div>` +
    `</div>` +
    `<div class="bj-message"></div>` +
    `<div class="bj-timer hidden"><span class="bj-timer-label">30</span></div>` +
    `</div>` +
    `<div class="bj-me">` +
    `<div class="bj-me-cards"></div>` +
    `<div class="bj-me-info"></div>` +
    `<div class="bj-actions">` +
    `<button class="btn primary bj-hit">Comprar (Hit)</button>` +
    `<button class="btn secondary bj-stand">Parar (Stand)</button>` +
    `</div></div></div>` +
    `<aside class="bj-scoreboard"></aside>`;
  document.getElementById("screen-game").appendChild(root);
  root.querySelector(".bj-hit").addEventListener("click", () => ctx.actions.hit());
  root.querySelector(".bj-stand").addEventListener("click", () => ctx.actions.stand());
  root.querySelector(".bj-score-toggle").addEventListener("click", () => {
    root.querySelector(".bj-scoreboard").classList.toggle("open");
  });
  ctx.root = root;
  return root;
}

function render(state) {
  if (state.phase === "over") { renderOver(state); return; }
  buildPalette(state.players.length);
  const root = ensureRoot();
  root.querySelector(".bj-over")?.remove();

  renderScoreboard(root, state);

  // Collect cards that need fly animation (opacity:0 until flight lands)
  const flyTargets = [];

  renderOthers(root, state, flyTargets);

  const msg = root.querySelector(".bj-message");
  msg.textContent = state.message || (state.your_turn ? "Sua vez!" : "Aguardando…");
  msg.classList.toggle("active", !!state.your_turn);

  // Own hand
  const meCards = root.querySelector(".bj-me-cards");
  const myPrev = prevCounts[state.you] ?? state.hand.length;
  const myNew = Math.max(0, state.hand.length - myPrev);
  meCards.replaceChildren();
  state.hand.forEach((face, i) => {
    const card = makeCard(face);
    if (i >= state.hand.length - myNew) flyTargets.push(card);
    meCards.appendChild(card);
  });
  prevCounts[state.you] = state.hand.length;

  const me = state.players[state.you] || ["você", [], 0, 0, ""];
  const meInfo = root.querySelector(".bj-me-info");
  meInfo.innerHTML =
    `<span class="avatar sm" style="--pc:${playerColor(state.you)}">${esc(initials(me[0]))}</span>` +
    `<span style="color:${playerColor(state.you)}">${esc(me[0])}</span>` +
    `<span class="bj-me-stats"> · total ${state.hand_value}</span>`;

  const canAct = !!state.your_turn;
  root.querySelector(".bj-hit").disabled = !canAct;
  root.querySelector(".bj-stand").disabled = !canAct;
  root.querySelector(".bj-actions").classList.toggle("hidden", !canAct);

  if (state.deadline) startTimer(root, state.deadline);
  else { stopTimer(); root.querySelector(".bj-timer").classList.add("hidden"); }

  // Fly new cards from deck — double rAF ensures layout is computed before reading rects.
  // Real cards are always visible; fly card is a cosmetic overlay.
  if (flyTargets.length) {
    const deckEl = root.querySelector(".bj-deck-top");
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const fromRect = deckEl?.getBoundingClientRect();
      if (!fromRect?.width) return;
      flyTargets.forEach((card, k) => {
        setTimeout(() => flyCard(fromRect, card), k * 110);
      });
    }));
  }
}

function renderScoreboard(root, state) {
  const sb = root.querySelector(".bj-scoreboard");
  sb.replaceChildren();

  const title = document.createElement("div");
  title.className = "bj-sb-title";
  title.textContent = `Meta · ${state.target_score} pts`;
  sb.appendChild(title);

  const ranked = state.players
    .map(([name, , , score], i) => ({ name, score, idx: i }))
    .sort((a, b) => b.score - a.score);

  ranked.forEach(({ name, score, idx }, rank) => {
    const isMe = idx === state.you;
    const isActive = idx === state.current;
    const pct = state.target_score > 0
      ? Math.min(100, Math.round((score / state.target_score) * 100))
      : 0;
    const color = playerColor(idx);

    const row = document.createElement("div");
    row.className = "bj-sb-row" +
      (isMe ? " bj-sb-me" : "") +
      (isActive ? " bj-sb-active" : "");
    row.innerHTML =
      `<div class="bj-sb-top">` +
      `<span class="bj-sb-rank">#${rank + 1}</span>` +
      `<span class="avatar sm" style="--pc:${color}">${esc(initials(name))}</span>` +
      `<span class="bj-sb-name">${esc(name)}${isMe ? " · você" : ""}</span>` +
      `<span class="bj-sb-pts" style="color:${color}">${score}</span>` +
      `</div>` +
      `<div class="bj-sb-bar-wrap">` +
      `<div class="bj-sb-bar" style="width:${pct}%;background:${color}"></div>` +
      `</div>`;
    sb.appendChild(row);
  });
}

function renderOthers(root, state, flyTargets) {
  const wrap = root.querySelector(".bj-others");
  wrap.replaceChildren();
  state.players.forEach((p, i) => {
    if (i === state.you) return;
    const [name, cards, value, , status] = p;

    const prev = prevCounts[i] ?? cards.length;
    const newCount = Math.max(0, cards.length - prev);
    prevCounts[i] = cards.length;

    // Server sends "??" placeholders (and status "") while an opponent's hand
    // is hidden — reveal is a single atomic broadcast once everyone's done,
    // no client-side timing needed.
    const hidden = cards.some((face) => face === "??");

    const seat = document.createElement("div");
    seat.className = "bj-seat" +
      (i === state.current ? " active" : "") +
      (status === "bust" ? " bust" : "");
    seat.dataset.idx = i;

    const statusLabel = STATUS_LABEL[status];
    const head = document.createElement("div");
    head.className = "bj-seat-head";
    head.innerHTML =
      `<span class="avatar sm" style="--pc:${playerColor(i)}">${esc(initials(name))}</span>` +
      `<span class="bj-name" style="color:${playerColor(i)}">${esc(name)}</span>` +
      `<span class="bj-value">${hidden ? "?" : value}</span>` +
      (statusLabel ? `<span class="bj-badge ${status}">${statusLabel}</span>` : "");

    const hand = document.createElement("div");
    hand.className = "bj-seat-cards";
    cards.forEach((face, ci) => {
      const card = hidden ? makeCardBack() : makeCard(face);
      if (ci >= cards.length - newCount) flyTargets.push(card);
      hand.appendChild(card);
    });

    seat.append(head, hand);
    wrap.appendChild(seat);
  });
}

// ── card fly animation ─────────────────────────────────────────────────────────

function flyCard(fromRect, targetEl) {
  const toRect = targetEl.getBoundingClientRect();
  if (!fromRect.width || !toRect.width) return;

  const fly = document.createElement("div");
  Object.assign(fly.style, {
    position: "fixed",
    left: `${fromRect.left}px`,
    top: `${fromRect.top}px`,
    width: `${fromRect.width}px`,
    height: `${fromRect.height}px`,
    zIndex: "300",
    pointerEvents: "none",
    borderRadius: "9px",
    border: "1px solid oklch(74.5% .118 80/.8)",
    background: "linear-gradient(160deg, #3d3720 0%, #2a2410 50%, #1a1508 100%)",
    boxShadow: "0 10px 28px -4px rgba(0,0,0,.9), inset 0 1px 0 oklch(74.5% .118 80/.2)",
    borderRadius: "11px",
  });
  document.body.appendChild(fly);

  const tx = toRect.left - fromRect.left;
  const ty = toRect.top - fromRect.top;
  const sx = toRect.width / fromRect.width;
  const sy = toRect.height / fromRect.height;

  fly.animate([
    { transform: "none", opacity: 1 },
    { transform: `translate(${tx}px,${ty}px) scale(${sx},${sy}) rotate(4deg)`, opacity: 1, offset: 0.65 },
    { transform: `translate(${tx}px,${ty}px) scale(${sx},${sy}) rotate(0deg)`, opacity: 0 },
  ], { duration: 400, easing: "cubic-bezier(.22,1,.36,1)", fill: "forwards" })
    .onfinish = () => fly.remove();
}

// ── game over ──────────────────────────────────────────────────────────────────

function renderOver(state) {
  const root = ensureRoot();
  stopTimer();
  if (root.querySelector(".bj-over")) return;
  const overlay = document.createElement("div");
  // "bj-over" is a bare JS query hook (see render()/renderOver() lookups below) —
  // no CSS rule targets it, all visuals are the Tailwind utilities alongside it.
  overlay.className = "bj-over absolute inset-0 z-[220] flex items-center justify-center bg-black/60";
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

function gameOver() {}

// ── timer ──────────────────────────────────────────────────────────────────────

function startTimer(root, deadlineUnix) {
  root.querySelector(".bj-timer").classList.remove("hidden");
  turnTimer.start(deadlineUnix);
}

function stopTimer() {
  turnTimer.stop();
}

function initials(name) {
  const parts = String(name).trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] || "?") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]
  );
}

const BlackjackView = { init, reset, render, gameOver };
registerView("blackjack.state", BlackjackView);
export default BlackjackView;
