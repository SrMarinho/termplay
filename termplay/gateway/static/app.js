// app.js — orchestrator: owns the WebSocket and routes messages to screens.
import * as lobby from "./core/lobby.js";
import { allViews, getView } from "./core/registry.js";
import "./games/games.js"; // side-effect: every game view self-registers

// The currently rendering game view (resolved from the state `v` tag).
let activeView = null;

function resetActiveView() {
  activeView?.reset?.();
  activeView = null;
}

const screens = {
  rooms: document.getElementById("screen-rooms"),
  lobby: document.getElementById("screen-lobby"),
  game: document.getElementById("screen-game"),
};

const topbar = document.querySelector(".topbar");

function show(name) {
  for (const [key, el] of Object.entries(screens)) {
    el.classList.toggle("active", key === name);
  }
  // The game screen has its own header — hide the global topbar to avoid two navbars.
  if (topbar) topbar.classList.toggle("hidden", name === "game");
}

class Gateway {
  constructor(onMessage, onStatus, onClose) {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    this.ws = new WebSocket(`${proto}://${location.host}/ws`);
    this.ws.onopen = () => onStatus("connected");
    this.ws.onclose = () => { onStatus("disconnected"); onClose(); };
    this.ws.onerror = () => onStatus("error");
    this.ws.onmessage = (ev) => onMessage(JSON.parse(ev.data));
  }
  send(obj) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj));
    }
  }
}

const nickInput = document.getElementById("nick");
const connBadge = document.getElementById("conn");

function nickname() {
  return (nickInput.value || "Player").trim().slice(0, 16) || "Player";
}

const hostBtn = document.getElementById("host-btn");
const hostHint = document.getElementById("host-hint");

function resetHostButton() {
  hostBtn.disabled = false;
  hostHint.textContent = "";
}

const gateway = new Gateway(onMessage, onStatus, resetHostButton);

// Tracks the game server address received from room_list for create_room.
let gameServer = { ip: "127.0.0.1", port: 4443 };

// Browser → server action senders ------------------------------------------
const sendInput = (text) => gateway.send({ action: "game_input", text });
const actions = {
  play: (idx) => sendInput(String(idx + 1)),
  draw: () => sendInput("d"),
  pass: () => sendInput("p"),
  chooseColor: (c) => sendInput(c),
  chooseTarget: (globalIdx) => sendInput(String(globalIdx + 1)),
  tap: () => sendInput("tap"),
  hit: () => sendInput("h"),
  stand: () => sendInput("s"),
  quit: () => sendInput("q"),
  // After a match ends, go back to the lobby room (for a rematch), not the room list.
  backToLobby: () => { resetActiveView(); show("lobby"); },
};

function joinRoom(room) {
  gateway.send({ action: "join_room", ip: room.ip, port: room.port, name: nickname() });
}

let selectedGame = "uno";

function hostRoom() {
  gateway.send({ action: "create_room", name: nickname(), game: selectedGame });
  hostBtn.disabled = true;
  hostHint.textContent = "Creating…";
}

// Clickable game tiles: one stays selected, drives selectedGame.
function initGameGrid() {
  const tiles = document.querySelectorAll(".game-tile");
  for (const tile of tiles) {
    tile.addEventListener("click", () => {
      tiles.forEach((t) => t.classList.remove("selected"));
      tile.classList.add("selected");
      selectedGame = tile.dataset.game || "uno";
    });
  }
}

// ── Uno rules: configured in the lobby via an animated modal ────────────────
const RULE_DEFS = [
  { key: "draw_then_play", label: "Comprar e jogar", desc: "pode jogar a carta comprada na hora" },
  { key: "initial_card_effect", label: "Efeito da 1ª carta", desc: "a primeira carta da pilha já aplica seu efeito" },
  { key: "wild4_strict", label: "+4 restrito", desc: "Wild+4 só quando não há outra carta jogável" },
  { key: "stack_draws", label: "Empilhar +2 / +4", desc: "compras acumulam para o próximo jogador" },
  { key: "draw_until_play", label: "Comprar até jogar", desc: "compra cartas até conseguir uma jogável" },
  { key: "zero_swap", label: "Carta 0: trocar mão", desc: "jogar um 0 troca sua mão com a de um jogador" },
  { key: "one_minigame", label: "Carta 1: minigame", desc: "jogar um 1 dispara o desafio do ponto; o mais lento compra" },
];
const PRESETS = {
  standard: { draw_then_play: true, initial_card_effect: true, wild4_strict: true, stack_draws: false, draw_until_play: false, zero_swap: false, one_minigame: false },
  br: { draw_then_play: false, initial_card_effect: false, wild4_strict: false, stack_draws: true, draw_until_play: true, zero_swap: true, one_minigame: true },
};
let rulesSpec = { ...PRESETS.standard };
let rulesDraft = { ...rulesSpec };

const rulesModal = document.getElementById("rules-modal");
const rulesBtn = document.getElementById("rules-btn");

function presetName(spec) {
  for (const [name, preset] of Object.entries(PRESETS)) {
    if (RULE_DEFS.every((r) => preset[r.key] === spec[r.key])) return name;
  }
  return "custom";
}

function renderRulesModal() {
  const list = document.getElementById("rule-toggles");
  list.replaceChildren();
  for (const { key, label, desc } of RULE_DEFS) {
    const li = document.createElement("li");
    li.className = "rule-toggle";
    li.innerHTML =
      `<div class="rule-text"><span class="rule-label">${label}</span>` +
      `<span class="rule-desc">${desc}</span></div>` +
      `<button class="switch ${rulesDraft[key] ? "on" : ""}" data-key="${key}" type="button"></button>`;
    list.appendChild(li);
  }
  const active = presetName(rulesDraft);
  for (const chip of document.querySelectorAll(".preset-chip")) {
    chip.classList.toggle("active", chip.dataset.preset === active);
  }
}

function openRulesModal() {
  rulesDraft = { ...rulesSpec };
  renderRulesModal();
  rulesModal.classList.remove("hidden");
  requestAnimationFrame(() => rulesModal.classList.add("open"));
}

function closeRulesModal() {
  rulesModal.classList.remove("open");
  setTimeout(() => rulesModal.classList.add("hidden"), 200);
}

function initRulesModal() {
  rulesBtn?.addEventListener("click", openRulesModal);
  document.getElementById("rules-cancel").addEventListener("click", closeRulesModal);
  document.getElementById("rules-save").addEventListener("click", () => {
    rulesSpec = { ...rulesDraft };
    closeRulesModal();
  });
  rulesModal.addEventListener("click", (e) => {
    if (e.target === rulesModal) closeRulesModal();
  });
  document.getElementById("preset-chips").addEventListener("click", (e) => {
    const chip = e.target.closest(".preset-chip");
    if (!chip || !PRESETS[chip.dataset.preset]) return;
    rulesDraft = { ...PRESETS[chip.dataset.preset] };
    renderRulesModal();
  });
  document.getElementById("rule-toggles").addEventListener("click", (e) => {
    const sw = e.target.closest(".switch");
    if (!sw) return;
    rulesDraft[sw.dataset.key] = !rulesDraft[sw.dataset.key];
    renderRulesModal();
  });
}

// Wiring --------------------------------------------------------------------
lobby.init({
  onJoin: joinRoom,
  onChat: (text) => gateway.send({ action: "chat", text }),
  onLeave: () => { gateway.send({ action: "leave" }); leaveRoom(); },
  onStart: () => gateway.send({ action: "start_game", rules: rulesSpec }),
  onAddBot: () => gateway.send({ action: "add_bot" }),
  onKick: (name) => gateway.send({ action: "kick", target: name }),
});
for (const view of allViews()) view.init(actions);

document.getElementById("host-btn").addEventListener("click", hostRoom);
initGameGrid();
initRulesModal();
document.getElementById("uno-quit").addEventListener("click", () => {
  actions.quit();
  leaveRoom();
});

// ── session persistence: survive a page reload by rejoining the room ────────
const SESSION_KEY = "termplay.session";

function saveSession(code) {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({ code, nick: nickname() }));
  } catch { /* storage unavailable */ }
}
function clearSession() {
  try { sessionStorage.removeItem(SESSION_KEY); } catch { /* ignore */ }
}
function loadSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null"); }
  catch { return null; }
}

let rejoinTried = false;
function attemptRejoin() {
  if (rejoinTried) return;
  rejoinTried = true;
  const s = loadSession();
  if (s && s.code) {
    if (s.nick) nickInput.value = s.nick;
    gateway.send({ action: "join_room", code: s.code, name: s.nick || nickname() });
  }
}

function leaveRoom() {
  clearSession();
  location.reload();
}

function onStatus(status) {
  connBadge.textContent = status;
  connBadge.className = `conn ${status}`;
  if (status === "connected") attemptRejoin();
}

function onMessage(msg) {
  switch (msg.type) {
    case "room_list":
      if (msg.server) gameServer = msg.server;
      lobby.renderRooms(msg.rooms);
      break;
    case "room_created":
      show("lobby");
      lobby.setRole("host", msg.you);
      saveSession(msg.code);
      // Rules button only for the host and only for Uno.
      rulesBtn?.classList.toggle("hidden", selectedGame !== "uno");
      break;
    case "room_joined":
      show("lobby");
      lobby.setRole("guest", msg.you);
      saveSession(msg.code);
      break;
    case "room_state":
      lobby.renderState(msg);
      break;
    case "chat":
      lobby.addChat(msg.name, msg.text);
      break;
    case "game_start":
      show("game");
      resetActiveView();
      break;
    case "game_render":
      handleRender(msg.content);
      break;
    case "game_over":
      activeView?.gameOver();
      break;
    case "error":
      alert(msg.message || "Server error");
      if (msg.fatal) leaveRoom();
      break;
  }
}

function handleRender(content) {
  let state;
  try { state = JSON.parse(content); } catch { return; }
  const view = getView(state.v);
  if (!view) return;
  if (view !== activeView) {
    activeView?.reset?.();
    activeView = view;
  }
  view.render(state);
}
