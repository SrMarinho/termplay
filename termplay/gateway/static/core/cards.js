// games/blackjack/assets/cards.js — French-deck card: suit top-left & bottom-right, rank centered.

const RED_SUITS = new Set(["♥", "♦"]);

export function makeCard(face) {
  const str = String(face);
  const suit = str.slice(-1);
  const rank = str.slice(0, -1);
  const el = document.createElement("div");
  el.className = "bj-card" + (RED_SUITS.has(suit) ? " red" : "");
  el.innerHTML =
    `<span class="bj-corner bj-corner-tl"><span class="bj-c-suit">${suit}</span></span>` +
    `<span class="bj-rank">${rank}</span>` +
    `<span class="bj-corner bj-corner-br"><span class="bj-c-suit">${suit}</span></span>`;
  return el;
}
