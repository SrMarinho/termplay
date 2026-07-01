// ── mesh/sprite factories ────────────────────────────────────────────────────
// Builds the actual THREE objects used everywhere else (static table, hand,
// opponents, fly/flip animations). Kept free of scene/state concerns.

import * as THREE from "three";
import { makeCardTexture, makeCardBack } from "./card-texture.js";

const CARD_GEO = () => new THREE.BoxGeometry(0.66, 0.96, 0.018);

export function makeCardMesh(face, opts = {}) {
  const edge = new THREE.MeshStandardMaterial({ color: 0x1a1510, roughness: 0.7 });
  const mats = [edge, edge, edge, edge,
    new THREE.MeshStandardMaterial({ map: makeCardTexture(face, opts), roughness: 0.55, metalness: 0.05, transparent: true, alphaTest: 0.5 }),
    new THREE.MeshStandardMaterial({ map: makeCardBack(), roughness: 0.55, transparent: true, alphaTest: 0.5 }),
  ];
  const m = new THREE.Mesh(CARD_GEO(), mats);
  m.castShadow = true; m.userData.dyn = true;
  return m;
}

export function makeCardBackMesh(glow = false) {
  const m = new THREE.Mesh(CARD_GEO(), new THREE.MeshStandardMaterial({
    map: makeCardBack(glow), roughness: 0.55, transparent: true, alphaTest: 0.5,
  }));
  m.castShadow = true; m.userData.dyn = true;
  return m;
}

export function makeTextSprite(text, x, y, z, color = "#fff", scale = 1) {
  const cv = document.createElement("canvas");
  cv.width = 256; cv.height = 64;
  const c  = cv.getContext("2d");
  c.fillStyle = color; c.font = "bold 28px sans-serif";
  c.textAlign = "center"; c.textBaseline = "middle";
  c.fillText(text, 128, 32);
  const sp = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), transparent: true })
  );
  sp.scale.set(2.2 * scale, 0.55 * scale, 1);
  sp.position.set(x, y, z); sp.userData.dyn = true;
  return sp;
}
