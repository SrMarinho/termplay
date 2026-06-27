// lobby.js — room list + lobby (players, chat, host controls). Pure view.
let handlers = {
  onJoin: () => {}, onChat: () => {}, onLeave: () => {},
  onStart: () => {}, onAddBot: () => {}, onKick: () => {},
};
let role = "guest"; // "host" | "guest"
let myName = "";

const roomList = document.getElementById("room-list");
const noRooms = document.getElementById("no-rooms");
const roomCount = document.getElementById("room-count");
const lobbyCode = document.getElementById("lobby-code");
const lobbyPlayers = document.getElementById("lobby-players");
const chatLog = document.getElementById("chat-log");
const hostControls = document.getElementById("host-controls");
const guestWait = document.getElementById("guest-wait");
const startBtn = document.getElementById("start-btn");
const startHint = document.getElementById("start-hint");

export function init(h) {
  handlers = h;
  document.getElementById("chat-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = document.getElementById("chat-input");
    const text = input.value.trim();
    if (text) { handlers.onChat(text); input.value = ""; }
  });
  document.getElementById("leave-btn").addEventListener("click", handlers.onLeave);
  document.getElementById("start-btn").addEventListener("click", handlers.onStart);
  document.getElementById("addbot-btn").addEventListener("click", handlers.onAddBot);
}

export function setRole(r, name) {
  role = r;
  myName = name || myName;
  hostControls.classList.toggle("hidden", role !== "host");
  guestWait.classList.toggle("hidden", role === "host");
}

export function renderRooms(rooms) {
  roomList.replaceChildren();
  noRooms.style.display = rooms.length ? "none" : "block";
  roomCount.textContent = rooms.length ? `${rooms.length} total` : "";
  for (const room of rooms) {
    const li = document.createElement("li");
    li.className = "room";
    const joinable = room.status === "waiting" && room.players < room.max_players;
    const info = document.createElement("div");
    info.className = "room-info";
    info.innerHTML =
      `<div class="room-host">${esc(room.host)} <span class="badge game">${esc(room.game)}</span></div>` +
      `<div class="room-sub muted">${room.players}/${room.max_players} players` +
      `${room.status === "playing" ? " · in progress" : ""}</div>`;
    const btn = document.createElement("button");
    btn.className = "btn secondary";
    btn.textContent = room.status === "playing" ? "in game" : joinable ? "Join" : "full";
    btn.disabled = !joinable;
    btn.addEventListener("click", () => handlers.onJoin(room));
    li.append(info, btn);
    roomList.appendChild(li);
  }
}

export function renderState(state) {
  lobbyCode.textContent = state.code ? `· room ${state.code}` : "";
  lobbyPlayers.replaceChildren();
  const bots = new Set(state.bots || []);
  for (const name of state.players || []) {
    const li = document.createElement("li");
    const isBot = bots.has(name);
    li.innerHTML =
      `<span class="dot" style="background:${isBot ? "#9ca0ac" : "#2a9d8f"}"></span>` +
      `<span class="pl-name">${esc(name)}</span>` +
      (name === myName ? `<span class="badge you">you</span>` : "") +
      (name === state.host ? `<span class="badge host">host</span>` : "") +
      (isBot ? `<span class="badge bot">bot</span>` : "");
    // Host can remove anyone except themselves (the host seat).
    if (role === "host" && name !== state.host) {
      const kick = document.createElement("button");
      kick.className = "kick-btn";
      kick.title = "Remover";
      kick.textContent = "✕";
      kick.addEventListener("click", () => handlers.onKick(name));
      li.appendChild(kick);
    }
    lobbyPlayers.appendChild(li);
  }
  if (role === "host") {
    startBtn.disabled = !state.can_start;
    startHint.textContent = state.can_start
      ? ""
      : `Need ${state.min_players} players (${state.player_count} now)`;
  }
}

export function addChat(name, text) {
  const li = document.createElement("li");
  li.innerHTML = `<b style="color:${nickColor(name)}">${esc(name)}</b>: ${esc(text)}`;
  chatLog.appendChild(li);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function nickColor(name) {
  const palette = ["#e63946", "#2a9d8f", "#457b9d", "#e9c46a", "#9d4edd", "#f4a261"];
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return palette[h % palette.length];
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]
  );
}
