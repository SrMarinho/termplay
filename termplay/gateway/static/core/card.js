// core/card.js — shared playing-card element factory (French-deck, 52-card style).
// Used by Blackjack and Truco; face strings are "<rank><suit>", where suit is
// either already the display symbol (Blackjack) or a letter code translatable
// via a `suitMap` (Truco: C/H/S/D → ♣/♥/♠/♦).

const RED_SUITS = new Set(["♥", "♦"]);

export function makeCard(face, { suitMap } = {}) {
  const str = String(face);
  const suitCode = str.slice(-1);
  const rank = str.slice(0, -1);
  const suit = suitMap ? (suitMap[suitCode] ?? suitCode) : suitCode;
  const el = document.createElement("div");
  el.className = "bj-card" + (RED_SUITS.has(suit) ? " red" : "");
  el.innerHTML =
    `<span class="bj-corner bj-corner-tl"><span class="bj-c-suit">${suit}</span></span>` +
    `<span class="bj-rank">${rank}</span>` +
    `<span class="bj-corner bj-corner-br"><span class="bj-c-suit">${suit}</span></span>`;
  return el;
}

export function makeCardBack() {
  const el = document.createElement("div");
  el.className = "bj-card bj-card-back";
  return el;
}

export function makeCardPlaceholder() {
  const el = document.createElement("div");
  el.className = "bj-card bj-card-placeholder";
  return el;
}
