// uno.js — renders the `uno.state` snapshot as native HTML with deal/play animations.
import { colorName, createCard, createCardBack, parseFace } from "./card.js";

let actions = { play: () => {}, draw: () => {}, chooseColor: () => {}, quit: () => {} };
let prev = null; // last play-phase state, used to diff for animations

const COLOR_BG = { R: "#e63946", G: "#2a9d8f", B: "#457b9d", Y: "#e9c46a", W: "#888" };
const COLOR_ORDER = { R: 0, G: 1, B: 2, Y: 3, W: 4 };

const els = {};
let timerRaf = null;

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
  els.timer = document.getElementById("uno-timer");
  els.timerBar = document.getElementById("uno-timer-bar");
  els.timerLabel = document.getElementById("uno-timer-label");

  for (const btn of els.picker.querySelectorAll("button")) {
    btn.addEventListener("click", () => {
      actions.chooseColor(btn.dataset.color);
      els.picker.classList.add("hidden");
    });
  }
}

export function reset() {
  prev = null;
  stopTimer();
  els.opponents.replaceChildren();
  els.discard.replaceChildren();
  els.hand.replaceChildren();
  els.message.textContent = "";
  els.badge.textContent = "";
  els.picker.classList.add("hidden");
  els.timer.classList.add("hidden");
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

  if (state.your_turn && state.deadline) {
    startTimer(state.deadline);
  } else {
    stopTimer();
    els.timer.classList.add("hidden");
  }

  prev = state;
}

export function gameOver() {
  // game_over arrives after the final uno.state(phase:over); nothing extra needed.
}

// ── opponents arc ─────────────────────────────────────────────────────────────

function renderOpponents(state) {
  // Save old fan rects BEFORE wiping DOM (keyed by player index).
  const oldFanRects = {};
  for (const el of els.opponents.querySelectorAll(".opponent[data-idx]")) {
    const fan = el.querySelector(".fan");
    if (fan) oldFanRects[el.dataset.idx] = fan.getBoundingClientRect();
  }

  // Detect count changes vs prev state.
  const changes = [];
  if (prev) {
    state.players.forEach(([, count], i) => {
      if (i === state.you) return;
      const prevCount = prev.players[i]?.[1];
      if (prevCount === undefined) return;
      if (count < prevCount) changes.push({ idx: i, type: "play" });
      else if (count > prevCount) changes.push({ idx: i, type: "draw" });
    });
  }

  // Rebuild DOM.
  els.opponents.replaceChildren();
  state.players.forEach(([name, count], i) => {
    if (i === state.you) return;
    const seat = document.createElement("div");
    seat.className = "opponent";
    seat.dataset.idx = i;
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

  // Launch flying animations now that new DOM is painted.
  const discardRect = els.discard.getBoundingClientRect();
  const drawRect = els.drawpile.getBoundingClientRect();

  for (const { idx, type } of changes) {
    const newSeat = els.opponents.querySelector(`.opponent[data-idx="${idx}"]`);
    const newFanRect = newSeat?.querySelector(".fan")?.getBoundingClientRect();

    if (type === "play" && oldFanRects[idx] && discardRect.width) {
      flyCardAnim(oldFanRects[idx], discardRect, 300);
    } else if (type === "draw" && newFanRect && drawRect.width) {
      flyCardAnim(drawRect, newFanRect, 350);
    }
  }
}

// ── center: draw pile + discard ───────────────────────────────────────────────

function renderCenter(state, topChanged) {
  els.drawpile.replaceChildren();
  const canDraw = state.your_turn && !state.need_color;
  const pile = createCardBack({
    width: 80, height: 114, onClick: canDraw ? () => actions.draw() : undefined,
  });
  pile.classList.toggle("disabled", !canDraw);
  els.drawpile.appendChild(pile);

  els.discard.replaceChildren();
  const top = createCard(state.top, { width: 92, height: 132 });
  if (topChanged) top.classList.add("slam");
  els.discard.appendChild(top);

  els.badge.textContent = colorName(state.color);
  els.badge.style.background = COLOR_BG[state.color] || "#888";
  els.badge.style.color = state.color === "Y" ? "#1b1d23" : "#fff";

  const dirChanged = !prev || prev.direction !== state.direction;
  els.direction.textContent = state.direction === 1 ? "↻" : "↺";
  els.direction.classList.toggle("reverse", state.direction !== 1);
  if (dirChanged && prev) {
    els.direction.classList.remove("spin");
    void els.direction.offsetWidth;
    els.direction.classList.add("spin");
  }
}

// ── player hand (sorted by color) ────────────────────────────────────────────

function renderHand(state, newCount) {
  els.hand.replaceChildren();
  const playable = new Set(state.playable || []);
  const total = state.hand.length;

  // New cards occupy original indices [total-newCount .. total-1].
  const newOriginalIndices = new Set();
  for (let k = total - newCount; k < total; k++) newOriginalIndices.add(k);

  // Sort by color group, preserving original index for play actions.
  const sorted = state.hand
    .map((face, i) => ({ face, i }))
    .sort((a, b) => {
      const ca = COLOR_ORDER[a.face.split(":")[0]] ?? 4;
      const cb = COLOR_ORDER[b.face.split(":")[0]] ?? 4;
      return ca !== cb ? ca - cb : a.i - b.i;
    });

  sorted.forEach(({ face, i }, displayIdx) => {
    const isPlayable = state.your_turn && !state.need_color && playable.has(i);
    const faded = state.your_turn && !state.need_color && !isPlayable;
    const card = createCard(face, {
      playable: isPlayable,
      faded,
      onClick: isPlayable ? () => playCard(i, card) : undefined,
    });
    if (newOriginalIndices.has(i)) {
      card.classList.add("deal");
      // Stagger: position in sorted display order among new cards.
      const newDisplayPos = [...newOriginalIndices].sort((a, b) => a - b).indexOf(i);
      card.style.animationDelay = `${newDisplayPos * 80}ms`;
    }
    els.hand.appendChild(card);
    void displayIdx;
  });

  const myName = state.players[state.you] ? state.players[state.you][0] : "you";
  els.handinfo.innerHTML =
    `<span class="me-name">${esc(myName)}</span> · ${total} cards` +
    `<span class="hint">highlighted = playable</span>`;
}

// ── play animation ────────────────────────────────────────────────────────────

function playCard(idx, cardEl) {
  const fromRect = cardEl.getBoundingClientRect();
  const toRect = els.discard.getBoundingClientRect();

  const clone = cardEl.cloneNode(true);
  Object.assign(clone.style, {
    position: "fixed",
    left: `${fromRect.left}px`,
    top: `${fromRect.top}px`,
    width: `${fromRect.width}px`,
    height: `${fromRect.height}px`,
    margin: "0",
    zIndex: "200",
    pointerEvents: "none",
    transition: "none",
    animation: "none",
  });
  document.body.appendChild(clone);

  cardEl.style.opacity = "0";
  cardEl.style.pointerEvents = "none";

  const tx = toRect.left + toRect.width / 2 - fromRect.left - fromRect.width / 2;
  const ty = toRect.top + toRect.height / 2 - fromRect.top - fromRect.height / 2;
  const scale = toRect.width / fromRect.width;

  clone.animate(
    [
      { transform: "translate(0,0) scale(1) rotate(0deg)", opacity: 1 },
      { transform: `translate(${tx}px,${ty}px) scale(${scale}) rotate(-8deg)`, opacity: 0.9 },
    ],
    { duration: 320, easing: "cubic-bezier(0.25,0.8,0.35,1)", fill: "forwards" }
  ).onfinish = () => clone.remove();

  actions.play(idx);
}

// ── generic card-back fly (for opponent moves) ────────────────────────────────

function flyCardAnim(fromRect, toRect, duration = 300) {
  const w = 42;
  const h = Math.round(w * 1.42);
  const el = document.createElement("div");
  Object.assign(el.style, {
    position: "fixed",
    left: `${fromRect.left + fromRect.width / 2 - w / 2}px`,
    top: `${fromRect.top + fromRect.height / 2 - h / 2}px`,
    width: `${w}px`,
    height: `${h}px`,
    zIndex: "200",
    pointerEvents: "none",
    borderRadius: "8px",
    border: "2px solid var(--gold)",
    background: "repeating-linear-gradient(45deg,#1b1d23 0 6px,#262a33 6px 12px)",
    boxShadow: "0 4px 10px rgba(0,0,0,.5)",
  });
  document.body.appendChild(el);

  const tx = toRect.left + toRect.width / 2 - (fromRect.left + fromRect.width / 2);
  const ty = toRect.top + toRect.height / 2 - (fromRect.top + fromRect.height / 2);

  el.animate(
    [
      { transform: "translate(0,0) scale(1) rotate(0deg)", opacity: 1 },
      { transform: `translate(${tx}px,${ty}px) scale(0.75) rotate(-6deg)`, opacity: 0.85 },
    ],
    { duration, easing: "cubic-bezier(0.25,0.8,0.35,1)", fill: "forwards" }
  ).onfinish = () => el.remove();
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

// ── turn timer ────────────────────────────────────────────────────────────────

let _timerDeadline = 0;
let _timerTotal = 0;

function startTimer(deadlineUnix) {
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

function stopTimer() {
  if (timerRaf !== null) { cancelAnimationFrame(timerRaf); timerRaf = null; }
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]
  );
}
