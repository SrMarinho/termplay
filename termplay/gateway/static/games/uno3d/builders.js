// ── static scene builders ────────────────────────────────────────────────────
// Turns a game `state` snapshot into meshes added to ctx.scene. Called once per
// render() after diffAndAnimate() has already spawned the transition animations.

import * as THREE from "three";
import { makeCardMesh, makeCardBackMesh, makeTextSprite, makeDirectionSprite } from "./objects.js";
import { oppPos, handPos, OPP_CARD_Y } from "./layout.js";
import { discardFace } from "./card-face.js";

export function buildDiscard(ctx, state) {
  if (!state.top) return;
  const m = makeCardMesh(discardFace(state));
  m.rotation.x = -Math.PI / 2; m.rotation.z = 0.2;
  m.position.set(0.85, 0.02, 0.2);
  ctx.scene.add(m);
}

export function buildDeck(ctx) {
  const STACK = 14;
  for (let k = 0; k < STACK; k++) {
    const isTop = k === STACK - 1;
    const m = makeCardBackMesh(isTop);   // top card glows (same style as hand's playable highlight)
    m.rotation.x = -Math.PI / 2;
    m.position.set(-0.85, 0.02 + k * 0.012, 0.2);
    if (isTop) {
      m.userData.isDeck = true;
      ctx.drawMesh = m;
    }
    ctx.scene.add(m);
  }
}

export function buildOpponents(ctx, state) {
  const players = state.players || [];
  const opps = players
    .map((p, i) => ({ name: p[0], cards: p[1], idx: i }))
    .filter(p => p.idx !== state.you);
  const N = opps.length;

  opps.forEach((opp, j) => {
    const { x, z } = oppPos(j, N);
    const n      = Math.min(opp.cards, 12);
    const active = opp.idx === state.current;
    const SPREAD = Math.min(n * 0.13, 2.0);

    // compute facing ONCE per hand (at its center) so every card in the hand
    // shares the exact same orientation — no per-card tilt drift
    const pivot = new THREE.Object3D();
    pivot.position.set(x, OPP_CARD_Y, z);
    pivot.lookAt(ctx.camera.position);
    pivot.rotateY(Math.PI);   // box front normal is +Z; lookAt points -Z at target
    const handQuat = pivot.quaternion;

    for (let k = 0; k < n; k++) {
      const t = n > 1 ? (k / (n - 1)) * 2 - 1 : 0;
      const m = makeCardBackMesh();
      m.position.set(x + t * (SPREAD / 2), OPP_CARD_Y, z);   // fan on X only — keep every card at the same Z
      m.quaternion.copy(handQuat);
      m.renderOrder = k;
      ctx.scene.add(m);
    }
    ctx.scene.add(makeTextSprite(opp.name + (active ? " ◀" : ""), x, 1.9, z, active ? "#E8C56B" : "#B9B3A4"));
  });
}

export function buildHand(ctx, state) {
  const hand     = state.hand || [];
  const playable = new Set(state.playable || []);
  const n        = hand.length;
  if (!n) return;

  hand.forEach((face, i) => {
    const isPlayable = state.your_turn && !state.need_color && playable.has(i);
    const pos        = handPos(i, n);
    const m          = makeCardMesh(face, { playable: isPlayable });
    m.rotation.order = "ZYX";
    m.rotation.x     = pos.rx;
    m.rotation.z     = pos.rz;
    m.position.set(pos.x, pos.y, pos.z);
    m.renderOrder         = i;
    m.userData.handIdx    = i;
    m.userData.isPlayable = isPlayable;
    m.userData.baseX      = pos.x;
    m.userData.targetX    = pos.x;
    ctx.handCards.push(m);
    ctx.scene.add(m);
  });
}

export function buildDirectionLabel(ctx, state) {
  ctx.scene.add(makeDirectionSprite(state.direction, 0, 0.15, 0.2, "#D4AF37"));
}
