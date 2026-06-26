// lobby.js — room list + lobby (players, chat, host controls). Pure view.
let handlers = {
  onJoin: () => {}, onChat: () => {}, onLeave: () => {},
  onStart: () => {}, onAddBot: () => {},
};
let role = "guest"; // "host" | "guest"
let myName = "";

const roomList = document.getElementById("room-list");
const noRooms = document.getElementById("no-rooms");
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
  for (const room of rooms) {
    const li = document.createElement("li");
    li.className = "room";
    const joinable = room.status === "waiting" && room.players < room.max_players;
    li.innerHTML =
      `<span class="room-host">${esc(room.host)}</span>` +
      `<span class="room-game">${esc(room.game)}</span>` +
      `<span class="room-count">${room.players}/${room.max_players}</span>` +
      `<span class="room-status ${room.status}">${esc(room.status)}</span>`;
    const btn = document.createElement("button");
    btn.textContent = joinable ? "Join" : "—";
    btn.disabled = !joinable;
    btn.addEventListener("click", () => handlers.onJoin(room));
    li.appendChild(btn);
    roomList.appendChild(li);
  }
}

export function renderState(state) {
  lobbyCode.textContent = state.code ? `#${state.code}` : "";
  lobbyPlayers.replaceChildren();
  for (const name of state.players || []) {
    const li = document.createElement("li");
    li.textContent = name;
    if ((state.bots || []).includes(name)) li.classList.add("bot");
    if (name === state.host) li.classList.add("host");
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
