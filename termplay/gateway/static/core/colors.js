// Player color palette — built once per game from the actual player count.
// Hues are evenly distributed around the OKLCH wheel so no two colors look similar.
// START_HUE = 80 anchors player 0 near the design's gold tone.
const START_HUE = 80;
const L = 68;   // lightness % — readable on dark backgrounds
const C = 0.13; // chroma — vivid but not garish

let _palette = [];
let _builtFor = 0;

export function buildPalette(count) {
  if (count === _builtFor || count < 1) return;
  _builtFor = count;
  const step = 360 / count;
  _palette = Array.from({ length: count }, (_, i) => {
    const hue = (START_HUE + step * i) % 360;
    return `oklch(${L}% ${C} ${hue.toFixed(1)})`;
  });
}

export function playerColor(idx) {
  if (!_palette.length) return `oklch(${L}% ${C} ${START_HUE})`; // pre-game fallback
  return _palette[((idx ?? 0) + _palette.length) % _palette.length];
}
