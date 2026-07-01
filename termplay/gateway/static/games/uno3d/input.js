// ── pointer input: raycast against the hand + deck, drive hover/click actions ──

import * as THREE from "three";
import { HOVER_PUSH } from "./layout.js";

function toNdc(canvas, e) {
  const r = canvas.getBoundingClientRect();
  return new THREE.Vector2(
    ((e.clientX - r.left) / r.width)  * 2 - 1,
    -((e.clientY - r.top)  / r.height) * 2 + 1
  );
}

function pick(ctx, e) {
  ctx.raycaster.setFromCamera(toNdc(ctx.canvas, e), ctx.camera);
  const hits = ctx.raycaster.intersectObjects([...ctx.handCards, ctx.drawMesh].filter(Boolean), false);
  return hits.length ? hits[0].object : null;
}

export function handleClick(ctx, e) {
  if (!ctx.scene || !ctx.camera) return;
  const o = pick(ctx, e);
  if (!o) return;
  if (o.userData.isDeck)     { ctx.actions.draw?.(); return; }
  if (o.userData.isPlayable) { ctx.actions.play?.(o.userData.handIdx); }
}

export function handleHover(ctx, e) {
  if (!ctx.scene || !ctx.camera) return;
  const hovered  = pick(ctx, e);
  const hoverIdx = hovered?.userData.handIdx;

  // collapsible-style reveal: push the cards on each side away from the
  // hovered one instead of lifting it, so it ends up fully unoccluded
  ctx.handCards.forEach(m => {
    const i = m.userData.handIdx;
    if (hoverIdx === undefined || i === hoverIdx) {
      m.userData.targetX = m.userData.baseX;
    } else if (i < hoverIdx) {
      m.userData.targetX = m.userData.baseX - HOVER_PUSH;
    } else {
      m.userData.targetX = m.userData.baseX + HOVER_PUSH;
    }
  });

  if (hovered) {
    if (hovered.userData.isDeck) hovered.position.y = (hovered.userData.baseY ?? 0.032) + 0.15;
    ctx.canvas.style.cursor = (hovered.userData.isPlayable || hovered.userData.isDeck) ? "pointer" : "default";
  } else {
    ctx.canvas.style.cursor = "default";
  }
}
