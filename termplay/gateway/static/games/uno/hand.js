// games/uno/hand.js — the local player's hand: color-sorted layout, playable
// highlighting, deal-in stagger, the draw-then-play option, and the play flick.

import { createCard } from "./assets/cards.js";
import { COLOR_ORDER, ctx, els, esc } from "./context.js";

export function renderHand(state, newCount) {
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

  const myName = state.players[state.you] ? state.players[state.you][0] : "you";
  const hint = state.may_play_drawn
    ? `<span class="hint">play the drawn card or pass</span>`
    : `<span class="hint">highlighted = playable</span>`;
  els.handinfo.innerHTML =
    `<span class="me-name">${esc(myName)}</span> · ${total} cards` + hint;

  if (state.may_play_drawn) {
    const passBtn = document.createElement("button");
    passBtn.className = "btn secondary pass-btn";
    passBtn.textContent = "Pass";
    passBtn.addEventListener("click", () => ctx.actions.pass());
    els.handinfo.appendChild(passBtn);
  }
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
