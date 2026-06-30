import * as THREE from "three";

const BG  = { R:"#c0392b", G:"#27ae60", B:"#2980b9", Y:"#f1c40f", W:"#2d2d2d" };
const FG  = { R:"#fff", G:"#fff", B:"#fff", Y:"#1b1d23", W:"#fff" };
const SYM = { skip:"⊘", reverse:"↺", draw2:"+2", wild4:"+4", "":"★" };

function _round(c, x, y, w, h, r) {
  c.beginPath();
  c.moveTo(x + r, y);
  c.arcTo(x + w, y, x + w, y + h, r);
  c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r);
  c.arcTo(x, y, x + w, y, r);
  c.closePath();
}

export function makeCardTexture(face, { playable = false, faded = false } = {}) {
  const [ck, val] = face.includes(":") ? face.split(":") : ["W", face];
  const W = 256, H = 384;
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  const c = cv.getContext("2d");

  // fundo cor
  const base = faded ? "#3a3a3a" : (BG[ck] ?? "#2d2d2d");
  c.fillStyle = base;
  _round(c, 0, 0, W, H, 28); c.fill();

  // moldura branca externa
  c.strokeStyle = "#fdfdfa"; c.lineWidth = 16;
  _round(c, 12, 12, W - 24, H - 24, 22); c.stroke();

  // oval branca central (marca UNO)
  c.save();
  c.translate(W / 2, H / 2); c.rotate(-Math.PI / 4);
  c.fillStyle = "#fdfdfa";
  c.beginPath(); c.ellipse(0, 0, W * 0.34, H * 0.42, 0, 0, Math.PI * 2); c.fill();
  c.restore();

  // valor central dentro do oval
  const lbl = SYM[val] ?? val ?? "W";
  c.fillStyle = faded ? "#777" : (BG[ck] ?? "#222");
  c.font = `900 ${lbl.length > 2 ? 88 : 150}px Georgia, serif`;
  c.textAlign = "center"; c.textBaseline = "middle";
  c.fillText(lbl, W / 2, H / 2);

  // cantos
  c.fillStyle = "#fff";
  c.font = "900 40px Georgia, serif";
  c.textAlign = "left"; c.textBaseline = "top";
  c.fillText(lbl, 22, 18);
  c.save(); c.translate(W - 22, H - 18); c.rotate(Math.PI);
  c.fillText(lbl, 0, 0); c.restore();

  // brilho diagonal sutil (gloss)
  const g = c.createLinearGradient(0, 0, W, H);
  g.addColorStop(0, "rgba(255,255,255,0.10)");
  g.addColorStop(0.5, "rgba(255,255,255,0)");
  c.fillStyle = g; _round(c, 0, 0, W, H, 28); c.fill();

  // glow jogável
  if (playable) {
    c.strokeStyle = "#ffe066"; c.lineWidth = 10;
    _round(c, 6, 6, W - 12, H - 12, 24); c.stroke();
  }

  const tex = new THREE.CanvasTexture(cv);
  tex.anisotropy = 8;
  tex.needsUpdate = true;
  return tex;
}

export function makeCardBack() {
  const W = 256, H = 384;
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  const c = cv.getContext("2d");

  // fundo azul
  c.fillStyle = "#16205c";
  _round(c, 0, 0, W, H, 28); c.fill();

  // moldura branca
  c.strokeStyle = "#fdfdfa"; c.lineWidth = 14;
  _round(c, 12, 12, W - 24, H - 24, 22); c.stroke();

  // oval vermelha diagonal
  c.save();
  c.translate(W / 2, H / 2); c.rotate(-Math.PI / 4);
  c.fillStyle = "#c0392b";
  c.beginPath(); c.ellipse(0, 0, W * 0.36, H * 0.44, 0, 0, Math.PI * 2); c.fill();
  c.restore();

  // marca UNO
  c.save();
  c.translate(W / 2, H / 2); c.rotate(-Math.PI / 8);
  c.fillStyle = "#f1c40f";
  c.font = "900 72px Georgia, serif";
  c.textAlign = "center"; c.textBaseline = "middle";
  c.strokeStyle = "#fff"; c.lineWidth = 4;
  c.strokeText("UNO", 0, 0);
  c.fillText("UNO", 0, 0);
  c.restore();

  const tex = new THREE.CanvasTexture(cv);
  tex.anisotropy = 8;
  tex.needsUpdate = true;
  return tex;
}
