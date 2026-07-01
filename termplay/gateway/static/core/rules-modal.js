// core/rules-modal.js — per-game rule definitions and modal UI.

const GAME_RULE_DEFS = {
  uno: [
    { key: "draw_then_play",     label: "Comprar e jogar",      desc: "pode jogar a carta comprada na hora" },
    { key: "initial_card_effect",label: "Efeito da 1ª carta",   desc: "a primeira carta da pilha já aplica seu efeito" },
    { key: "wild4_strict",       label: "+4 restrito",          desc: "Wild+4 só quando não há outra carta jogável" },
    { key: "stack_draws",        label: "Empilhar +2 / +4",     desc: "compras acumulam para o próximo jogador" },
    { key: "draw_until_play",    label: "Comprar até jogar",    desc: "compra cartas até conseguir uma jogável" },
    { key: "zero_swap",          label: "Carta 0: trocar mão",  desc: "jogar um 0 troca sua mão com a de um jogador" },
    { key: "one_minigame",       label: "Carta 1: minigame",    desc: "jogar um 1 dispara o desafio do ponto; o mais lento compra" },
    { key: "multi_same_number",  label: "Varias do mesmo número", desc: "jogue várias cartas do mesmo número de uma vez (cores diferentes OK)" },
    { key: "manual_draw",        label: "Compra manual",          desc: "comprar cartas forçadas uma por vez — sinta o sofrimento" },
  ],
  blackjack: [
    { key: "bust_penalty", label: "Punição por estourar", desc: "estourar (passar de 21) desconta 1 ponto do placar" },
    { key: "hide_opponent_cards", label: "Esconder cartas dos oponentes", desc: "cartas dos outros jogadores ficam viradas para baixo (mostradas rapidamente ao comprar)" },
  ],
  truco: [
    { key: "mao_de_onze", label: "Mão de onze", desc: "time com 11 pts decide jogar ou correr antes de ver as cartas" },
  ],
};

const GAME_PRESETS = {
  uno: {
    standard: { draw_then_play: true, initial_card_effect: true, wild4_strict: true, stack_draws: false, draw_until_play: false, zero_swap: false, one_minigame: false, multi_same_number: false, manual_draw: false },
    br:       { draw_then_play: false, initial_card_effect: false, wild4_strict: false, stack_draws: true, draw_until_play: true, zero_swap: true, one_minigame: true, multi_same_number: true, manual_draw: true },
  },
  blackjack: {
    standard: { bust_penalty: false, hide_opponent_cards: true },
  },
  truco: {
    standard: { mao_de_onze: true },
  },
};

let _game = "uno";
let _spec = { ...GAME_PRESETS.uno.standard };
let _draft = { ..._spec };

const _modal  = document.getElementById("rules-modal");
const _btn    = document.getElementById("rules-btn");
const _list   = document.getElementById("rule-toggles");
const _chips  = document.getElementById("preset-chips");

function _defs()    { return GAME_RULE_DEFS[_game] ?? []; }
function _presets() { return GAME_PRESETS[_game] ?? {}; }

function _presetName(spec) {
  const defs = _defs();
  for (const [name, preset] of Object.entries(_presets())) {
    if (defs.every((r) => preset[r.key] === spec[r.key])) return name;
  }
  return "custom";
}

function _render() {
  _list.replaceChildren();
  for (const { key, label, desc } of _defs()) {
    const li = document.createElement("li");
    li.className = "rule-toggle";
    li.innerHTML =
      `<div class="rule-text"><span class="rule-label">${label}</span>` +
      `<span class="rule-desc">${desc}</span></div>` +
      `<button class="switch ${_draft[key] ? "on" : ""}" data-key="${key}" type="button"></button>`;
    _list.appendChild(li);
  }
  const multiPreset = Object.keys(_presets()).length > 1;
  _chips?.classList.toggle("hidden", !multiPreset);
  const active = _presetName(_draft);
  for (const chip of document.querySelectorAll(".preset-chip")) {
    chip.classList.toggle("active", chip.dataset.preset === active);
  }
}

function _open() {
  _draft = { ...(Object.values(_presets())[0] ?? {}), ..._spec };
  _render();
  _modal.classList.remove("hidden");
  requestAnimationFrame(() => _modal.classList.add("open"));
}

function _close() {
  _modal.classList.remove("open");
  setTimeout(() => _modal.classList.add("hidden"), 200);
}

export function init() {
  _btn?.addEventListener("click", _open);
  document.getElementById("rules-cancel").addEventListener("click", _close);
  document.getElementById("rules-save").addEventListener("click", () => {
    _spec = { ..._draft };
    _close();
  });
  _modal.addEventListener("click", (e) => { if (e.target === _modal) _close(); });
  _chips?.addEventListener("click", (e) => {
    const chip = e.target.closest(".preset-chip");
    const preset = _presets()[chip?.dataset.preset];
    if (!preset) return;
    _draft = { ...preset };
    _render();
  });
  _list.addEventListener("click", (e) => {
    const sw = e.target.closest(".switch");
    if (!sw) return;
    _draft[sw.dataset.key] = !_draft[sw.dataset.key];
    _render();
  });
}

export function setGame(game) {
  _game = game;
  _spec = { ...(Object.values(_presets())[0] ?? {}) };
  const hasDefs = (_defs().length > 0);
  _btn?.classList.toggle("hidden", !hasDefs);
}

export function getRulesSpec() { return _spec; }
