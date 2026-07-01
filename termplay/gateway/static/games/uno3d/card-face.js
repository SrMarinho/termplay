// ── card face formatting helpers ─────────────────────────────────────────────
// Pure string transforms shared by builders.js (static discard pile) and
// animation.js (the flight that lands on it).

// After a Wild/+4 is played, the discard face is repainted in the chosen
// color (state.color) so the active color reads at a glance — easier to see
// which hand cards are playable than a still-black wild card.
export function discardFace(state) {
  const isWild = state.top.startsWith("W:");
  if (!isWild || !state.color || state.color === "W") return state.top;
  const [, value] = state.top.split(":");
  return `${state.color}:${value}`;
}
