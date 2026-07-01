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

export function makeTextSprite(text, x, y, z, color = "#F4ECDC", scale = 1) {
  const cv = document.createElement("canvas");
  cv.width = 256; cv.height = 64;
  const c  = cv.getContext("2d");
  c.shadowColor = "rgba(0,0,0,0.7)"; c.shadowBlur = 6;
  c.fillStyle = color; c.font = "600 28px Georgia, serif";
  c.textAlign = "center"; c.textBaseline = "middle";
  c.fillText(text, 128, 32);
  const sp = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), transparent: true })
  );
  sp.scale.set(2.2 * scale, 0.55 * scale, 1);
  sp.position.set(x, y, z); sp.userData.dyn = true;
  return sp;
}

// A circular arrow (looping ring with an arrowhead) — shows the turn order
// direction without needing any text.
export function makeDirectionSprite(direction, x, y, z, color = "#D4AF37", scale = 1) {
  const cv = document.createElement("canvas");
  cv.width = 128; cv.height = 128;
  const c  = cv.getContext("2d");
  const cx = 64, cy = 64, r = 42;
  const ccw = direction === -1;

  const start = -Math.PI * 0.65;
  const end   =  Math.PI * 0.65;

  c.strokeStyle = color; c.lineWidth = 8; c.lineCap = "round";
  c.beginPath();
  c.arc(cx, cy, r, start, end, ccw);
  c.stroke();

  // arrowhead at the stroke's terminal point, tangent to the circle — small
  // relative to the ring's radius so it hugs the curve instead of drooping inward
  const tipAngle = end;
  const tipX = cx + r * Math.cos(tipAngle);
  const tipY = cy + r * Math.sin(tipAngle);
  const tangent = tipAngle + (ccw ? -Math.PI / 2 : Math.PI / 2);
  c.fillStyle = color;
  c.save();
  c.translate(tipX, tipY);
  c.rotate(tangent);
  c.beginPath();
  c.moveTo(0, 0);      // apex — local +x now points along the tangent (direction of travel)
  c.lineTo(-9, -6);
  c.lineTo(-9, 6);
  c.closePath();
  c.fill();
  c.restore();

  const sp = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), transparent: true })
  );
  sp.scale.set(0.7 * scale, 0.7 * scale, 1);
  sp.position.set(x, y, z); sp.userData.dyn = true;
  return sp;
}
