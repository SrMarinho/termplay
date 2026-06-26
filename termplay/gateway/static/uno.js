// uno.js — renders the `uno.state` snapshot as native HTML. View only.
let actions = { play: () => {}, draw: () => {}, chooseColor: () => {}, quit: () => {} };
let lastState = null;

const table = document.getElementById("uno-table");
const hand = document.getElementById("uno-hand");
const message = document.getElementById("uno-message");
const picker = document.getElementById("uno-color-picker");
const drawBtn = document.getElementById("uno-draw");

const COLOR_NAME = { R: "red", G: "green", B: "blue", Y: "yellow", W: "wild" };
const VALUE_LABEL = {
  skip: "⊘", reverse: "⇄", draw2: "+2", wild: "WILD", wild4: "+4",
};

export function init(a) {
  actions = a;
  drawBtn.addEventListener("click", () => actions.draw());
  for (const btn of picker.querySelectorAll("button")) {
    btn.addEventListener("click", () => {
      actions.chooseColor(btn.dataset.color);
      picker.classList.add("hidden");
    });
  }
}

export function reset() {
  lastState = null;
  table.replaceChildren();
  hand.replaceChildren();
  message.textContent = "";
  picker.classList.add("hidden");
}

export function render(state) {
  if (state.phase === "toast") {
    flash(state.message);
    return;
  }
  if (state.phase === "over") {
    renderOver(state);
    return;
  }
  lastState = state;
  renderTable(state);
  renderHand(state);
  message.textContent = state.message || (state.your_turn ? "Your turn." : "");
  drawBtn.disabled = !state.your_turn || state.need_color;
  picker.classList.toggle("hidden", !state.need_color);
}

export function gameOver() {
  if (!lastState) return;
  drawBtn.disabled = true;
}

function renderTable(state) {
  table.replaceChildren();
  const arrow = state.direction === 1 ? "↻" : "↺";
  const top = document.createElement("div");
  top.className = "pile";
  top.appendChild(cardEl(state.top, false, false));
  top.appendChild(tag(`active: ${COLOR_NAME[state.color] || state.color} ${arrow}`));
  table.appendChild(top);

  const seats = document.createElement("ul");
  seats.className = "seats";
  (state.players || []).forEach(([name, count], i) => {
    const li = document.createElement("li");
    li.className = "seat";
    if (i === state.current) li.classList.add("current");
    if (i === state.you) li.classList.add("me");
    li.innerHTML = `<span>${esc(name)}</span><span class="count">${count}🂠</span>`;
    seats.appendChild(li);
  });
  table.appendChild(seats);
}

function renderHand(state) {
  hand.replaceChildren();
  const playable = new Set(state.playable || []);
  (state.hand || []).forEach((face, idx) => {
    const enabled = state.your_turn && !state.need_color && playable.has(idx);
    const el = cardEl(face, true, !enabled);
    if (enabled) el.addEventListener("click", () => actions.play(idx));
    hand.appendChild(el);
  });
}

function renderOver(state) {
  table.replaceChildren();
  hand.replaceChildren();
  picker.classList.add("hidden");
  drawBtn.disabled = true;
  message.textContent = state.winner ? `🏆 ${state.winner} won!` : "Game over.";
}

function cardEl(face, inHand, dim) {
  const [color, value] = String(face).split(":");
  const el = document.createElement("div");
  el.className = `card ${color}`;
  if (inHand) el.classList.add("in-hand");
  if (dim) el.classList.add("dim");
  el.textContent = VALUE_LABEL[value] || value;
  return el;
}

function tag(text) {
  const el = document.createElement("span");
  el.className = "pile-tag";
  el.textContent = text;
  return el;
}

let flashTimer = null;
function flash(text) {
  if (!text) return;
  message.textContent = text;
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => {
    if (lastState) {
      message.textContent =
        lastState.message || (lastState.your_turn ? "Your turn." : "");
    }
  }, 2500);
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]
  );
}
