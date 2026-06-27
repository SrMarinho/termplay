// card.js — builds UNO card DOM. Pure view component, reused by hand/discard/opponents.
//
// "Quiet luxury" card: dessaturated suit-colour surface, hairline gold frame,
// Art-Deco corner brackets (top-right + bottom-left), a serif numeral in the
// centre and small serif indices on the free corners (top-left + bottom-right).
// Modelled on the carta-preta reference; the Wild card uses the same black
// surface as the deck back.

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
  return { R: "Vermelho", G: "Verde", B: "Azul", Y: "Amarelo", W: "Curinga" }[c] ?? c;
}

// Appends the two Art-Deco corner brackets (top-right + bottom-left) so the
// free corners stay clear for the indices.
function addDeco(el) {
  for (const pos of ["tr", "bl"]) {
    const d = document.createElement("span");
    d.className = `card-deco ${pos}`;
    el.appendChild(d);
  }
}

/**
 * Build a card element.
 * @param {string} face  server face string, e.g. "R:7"
 * @param {object} opts  {width,height,playable,faded,onClick}
 */
export function createCard(face, opts = {}) {
  const { width = 70, height = 100, playable = false, faded = false, onClick } = opts;
  const { color, value } = parseFace(face);
  const display = glyph(value);
  const wide = display.length > 1;

  const el = document.createElement(onClick ? "button" : "div");
  el.className = `card ${color}`;
  if (playable) el.classList.add("playable");
  if (faded) el.classList.add("faded");
  el.style.width = `${width}px`;
  el.style.height = `${height}px`;
  el.style.setProperty("--ix-size", `${Math.round(height * 0.13)}px`);
  el.style.setProperty("--val-size", `${Math.round(height * (wide ? 0.3 : 0.44))}px`);

  addDeco(el);
  if (color !== "W") {
    const spine = document.createElement("span");
    spine.className = "card-spine";
    el.appendChild(spine);
  }

  const top = document.createElement("span");
  top.className = "card-ix card-ix-top";
  top.textContent = display;
  const val = document.createElement("span");
  val.className = "card-val";
  val.textContent = display;
  const bot = document.createElement("span");
  bot.className = "card-ix card-ix-bot";
  bot.textContent = display;
  el.append(top, val, bot);

  if (onClick) {
    el.type = "button";
    el.addEventListener("click", onClick);
  }
  return el;
}

/** Build a face-down card back (carta-preta: black surface, gold frame, monogram). */
export function createCardBack(opts = {}) {
  const { width = 50, height = 72, onClick } = opts;
  const el = document.createElement(onClick ? "button" : "div");
  el.className = "card-back";
  el.style.width = `${width}px`;
  el.style.height = `${height}px`;
  for (const pos of ["tl", "tr", "bl", "br"]) {
    const d = document.createElement("span");
    d.className = `card-deco ${pos}`;
    el.appendChild(d);
  }
  const mark = document.createElement("span");
  mark.className = "card-back-mark";
  // Narrow backs (opponent fans, draw pile) only have room for the leaf monogram.
  mark.innerHTML = width >= 64
    ? `<span class="card-back-leaf">☘</span><span class="card-back-word">termplay</span>`
    : `<span class="card-back-leaf">☘</span>`;
  el.appendChild(mark);
  if (onClick) {
    el.type = "button";
    el.addEventListener("click", onClick);
  }
  return el;
}
