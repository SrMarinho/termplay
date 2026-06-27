// games/uno/table.js — the shared table: opponents arc, draw pile + discard,
// color/direction badges, pending-draw badge, and the card-back fly animation.

import { colorName, createCard, createCardBack } from "./assets/cards.js";
import { COLOR_BG, ctx, els, esc } from "./context.js";

// ── opponents arc ─────────────────────────────────────────────────────────────

// Initials for a player avatar (e.g. "Helena Vaz" → "HV").
function initials(name) {
  const parts = String(name).trim().split(/\s+/).filter(Boolean);
  const a = parts[0]?.[0] || "?";
  const b = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (a + b).toUpperCase();
}

export function renderOpponents(state) {
  // Save old pip-stack rects BEFORE wiping DOM (keyed by player index).
  const oldRects = {};
  for (const el of els.opponents.querySelectorAll(".opponent[data-idx]")) {
    const pips = el.querySelector(".opp-pips");
    if (pips) oldRects[el.dataset.idx] = pips.getBoundingClientRect();
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

  // Rebuild DOM — a row of horizontal seats with avatar + count + pip stack.
  els.opponents.replaceChildren();
  state.players.forEach(([name, count], i) => {
    if (i === state.you) return;
    const seat = document.createElement("div");
    seat.className = "opponent";
    seat.dataset.idx = i;
    if (i === state.current) seat.classList.add("active");

    const isBot = String(name).startsWith("Bot");
    const pips = Array.from({ length: Math.min(count, 7) }, () => `<span class="pip"></span>`).join("");
    seat.innerHTML =
      `<span class="avatar sm">${esc(initials(name))}</span>` +
      `<div class="opp-body"><span class="opp-name">${esc(name)}` +
      (isBot ? ` <span class="badge bot">bot</span>` : "") + `</span>` +
      `<span class="opp-count">${count} cartas</span></div>` +
      `<div class="opp-pips">${pips}</div>`;

    els.opponents.appendChild(seat);
  });

  // Launch flying animations now that new DOM is painted.
  const discardRect = els.discard.getBoundingClientRect();
  const drawRect = els.drawpile.getBoundingClientRect();

  for (const { idx, type } of changes) {
    const newSeat = els.opponents.querySelector(`.opponent[data-idx="${idx}"]`);
    const newRect = newSeat?.querySelector(".opp-pips")?.getBoundingClientRect();

    if (type === "play" && oldRects[idx] && discardRect.width) {
      flyCardAnim(oldRects[idx], discardRect, 300);
    } else if (type === "draw" && newRect && drawRect.width) {
      flyCardAnim(drawRect, newRect, 350);
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
    border: "1px solid oklch(74.5% .118 80/.6)",
    background: "linear-gradient(160deg,#23200F,#141109)",
    boxShadow: "0 8px 18px -6px rgba(0,0,0,.6)",
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
