// ── flight animations + prev→next state diffing ────────────────────────────────
// Consumes a shared `ctx` (see renderer.js) so animations can add meshes to the
// live scene and register per-frame tick callbacks without each caller needing
// to know about ctx.scene / ctx.anims individually.

import * as THREE from "three";
import { makeCardMesh, makeCardBackMesh } from "./objects.js";
import { handPos, oppPos, OPP_CARD_Y } from "./layout.js";
import { discardFace } from "./card-face.js";

function easeInOut(p) { return p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; }

// ── fly card A→B with a parabolic arc ───────────────────────────────────────────
export function flyCard(ctx, { face, fromPos, fromRot, toPos, toRot, dur = 0.4,
                                isBack = false, arcH = 1.2, delay = 0 }) {
  const m = isBack ? makeCardBackMesh() : makeCardMesh(face ?? "W:", {});
  m.userData.dyn  = false;  // survives render() rebuild
  m.userData.anim = true;
  ctx.scene.add(m);

  const fp = new THREE.Vector3(...fromPos);
  const tp = new THREE.Vector3(...toPos);
  const fr = new THREE.Euler(...fromRot, "ZYX");
  const tr = new THREE.Euler(...toRot,   "ZYX");

  let elapsed = -delay;
  ctx.anims.push((dt) => {
    elapsed += dt;
    if (elapsed < 0) { m.visible = false; return true; }
    m.visible = true;
    const p = easeInOut(Math.min(elapsed / dur, 1));
    m.position.lerpVectors(fp, tp, p);
    m.position.y += Math.sin(p * Math.PI) * arcH;
    m.rotation.x  = fr.x + (tr.x - fr.x) * p;
    m.rotation.y  = fr.y + (tr.y - fr.y) * p;
    m.rotation.z  = fr.z + (tr.z - fr.z) * p;
    if (elapsed >= dur) { ctx.scene.remove(m); m.geometry?.dispose(); return false; }
    return true;
  });
}

// ── card flips (face-down → face-up) while flying ──────────────────────────────
export function flipCard(ctx, { face, fromPos, fromRot, toPos, toRot, dur = 0.42, delay = 0 }) {
  const mBack  = makeCardBackMesh();
  const mFront = makeCardMesh(face ?? "W:", {});
  mBack.userData.dyn = mFront.userData.dyn = false;
  mBack.userData.anim = mFront.userData.anim = true;
  mFront.visible = false;
  ctx.scene.add(mBack); ctx.scene.add(mFront);

  const fp = new THREE.Vector3(...fromPos);
  const tp = new THREE.Vector3(...toPos);
  const fr = new THREE.Euler(...fromRot, "ZYX");
  const tr = new THREE.Euler(...toRot,   "ZYX");

  let elapsed = -delay;
  ctx.anims.push((dt) => {
    elapsed += dt;
    if (elapsed < 0) return true;
    const p   = easeInOut(Math.min(elapsed / dur, 1));
    const pos = new THREE.Vector3().lerpVectors(fp, tp, p);
    pos.y    += Math.sin(p * Math.PI) * 1.0;
    const rx  = fr.x + (tr.x - fr.x) * p;
    const rz  = fr.z + (tr.z - fr.z) * p;
    const ry  = p * Math.PI * 2;           // full spin around Y during flight

    const setM = (m) => { m.position.copy(pos); m.rotation.set(rx, ry, rz, "ZYX"); };
    if (p < 0.5) { mBack.visible = true; mFront.visible = false; setM(mBack); }
    else         { mBack.visible = false; mFront.visible = true;  setM(mFront); }

    if (elapsed >= dur) {
      ctx.scene.remove(mBack);  mBack.geometry?.dispose();
      ctx.scene.remove(mFront); mFront.geometry?.dispose();
      return false;
    }
    return true;
  });
}

// ── diff prev→next state and spawn the matching animations ─────────────────────
export function diffAndAnimate(ctx, prev, next) {
  if (!prev || !next?.hand) return;

  const topChanged  = next.top !== prev.top;
  const handShrank  = next.hand.length < prev.hand.length;
  const handGrew    = next.hand.length > prev.hand.length;
  const prevHand    = prev.hand ?? [];
  const deckPos     = [-0.85, 0.04, 0.2];
  const deckRot     = [-Math.PI / 2, 0, 0];
  const discardPos  = [0.85, 0.04, 0.2];
  const discardRot  = [-Math.PI / 2, 0, 0.2];

  // ── card played: hand shrinks + top changed ──────────────────────────────
  if (handShrank && topChanged && next.top) {
    const idx  = prevHand.indexOf(next.top);   // played card's index in the previous hand
    const n    = prevHand.length;
    const pos  = handPos(idx >= 0 ? idx : Math.floor(n / 2), n);
    flyCard(ctx, {
      face: discardFace(next),
      fromPos: [pos.x, pos.y, pos.z],
      fromRot: [pos.rx, 0, pos.rz],
      toPos:   discardPos,
      toRot:   discardRot,
      dur:     0.42,
      arcH:    1.4,
    });
  }

  // ── cards drawn: my hand grew ─────────────────────────────────────────────
  if (handGrew) {
    const added  = next.hand.length - prevHand.length;
    const isDeal = prevHand.length === 0 && next.hand.length > 3;

    for (let k = 0; k < added; k++) {
      const targetIdx = prevHand.length + k;
      const face       = next.hand[targetIdx] ?? next.hand[next.hand.length - 1 - k];
      const pos        = handPos(targetIdx, next.hand.length);
      flipCard(ctx, {
        face,
        fromPos: deckPos,
        fromRot: deckRot,
        toPos:   [pos.x, pos.y, pos.z],
        toRot:   [pos.rx, 0, pos.rz],
        dur:     0.38,
        delay:   isDeal ? k * 0.08 : 0,
      });
    }
  }

  // ── opponent drew or played a card ───────────────────────────────────────
  const players = next.players ?? [];
  const opps = players
    .map((p, i) => ({ idx: i, count: p[1] }))
    .filter(o => o.idx !== next.you);
  const N = opps.length;

  opps.forEach((opp, j) => {
    const { x, z, ry, rx } = oppPos(j, N);
    const oppPosXYZ = [x, OPP_CARD_Y, z];
    const oppRot    = [rx, ry, 0];
    const prevCount = prev.players?.[opp.idx]?.[1] ?? 0;
    const gained    = opp.count - prevCount;
    const lost      = prevCount - opp.count;

    if (gained > 0) {
      for (let k = 0; k < Math.min(gained, 3); k++) {
        flyCard(ctx, { face: "W:", fromPos: deckPos, fromRot: deckRot,
          toPos: oppPosXYZ, toRot: oppRot, dur: 0.45, arcH: 0.9, isBack: true, delay: k * 0.06 });
      }
    }

    if (lost > 0 && topChanged && next.top) {
      flyCard(ctx, { face: discardFace(next), fromPos: oppPosXYZ, fromRot: oppRot,
        toPos: discardPos, toRot: discardRot, dur: 0.48, arcH: 1.3 });
    }
  });
}
