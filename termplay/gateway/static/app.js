// app.js — orchestrator: owns the WebSocket and routes messages to screens.
import * as lobby from "./core/lobby.js";
import * as rulesModal from "./core/rules-modal.js";
import * as session from "./core/session.js";
import { allViews, getView } from "./core/registry.js";
import "./games/games.js"; // side-effect: every game view self-registers

// ── Screens ──────────────────────────────────────────────────────────────────

const screens = {
  rooms: document.getElementById("screen-rooms"),
  lobby: document.getElementById("screen-lobby"),
  game:  document.getElementById("screen-game"),
};
const topbar = document.querySelector(".topbar");

function show(name) {
  for (const [key, el] of Object.entries(screens)) el.classList.toggle("active", key === name);
  topbar?.classList.toggle("hidden", name === "game");
}

// ── Active game view ──────────────────────────────────────────────────────────

let activeView = null;

function resetActiveView() {
  activeView?.reset?.();
  activeView = null;
}

function handleRender(content) {
  let state;
  try { state = JSON.parse(content); } catch { return; }
  const view = getView(state.v);
  if (!view) return;
  if (view !== activeView) { activeView?.reset?.(); activeView = view; }
  view.render(state);
}

// ── Nickname ──────────────────────────────────────────────────────────────────

const NICK_KEY = "termplay.nick";
const nickInput = document.getElementById("nick");
const savedNick = localStorage.getItem(NICK_KEY);
if (savedNick) nickInput.value = savedNick;
nickInput.addEventListener("input", () => localStorage.setItem(NICK_KEY, nickInput.value.trim()));

function nickname() {
  return (nickInput.value || "Player").trim().slice(0, 16) || "Player";
}

// ── Gateway ───────────────────────────────────────────────────────────────────

class Gateway {
  constructor(onMessage, onStatus, onClose) {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    this.ws = new WebSocket(`${proto}://${location.host}/ws`);
    this.ws.onopen    = () => onStatus("connected");
    this.ws.onclose   = () => { onStatus("disconnected"); onClose(); };
    this.ws.onerror   = () => onStatus("error");
    this.ws.onmessage = (ev) => onMessage(JSON.parse(ev.data));
  }
  send(obj) {
    if (this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(obj));
  }
}

const connBadge = document.getElementById("conn");
const hostBtn   = document.getElementById("host-btn");
const hostHint  = document.getElementById("host-hint");

function onStatus(status) {
  const labels = { connected: "LAN · estável", disconnected: "LAN · offline", error: "LAN · erro", connecting: "LAN · conectando" };
  connBadge.textContent = labels[status] || `LAN · ${status}`;
  connBadge.className   = `conn ${status}`;
  if (status === "connected") attemptRejoin();
}

const gateway = new Gateway(onMessage, onStatus, () => { hostBtn.disabled = false; hostHint.textContent = ""; });

// ── Session rejoin ────────────────────────────────────────────────────────────

let gameServer  = { ip: "127.0.0.1", port: 4443 };
let rejoinTried = false;

function attemptRejoin() {
  if (rejoinTried) return;
  rejoinTried = true;
  const s = session.load();
  if (s?.code) {
    if (s.nick) nickInput.value = s.nick;
    gateway.send({ action: "join_room", code: s.code, name: s.nick || nickname() });
  }
}

function leaveRoom() {
  session.clear();
  location.reload();
}

// ── Game actions ──────────────────────────────────────────────────────────────

const sendInput = (text) => gateway.send({ action: "game_input", text });
const actions = {
  play:         (idx) => sendInput(String(idx + 1)),
  draw:         ()    => sendInput("d"),
  pass:         ()    => sendInput("p"),
  chooseColor:  (c)   => sendInput(c),
  chooseTarget: (i)   => sendInput(String(i + 1)),
  skipSwap:     ()    => sendInput("skip"),
  tap:          ()    => sendInput("tap"),
  hit:          ()    => sendInput("h"),
  stand:        ()    => sendInput("s"),
  quit:         ()    => sendInput("q"),
  backToLobby:  ()    => { resetActiveView(); show("lobby"); },
};

// ── Message router ────────────────────────────────────────────────────────────

function onMessage(msg) {
  switch (msg.type) {
    case "room_list":
      if (msg.server) gameServer = msg.server;
      lobby.renderRooms(msg.rooms);
      break;
    case "room_created":
      show("lobby");
      lobby.setRole("host", msg.you);
      session.save(msg.code, nickname());
      rulesModal.setGame(selectedGame);
      break;
    case "room_joined":
      show("lobby");
      lobby.setRole("guest", msg.you);
      session.save(msg.code, nickname());
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

// ── Room actions ──────────────────────────────────────────────────────────────

let selectedGame = "uno";

function hostRoom() {
  gateway.send({ action: "create_room", name: nickname(), game: selectedGame });
  hostBtn.disabled    = true;
  hostHint.textContent = "Creating…";
}

function joinRoom(room) {
  gateway.send({ action: "join_room", ip: room.ip, port: room.port, name: nickname() });
}

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

// ── Bootstrap ─────────────────────────────────────────────────────────────────

lobby.init({
  onJoin:   joinRoom,
  onChat:   (text) => gateway.send({ action: "chat", text }),
  onLeave:  () => { gateway.send({ action: "leave" }); leaveRoom(); },
  onStart:  () => gateway.send({ action: "start_game", rules: rulesModal.getRulesSpec() }),
  onAddBot: () => gateway.send({ action: "add_bot" }),
  onKick:   (name) => gateway.send({ action: "kick", target: name }),
});

for (const view of allViews()) view.init(actions);

hostBtn.addEventListener("click", hostRoom);
document.getElementById("host-btn-2")?.addEventListener("click", hostRoom);
document.getElementById("uno-quit")?.addEventListener("click", () => { actions.quit(); leaveRoom(); });

initGameGrid();
rulesModal.init();
