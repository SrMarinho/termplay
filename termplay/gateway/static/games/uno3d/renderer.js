// ── public API + orchestration ───────────────────────────────────────────────
// This module owns the mutable `ctx` (scene/camera/handCards/anims/…) and wires
// the pure/stateless pieces (layout, objects, animation, builders, input)
// together. Callers only ever touch init/reset/render.

import { createScene } from "./scene-setup.js";
import { diffAndAnimate } from "./animation.js";
import { buildDiscard, buildDeck, buildOpponents, buildHand, buildDirectionLabel } from "./builders.js";
import { handleClick, handleHover } from "./input.js";
import * as THREE from "three";

let ctx = null;

export function init(canvas, actions) {
  const { scene, camera, renderer, composer } = createScene(canvas);

  ctx = {
    scene, camera, renderer, composer,
    canvas, actions,
    raycaster: new THREE.Raycaster(),
    handCards: [],
    drawMesh: null,
    prevState: null,
    anims: [],
    lastTime: performance.now(),
    raf: null,
  };

  ctx.onClick = (e) => handleClick(ctx, e);
  ctx.onHover = (e) => handleHover(ctx, e);
  canvas.addEventListener("click",     ctx.onClick);
  canvas.addEventListener("mousemove", ctx.onHover);

  ctx.raf = requestAnimationFrame(_loop);
}

export function reset() {
  if (!ctx) return;
  ctx.canvas?.classList.add("hidden");  // hide before WebGL dispose to avoid white flash
  if (ctx.raf) cancelAnimationFrame(ctx.raf);
  ctx.canvas?.removeEventListener("click",     ctx.onClick);
  ctx.canvas?.removeEventListener("mousemove", ctx.onHover);
  ctx.composer?.dispose?.();
  ctx.renderer?.dispose();
  ctx = null;
}

export function render(state) {
  if (!ctx) return;

  // Diff before rebuild
  diffAndAnimate(ctx, ctx.prevState, state);
  ctx.prevState = state;

  // Clear static dynamic objects
  const rm = [];
  ctx.scene.traverse(o => { if (o.userData.dyn) rm.push(o); });
  rm.forEach(o => { ctx.scene.remove(o); o.geometry?.dispose(); });
  ctx.handCards = []; ctx.drawMesh = null;

  buildDiscard(ctx, state);
  buildDeck(ctx);
  buildOpponents(ctx, state);
  buildHand(ctx, state);
  buildDirectionLabel(ctx, state);
}

function _loop() {
  ctx.raf = requestAnimationFrame(_loop);
  const now = performance.now();
  const dt  = Math.min((now - ctx.lastTime) / 1000, 0.1);
  ctx.lastTime = now;

  // Tick animations
  for (let i = ctx.anims.length - 1; i >= 0; i--) {
    if (!ctx.anims[i](dt)) ctx.anims.splice(i, 1);
  }

  // Smooth hover lerp for hand cards
  const LERP = 0.18;
  for (const m of ctx.handCards) {
    if (m.userData.targetX !== undefined) {
      m.position.x += (m.userData.targetX - m.position.x) * LERP;
    }
  }

  ctx.composer?.render();
}
