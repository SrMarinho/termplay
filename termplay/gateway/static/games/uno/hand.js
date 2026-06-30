// games/uno/hand.js — the local player's hand: color-sorted layout, playable
// highlighting, deal-in stagger, the draw-then-play option, and the play flick.

import { createCard } from "./assets/cards.js";
import { COLOR_ORDER, ctx, els, esc } from "./context.js";
import { playerColor } from "../../core/colors.js";

export function renderHand(state, newCount) {
  els.hand.replaceChildren();
  if (!state.multi_played?.length) document.getElementById("uno-multi-played")?.remove();
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

  sorted.forEach(({ face, i }) => {
    const isPlayable = state.your_turn && !state.need_color && playable.has(i);
    const faded = state.your_turn && !state.need_color && !isPlayable;
    const card = createCard(face, {
      playable: isPlayable,
      faded,
      onClick: isPlayable ? () => playCard(i, card) : undefined,
    });
    if (state.may_play_drawn && i === state.drawn_card_idx) {
      card.classList.add("drawn-option");
    }
    if (newOriginalIndices.has(i)) {
      card.classList.add("deal");
      // Stagger: position in sorted display order among new cards.
      const newDisplayPos = [...newOriginalIndices].sort((a, b) => a - b).indexOf(i);
      card.style.animationDelay = `${newDisplayPos * 80}ms`;
    }
    els.hand.appendChild(card);
  });

  const inMulti          = state.your_turn && state.multi_played?.length > 0;
  const inDraw           = state.draws_remaining > 0;
  const inStack          = state.your_turn && (state.pending_draws ?? 0) > 0 && !inMulti && !inDraw;
  const inDrewUnplayable = state.your_turn && state.drew_unplayable === true;
  const myName = state.players[state.you] ? state.players[state.you][0] : "você";
  const ini = initials(myName);
  const turnText = inDraw
    ? `compre a próxima carta (${state.draws_remaining} restantes)`
    : inDrewUnplayable
    ? "sem carta jogável — compre a próxima ou passe"
    : inStack
    ? `+${state.pending_draws} acumulados — empilhe +2/+4 ou aceite`
    : inMulti
    ? `${state.multi_played.length}× jogadas — continue ou passe`
    : state.may_play_drawn
    ? "jogue a carta comprada ou passe"
    : state.your_turn ? "sua vez" : "aguarde sua vez";
  els.handinfo.innerHTML =
    `<span class="avatar" style="--pc:${playerColor(state.you)}">${esc(ini)}</span>` +
    `<div class="me-body"><span class="me-name">${esc(myName)} · você</span>` +
    `<span class="me-sub">${total} cartas · ${turnText}</span></div>` +
    `<div class="hand-actions"></div>`;
  const actions = els.handinfo.querySelector(".hand-actions");

  if (inDraw) {
    const drawBtn = document.createElement("button");
    drawBtn.className = "btn primary small";
    drawBtn.textContent = `Comprar (${state.draws_remaining} restantes)`;
    drawBtn.addEventListener("click", () => ctx.actions.draw());
    actions.appendChild(drawBtn);
  } else if (inDrewUnplayable) {
    const nextBtn = document.createElement("button");
    nextBtn.className = "btn primary small";
    nextBtn.textContent = "Próxima carta";
    nextBtn.addEventListener("click", () => ctx.actions.draw());
    actions.appendChild(nextBtn);
    const passBtn = document.createElement("button");
    passBtn.className = "btn ghost small";
    passBtn.textContent = "Passar";
    passBtn.addEventListener("click", () => ctx.actions.pass());
    actions.appendChild(passBtn);
  } else if (inMulti) {
    const stopBtn = document.createElement("button");
    stopBtn.className = "btn secondary small";
    stopBtn.textContent = `Terminar turno (${state.multi_played.length}×)`;
    stopBtn.addEventListener("click", () => ctx.actions.pass());
    actions.appendChild(stopBtn);
  } else if (state.may_play_drawn) {
    const passBtn = document.createElement("button");
    passBtn.className = "btn ghost small";
    passBtn.textContent = "Passar";
    passBtn.addEventListener("click", () => ctx.actions.pass());
    actions.appendChild(passBtn);
  } else if (state.your_turn && !state.need_color) {
    const drawBtn = document.createElement("button");
    drawBtn.className = "btn primary small";
    const pd = state.pending_draws ?? 0;
    drawBtn.textContent = pd > 0 ? `Aceitar (+${pd} cartas)` : "Comprar";
    if (pd > 0) drawBtn.classList.add("stack-accept");
    drawBtn.addEventListener("click", () => ctx.actions.draw());
    actions.appendChild(drawBtn);
  }

  if (inMulti) renderMultiPlayed(state.multi_played);
}

function renderMultiPlayed(faces) {
  document.getElementById("uno-multi-played")?.remove();
  const bar = document.createElement("div");
  bar.id = "uno-multi-played";
  bar.className = "uno-multi-bar";
  const val = faces[0]?.split(":")[1] ?? "";
  bar.innerHTML =
    `<span class="uno-multi-count">${faces.length}×</span>` +
    `<span class="uno-multi-label">${val}</span>` +
    `<span class="uno-multi-pips">` +
    faces.map((f) => `<span class="uno-multi-pip">${_suitIcon(f)}</span>`).join("") +
    `</span>`;
  els.handinfo.after(bar);
}

function _suitIcon(face) {
  const color = face.split(":")[0];
  const val   = face.split(":")[1] ?? face;
  const colors = { R: "#d96b63", G: "#5bab6a", B: "#5b8fd9", Y: "#d9b84a", W: "#aaa" };
  const c = colors[color] || "#aaa";
  return `<span style="color:${c};font-weight:700">${val}</span>`;
}

// Initials for the player avatar (e.g. "Otávio Ramires" → "OR").
function initials(name) {
  const parts = String(name).trim().split(/\s+/).filter(Boolean);
  const a = parts[0]?.[0] || "?";
  const b = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (a + b).toUpperCase();
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

  ctx.actions.play(idx);
}
