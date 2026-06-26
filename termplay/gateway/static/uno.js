// uno.js — renders the `uno.state` snapshot as native HTML with deal/play animations.
import { colorName, createCard, createCardBack, parseFace } from "./card.js";

let actions = { play: () => {}, draw: () => {}, chooseColor: () => {}, quit: () => {} };
let prev = null; // last play-phase state, used to diff for animations

const COLOR_BG = { R: "#e63946", G: "#2a9d8f", B: "#457b9d", Y: "#e9c46a", W: "#888" };

const els = {};

export function init(a) {
  actions = a;
  els.opponents = document.getElementById("uno-opponents");
  els.drawpile = document.getElementById("uno-drawpile");
  els.discard = document.getElementById("uno-discard");
  els.badge = document.getElementById("uno-colorbadge");
  els.direction = document.getElementById("uno-direction");
  els.message = document.getElementById("uno-message");
  els.picker = document.getElementById("uno-color-picker");
  els.hand = document.getElementById("uno-hand");
  els.handinfo = document.getElementById("uno-handinfo");

  for (const btn of els.picker.querySelectorAll("button")) {
    btn.addEventListener("click", () => {
      actions.chooseColor(btn.dataset.color);
      els.picker.classList.add("hidden");
    });
  }
}

export function reset() {
  prev = null;
  els.opponents.replaceChildren();
  els.discard.replaceChildren();
  els.hand.replaceChildren();
  els.message.textContent = "";
  els.badge.textContent = "";
  els.picker.classList.add("hidden");
}

export function render(state) {
  if (state.phase === "toast") { flash(state.message); return; }
  if (state.phase === "over") { renderOver(state); return; }

  const handGrew = prev && state.hand.length > prev.hand.length;
  const newCount = handGrew ? state.hand.length - prev.hand.length : 0;
  const topChanged = !prev || prev.top !== state.top;

  renderOpponents(state);
  renderCenter(state, topChanged);
  renderHand(state, newCount);

  els.message.textContent = state.message || (state.your_turn ? "Your turn" : "Waiting…");
  els.message.classList.toggle("active", !!state.your_turn);
  els.picker.classList.toggle("hidden", !state.need_color);

  prev = state;
}

export function gameOver() {
  // game_over arrives after the final uno.state(phase:over); nothing extra needed.
}

// ── opponents arc ─────────────────────────────────────────────────────────────

function renderOpponents(state) {
  els.opponents.replaceChildren();
  const total = state.players.length;
  state.players.forEach(([name, count], i) => {
    if (i === state.you) return;
    const seat = document.createElement("div");
    seat.className = "opponent";
    if (i === state.current) seat.classList.add("active");

    const fan = document.createElement("div");
    fan.className = "fan";
    const shown = Math.min(count, 7);
    for (let j = 0; j < shown; j++) {
      const back = createCardBack({ width: 38, height: 54 });
      back.style.marginLeft = j === 0 ? "0" : "-24px";
      back.style.transform = `rotate(${(j - shown / 2) * 5}deg)`;
      fan.appendChild(back);
    }
    const label = document.createElement("div");
    label.className = "opponent-label";
    const isBot = String(name).startsWith("Bot");
    label.innerHTML =
      `<span class="opp-name">${esc(name)}</span>` +
      (isBot ? `<span class="badge bot">BOT</span>` : "") +
      `<span class="opp-count">· ${count} cards</span>`;

    seat.append(fan, label);
    els.opponents.appendChild(seat);
  });
  void total;
}

// ── center: draw pile + discard ───────────────────────────────────────────────

function renderCenter(state, topChanged) {
  // Draw pile (clickable card back)
  els.drawpile.replaceChildren();
  const canDraw = state.your_turn && !state.need_color;
  const pile = createCardBack({
    width: 80, height: 114, onClick: canDraw ? () => actions.draw() : undefined,
  });
  pile.classList.toggle("disabled", !canDraw);
  els.drawpile.appendChild(pile);

  // Discard top
  els.discard.replaceChildren();
  const top = createCard(state.top, { width: 92, height: 132 });
  if (topChanged) top.classList.add("slam");
  els.discard.appendChild(top);

  // Active color badge
  els.badge.textContent = colorName(state.color);
  els.badge.style.background = COLOR_BG[state.color] || "#888";
  els.badge.style.color = state.color === "Y" ? "#1b1d23" : "#fff";

  // Direction arrow
  els.direction.textContent = state.direction === 1 ? "↻" : "↺";
}

// ── player hand ───────────────────────────────────────────────────────────────

function renderHand(state, newCount) {
  els.hand.replaceChildren();
  const playable = new Set(state.playable || []);
  const total = state.hand.length;
  state.hand.forEach((face, i) => {
    const isPlayable = state.your_turn && !state.need_color && playable.has(i);
    const faded = state.your_turn && !state.need_color && !isPlayable;
    const card = createCard(face, {
      playable: isPlayable,
      faded,
      onClick: isPlayable ? () => playCard(i, card) : undefined,
    });
    // Newly drawn cards (trailing) animate in.
    if (newCount > 0 && i >= total - newCount) {
      card.classList.add("deal");
      card.style.animationDelay = `${(i - (total - newCount)) * 80}ms`;
    }
    els.hand.appendChild(card);
  });

  const myName = state.players[state.you] ? state.players[state.you][0] : "you";
  els.handinfo.innerHTML =
    `<span class="me-name">${esc(myName)}</span> · ${total} cards` +
    `<span class="hint">highlighted = playable</span>`;
}

function playCard(idx, cardEl) {
  // Fly the played card toward the discard pile before sending the move.
  cardEl.classList.add("playing");
  actions.play(idx);
}

// ── toast / game over ─────────────────────────────────────────────────────────

let flashTimer = null;
function flash(text) {
  if (!text) return;
  els.message.textContent = text;
  els.message.classList.add("flash");
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => {
    els.message.classList.remove("flash");
    if (prev) {
      els.message.textContent =
        prev.message || (prev.your_turn ? "Your turn" : "Waiting…");
    }
  }, 2500);
}

function renderOver(state) {
  els.picker.classList.add("hidden");
  const overlay = document.createElement("div");
  overlay.className = "uno-over";
  overlay.innerHTML =
    `<div class="over-card">` +
    `<div class="over-title">${state.winner ? `🏆 ${esc(state.winner)} wins!` : "Game over"}</div>` +
    `<button class="over-btn" id="over-leave">Back to rooms</button>` +
    `</div>`;
  document.getElementById("screen-game").appendChild(overlay);
  document.getElementById("over-leave").addEventListener("click", () => {
    actions.quit();
    location.reload();
  });
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]
  );
}
