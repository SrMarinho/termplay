// games/blackjack/assets/cards.js — renders a French-deck card from a face like
// "A♠" / "10♥". Hearts and diamonds are red; clubs and spades are dark.

const RED_SUITS = new Set(["♥", "♦"]);

export function makeCard(face) {
  const str = String(face);
  const suit = str.slice(-1);
  const rank = str.slice(0, -1);
  const el = document.createElement("div");
  el.className = "bj-card" + (RED_SUITS.has(suit) ? " red" : "");
  el.innerHTML =
    `<span class="bj-rank">${rank}</span><span class="bj-suit">${suit}</span>`;
  return el;
}
