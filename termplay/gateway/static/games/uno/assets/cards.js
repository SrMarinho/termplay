// card.js — builds UNO card DOM. Pure view component, reused by hand/discard/opponents.

const COLOR_BG = { R: "#e63946", G: "#2a9d8f", B: "#457b9d", Y: "#e9c46a" };

// Maps server card values ("skip","reverse","draw2","wild","wild4","0".."9")
// to a short display glyph.
const VALUE_GLYPH = {
  skip: "⊘", reverse: "⇄", draw2: "+2", wild: "★", wild4: "+4",
};

// Parses a server face string like "R:7" or "W:wild4" into {color, value}.
export function parseFace(face) {
  const [color, value] = String(face).split(":");
  return { color, value };
}

export function glyph(value) {
  return VALUE_GLYPH[value] ?? value;
}

export function colorName(c) {
  return { R: "Red", G: "Green", B: "Blue", Y: "Yellow", W: "Wild" }[c] ?? c;
}

/**
 * Build a card element.
 * @param {string} face  server face string, e.g. "R:7"
 * @param {object} opts  {width,height,playable,faded,onClick}
 */
export function createCard(face, opts = {}) {
  const { width = 70, height = 100, playable = false, faded = false, onClick } = opts;
  const { color, value } = parseFace(face);
  const isWild = color === "W";
  const display = glyph(value);

  const el = document.createElement(onClick ? "button" : "div");
  el.className = "card";
  if (playable) el.classList.add("playable");
  if (faded) el.classList.add("faded");
  el.style.width = `${width}px`;
  el.style.height = `${height}px`;
  el.style.background = isWild ? "#1b1d23" : COLOR_BG[color];

  if (isWild) {
    const stripes = document.createElement("div");
    stripes.className = "card-wild";
    el.appendChild(stripes);
  }

  const oval = document.createElement("div");
  oval.className = "card-oval";
  oval.style.fontSize = display.length > 1 ? `${height * 0.22}px` : `${height * 0.32}px`;
  const inner = document.createElement("span");
  inner.textContent = display;
  oval.appendChild(inner);
  el.appendChild(oval);

  const tl = document.createElement("span");
  tl.className = "card-corner tl";
  tl.textContent = display;
  const br = document.createElement("span");
  br.className = "card-corner br";
  br.textContent = display;
  el.append(tl, br);

  if (onClick) {
    el.type = "button";
    el.addEventListener("click", onClick);
  }
  return el;
}

/** Build a face-down card back (for opponents and the draw pile). */
export function createCardBack(opts = {}) {
  const { width = 50, height = 72, onClick } = opts;
  const el = document.createElement(onClick ? "button" : "div");
  el.className = "card-back";
  el.style.width = `${width}px`;
  el.style.height = `${height}px`;
  el.textContent = "UNO";
  if (onClick) {
    el.type = "button";
    el.addEventListener("click", onClick);
  }
  return el;
}
