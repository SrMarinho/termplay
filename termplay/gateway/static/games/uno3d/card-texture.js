import * as THREE from "three";

// Matches 2D card design: dark gradient, gold hairline, Art-Deco corners,
// spine, cream serif numerals — "quiet luxury / carta-preta" aesthetic.

const GRAD = {
  R: ["#b82828", "#780e0e"],
  G: ["#3a7858", "#245038"],
  B: ["#1a58c0", "#0a3278"],
  Y: ["#c09030", "#886010"],
  W: ["#1e1c10", "#0f0d06"],
};

const SPINE = {
  R: "#ff8080", G: "#80f0b0", B: "#80b8ff", Y: "#ffe880", W: "rgba(212,175,55,0.4)",
};

const GOLD  = "#D4AF37";
const CREAM = "#F4ECDC";

// Matches 2D VALUE_GLYPH
const SYM = { skip:"⊘", reverse:"⇄", draw2:"+2", wild:"★", wild4:"+4", "":"★" };

function _round(c, x, y, w, h, r) {
  c.beginPath();
  c.moveTo(x + r, y);
  c.arcTo(x + w, y, x + w, y + h, r);
  c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r);
  c.arcTo(x, y, x + w, y, r);
  c.closePath();
}

function _noise(c, W, H, alpha = 0.05) {
  const tmp = document.createElement("canvas");
  tmp.width = W; tmp.height = H;
  const tc = tmp.getContext("2d");
  const id = tc.createImageData(W, H);
  const d = id.data;
  for (let i = 0; i < d.length; i += 4) {
    const v = Math.random() * 255 | 0;
    d[i] = d[i + 1] = d[i + 2] = v; d[i + 3] = 255;
  }
  tc.putImageData(id, 0, 0);
  c.save(); c.globalAlpha = alpha; c.drawImage(tmp, 0, 0); c.restore();
}

function _bracket(c, x, y, corner, color) {
  const S = 22;
  c.strokeStyle = color; c.lineWidth = 3.5;
  c.beginPath();
  if (corner === "tr") {
    c.moveTo(x, y); c.lineTo(x + S, y);
    c.moveTo(x + S, y); c.lineTo(x + S, y + S);
  } else if (corner === "bl") {
    c.moveTo(x, y); c.lineTo(x, y + S);
    c.moveTo(x, y + S); c.lineTo(x + S, y + S);
  } else if (corner === "tl") {
    c.moveTo(x + S, y); c.lineTo(x, y);
    c.moveTo(x, y); c.lineTo(x, y + S);
  } else { // br
    c.moveTo(x, y); c.lineTo(x + S, y);
    c.moveTo(x, y); c.lineTo(x, y + S);
  }
  c.stroke();
}

export function makeCardTexture(face, { playable = false } = {}) {
  const [ck, val] = face.includes(":") ? face.split(":") : ["W", face];
  const W = 256, H = 384;
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  const c = cv.getContext("2d");

  // Background — diagonal gradient matching CSS linear-gradient(160deg,…)
  // (kept in true color even when unplayable — the playable glow already
  // marks which cards can be played, no need to also darken the rest)
  const [c1, c2] = GRAD[ck] ?? GRAD.W;
  const grd = c.createLinearGradient(0, 0, W * 0.65, H);
  grd.addColorStop(0, c1);
  grd.addColorStop(1, c2);
  c.fillStyle = grd;
  _round(c, 0, 0, W, H, 20);
  c.fill();

  // Hairline border
  const borderClr = ck === "W"
    ? "rgba(212,175,55,0.55)"
    : "rgba(244,236,220,0.22)";
  c.strokeStyle = borderClr; c.lineWidth = 4;
  _round(c, 4, 4, W - 8, H - 8, 17);
  c.stroke();

  // Art-Deco corners (TR + BL like 2D card face)
  const decoClr = ck === "W" ? "rgba(212,175,55,0.7)" : "rgba(244,236,220,0.55)";
  _bracket(c, W - 40, 14, "tr", decoClr);
  _bracket(c, 14, H - 36, "bl", decoClr);

  // Spine (thin left bar, like .card-spine in CSS)
  if (ck !== "W") {
    c.fillStyle = (SPINE[ck] ?? CREAM) + "70";
    _round(c, 18, H * 0.22, 5, H * 0.56, 3);
    c.fill();
  }

  // Center value
  const lbl = SYM[val] ?? val ?? "★";
  c.save();
  c.shadowColor = "rgba(0,0,0,0.55)"; c.shadowBlur = 10;
  c.fillStyle = ck === "W" ? GOLD : CREAM;
  const fontSize = lbl.length > 2 ? 96 : 162;
  c.font = `700 ${fontSize}px Georgia, serif`;
  c.textAlign = "center"; c.textBaseline = "middle";
  c.fillText(lbl, W / 2, H / 2);
  c.restore();

  // Corner indices (top-left + bottom-right, matching .card-ix)
  c.fillStyle = ck === "W" ? GOLD : CREAM;
  c.font = "700 46px Georgia, serif";
  c.textAlign = "left"; c.textBaseline = "top";
  c.fillText(lbl, 30, 24);
  c.save();
  c.translate(W - 30, H - 24); c.rotate(Math.PI);
  c.textBaseline = "top"; c.textAlign = "left";
  c.fillText(lbl, 0, 0);
  c.restore();

  // Film grain
  _noise(c, W, H, 0.05);

  // Playable glow — white glow with blur layers
  if (playable) {
    for (const [blur, alpha, lw] of [[18, 0.35, 14], [8, 0.6, 8], [0, 0.95, 4]]) {
      c.save();
      c.shadowColor = "rgba(255,255,255,0.9)";
      c.shadowBlur = blur;
      c.strokeStyle = `rgba(255,255,255,${alpha})`;
      c.lineWidth = lw;
      _round(c, 5, 5, W - 10, H - 10, 17);
      c.stroke();
      c.restore();
    }
  }

  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  tex.needsUpdate = true;
  return tex;
}

export function makeCardBack(glow = false) {
  const W = 256, H = 384;
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  const c = cv.getContext("2d");

  // Near-black surface (matches .card-back / .card.W)
  const grd = c.createLinearGradient(0, 0, W * 0.65, H);
  grd.addColorStop(0, "#1e1c0f");
  grd.addColorStop(1, "#0f0d06");
  c.fillStyle = grd;
  _round(c, 0, 0, W, H, 20);
  c.fill();

  // Gold border
  c.strokeStyle = "rgba(212,175,55,0.55)"; c.lineWidth = 4;
  _round(c, 4, 4, W - 8, H - 8, 17);
  c.stroke();

  // All 4 Art-Deco corners (matches createCardBack with all 4 deco spans)
  const dc = "rgba(212,175,55,0.7)";
  _bracket(c, 14, 14, "tl", dc);
  _bracket(c, W - 36, 14, "tr", dc);
  _bracket(c, 14, H - 36, "bl", dc);
  _bracket(c, W - 36, H - 36, "br", dc);

  // Film grain
  _noise(c, W, H, 0.05);

  // "☘ termplay" monogram
  c.save();
  c.shadowColor = "rgba(0,0,0,0.6)"; c.shadowBlur = 8;
  c.fillStyle = GOLD;
  c.font = "700 52px Georgia, serif";
  c.textAlign = "center"; c.textBaseline = "middle";
  c.fillText("☘", W / 2, H / 2 - 34);
  c.font = "500 30px Georgia, serif";
  c.fillText("termplay", W / 2, H / 2 + 28);
  c.restore();

  // Deck-top glow — gold blur layers, drawn onto the texture (matches the
  // hand card's "playable" highlight instead of a real scene light)
  if (glow) {
    for (const [blur, alpha, lw] of [[18, 0.35, 14], [8, 0.6, 8], [0, 0.9, 4]]) {
      c.save();
      c.shadowColor = "rgba(212,175,55,0.9)";
      c.shadowBlur = blur;
      c.strokeStyle = `rgba(212,175,55,${alpha})`;
      c.lineWidth = lw;
      _round(c, 5, 5, W - 10, H - 10, 17);
      c.stroke();
      c.restore();
    }
  }

  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  tex.needsUpdate = true;
  return tex;
}

export function makeFeltTexture() {
  const W = 512, H = 512;
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  const c = cv.getContext("2d");
  c.fillStyle = "#0c3b1e"; c.fillRect(0, 0, W, H);
  for (let i = 0; i < 120; i++) {
    const x = Math.random() * W;
    c.strokeStyle = `rgba(255,255,255,${Math.random() * 0.025})`;
    c.lineWidth = Math.random() * 1.5 + 0.5;
    c.beginPath(); c.moveTo(x, 0); c.lineTo(x + (Math.random() - 0.5) * 30, H); c.stroke();
  }
  _noise(c, W, H, 0.14);
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(5, 5);
  tex.anisotropy = 8;
  tex.needsUpdate = true;
  return tex;
}
