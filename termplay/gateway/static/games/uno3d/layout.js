// ── pure layout math: where cards sit and how they're oriented ────────────────
// No THREE/DOM dependencies — safe to unit test in isolation.

// Camera position (kept in sync with scene-setup.js's PerspectiveCamera)
export const CAM_Y = 11, CAM_Z = 6.5;

// ── opponents (standing in an arc around the table) ────────────────────────────
export const OPP_R      = 2.4;   // radius from center
export const OPP_CARD_Y = 0.55;  // height when standing

export function oppPos(j, N) {
  const halfArc = N <= 1 ? 0 : Math.min(2.27, Math.PI / 2 + (N - 2) * 0.28);
  const a = N <= 1 ? 0 : -halfArc + j * (2 * halfArc / (N - 1));
  const x = OPP_R * Math.sin(a);
  const z = -OPP_R * Math.cos(a);
  // rotation.y so back face points toward camera (camera.z ≈ 10)
  const ry = Math.atan2(OPP_R * Math.sin(a), -(10 + OPP_R * Math.cos(a)));
  // rotation.x so card face is perpendicular to the line of sight from the
  // (high, steep) camera — same idea as the hand's TILT constant, but computed
  // per-position since opponents are spread across an arc.
  const horiz = Math.hypot(x, CAM_Z - z);
  const rx = -Math.atan2(CAM_Y - OPP_CARD_Y, horiz);
  return { x, z, a, ry, rx };
}

// ── the local player's hand ─────────────────────────────────────────────────────
export const ARC_X      = (n) => Math.min(n * 0.22, 4.2);   // overlap step between cards
export const HOVER_PUSH = 0.4;   // how far neighbors slide apart to reveal the hovered card
// Camera (0,11,6.5) → hand center (0,0.75,2.3): face camera = arcsin(Δy/d)
// Δy=10.25, Δz=4.2, d≈11.08 → arcsin(0.925) ≈ 1.18 rad
export const TILT   = 1.18;
export const BASE_Y = 0.75;
export const HAND_Z = 2.3;   // base Z for hand — close, but kept inside the frustum

export function handPos(i, n) {
  const t = n > 1 ? (i / (n - 1)) * 2 - 1 : 0;
  return {
    x:   t * (ARC_X(n) / 2),
    y:   BASE_Y,   // flat row — playable/hover no longer lift, they push neighbors apart instead
    z:   HAND_Z,   // same depth for every card
    rx:  -TILT,
    rz:  0,        // straight — no fan tilt; overlap does the work
    t,
  };
}
