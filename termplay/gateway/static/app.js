// app.js — orchestrator: owns the WebSocket and routes messages to screens.
import * as lobby from "./lobby.js";
import * as uno from "./uno.js";

const screens = {
  rooms: document.getElementById("screen-rooms"),
  lobby: document.getElementById("screen-lobby"),
  game: document.getElementById("screen-game"),
};

function show(name) {
  for (const [key, el] of Object.entries(screens)) {
    el.classList.toggle("active", key === name);
  }
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
  chooseColor: (c) => sendInput(c),
  quit: () => sendInput("q"),
};

function joinRoom(room) {
  gateway.send({ action: "join_room", ip: room.ip, port: room.port, name: nickname() });
}

function hostRoom() {
  const game = document.getElementById("host-game")?.value || "uno";
  gateway.send({ action: "create_room", name: nickname(), game });
  hostBtn.disabled = true;
  hostHint.textContent = "Creating…";
}

// Wiring --------------------------------------------------------------------
lobby.init({
  onJoin: joinRoom,
  onChat: (text) => gateway.send({ action: "chat", text }),
  onLeave: () => location.reload(),
  onStart: () => gateway.send({ action: "start_game" }),
  onAddBot: () => gateway.send({ action: "add_bot" }),
});
uno.init(actions);

document.getElementById("host-btn").addEventListener("click", hostRoom);
document.getElementById("uno-quit").addEventListener("click", () => {
  actions.quit();
  location.reload();
});

function onStatus(status) {
  connBadge.textContent = status;
  connBadge.className = `conn ${status}`;
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
      break;
    case "room_joined":
      show("lobby");
      lobby.setRole("guest", msg.you);
      break;
    case "room_state":
      lobby.renderState(msg);
      break;
    case "chat":
      lobby.addChat(msg.name, msg.text);
      break;
    case "game_start":
      show("game");
      uno.reset();
      break;
    case "game_render":
      handleRender(msg.content);
      break;
    case "game_over":
      uno.gameOver();
      break;
    case "error":
      alert(msg.message || "Server error");
      if (msg.fatal) location.reload();
      break;
  }
}

function handleRender(content) {
  let state;
  try { state = JSON.parse(content); } catch { return; }
  if (state.v !== "uno.state") return;
  uno.render(state);
}
