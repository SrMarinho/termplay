import * as THREE from "three";

const BG  = { R:"#c0392b", G:"#27ae60", B:"#2980b9", Y:"#f1c40f", W:"#2d2d2d" };
const FG  = { R:"#fff", G:"#fff", B:"#fff", Y:"#1b1d23", W:"#fff" };

export function makeCardTexture(face, { playable = false, faded = false } = {}) {
  const [ck, val] = face.includes(":") ? face.split(":") : ["W", face];
  const W = 128, H = 192;
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  const c = cv.getContext("2d");

  c.fillStyle = faded ? "#3a3a3a" : (BG[ck] ?? "#2d2d2d");
  c.roundRect(2, 2, W - 4, H - 4, 14);
  c.fill();

  if (playable) {
    c.strokeStyle = "#ffe066"; c.lineWidth = 7;
    c.roundRect(4, 4, W - 8, H - 8, 12);
    c.stroke();
  }

  const lbl = val === "skip"  ? "⊘"
            : val === "reverse" ? "↺"
            : val === "draw2"   ? "+2"
            : val === "wild4"   ? "+4"
            : val || "W";
  c.fillStyle = FG[ck] ?? "#fff";
  c.font = `bold ${lbl.length > 2 ? 36 : 56}px sans-serif`;
  c.textAlign = "center"; c.textBaseline = "middle";
  c.fillText(lbl, W / 2, H / 2);

  c.font = "bold 20px sans-serif";
  c.textBaseline = "top"; c.textAlign = "left";
  c.fillText(lbl, 7, 5);
  c.save();
  c.translate(W - 7, H - 5); c.rotate(Math.PI);
  c.textBaseline = "top"; c.textAlign = "left";
  c.fillText(lbl, 0, 0);
  c.restore();

  const tex = new THREE.CanvasTexture(cv);
  tex.needsUpdate = true;
  return tex;
}

export function makeCardBack() {
  const W = 128, H = 192;
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  const c = cv.getContext("2d");
  c.fillStyle = "#1a237e";
  c.roundRect(2, 2, W - 4, H - 4, 14);
  c.fill();
  c.strokeStyle = "#fff"; c.lineWidth = 3;
  c.roundRect(8, 8, W - 16, H - 16, 10);
  c.stroke();
  c.fillStyle = "#fff"; c.font = "bold 40px sans-serif";
  c.textAlign = "center"; c.textBaseline = "middle";
  c.fillText("UNO", W / 2, H / 2);
  const tex = new THREE.CanvasTexture(cv);
  tex.needsUpdate = true;
  return tex;
}
