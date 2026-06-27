// games/uno/table.js — the shared table: opponents arc, draw pile + discard,
// color/direction badges, pending-draw badge, and the card-back fly animation.

import { colorName, createCard, createCardBack } from "./assets/cards.js";
import { COLOR_BG, ctx, els, esc } from "./context.js";

// ── opponents arc ─────────────────────────────────────────────────────────────

export function renderOpponents(state) {
  // Save old fan rects BEFORE wiping DOM (keyed by player index).
  const oldFanRects = {};
  for (const el of els.opponents.querySelectorAll(".opponent[data-idx]")) {
    const fan = el.querySelector(".fan");
    if (fan) oldFanRects[el.dataset.idx] = fan.getBoundingClientRect();
  }

  // Detect count changes vs prev state.
  const changes = [];
  if (ctx.prev) {
    state.players.forEach(([, count], i) => {
      if (i === state.you) return;
      const prevCount = ctx.prev.players[i]?.[1];
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

export function renderCenter(state, topChanged) {
  els.drawpile.replaceChildren();
  const canDraw = state.your_turn && !state.need_color;
  const pile = createCardBack({
    width: 80, height: 114, onClick: canDraw ? () => ctx.actions.draw() : undefined,
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

  renderPendingBadge(state.pending_draws || 0);

  const dirChanged = !ctx.prev || ctx.prev.direction !== state.direction;
  els.direction.textContent = state.direction === 1 ? "↻" : "↺";
  els.direction.classList.toggle("reverse", state.direction !== 1);
  if (dirChanged && ctx.prev) {
    els.direction.classList.remove("spin");
    void els.direction.offsetWidth;
    els.direction.classList.add("spin");
  }
}

function renderPendingBadge(pending) {
  if (!els.discardWrap) return;
  let badge = els.discardWrap.querySelector(".pending-draws-badge");
  if (pending > 0) {
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "pending-draws-badge";
      els.discardWrap.appendChild(badge);
    }
    badge.textContent = `+${pending}`;
  } else if (badge) {
    badge.remove();
  }
}

// ── generic card-back fly (for opponent moves) ────────────────────────────────

export function flyCardAnim(fromRect, toRect, duration = 300) {
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
