// lobby.js — room list (Salão) + lobby (assentos, chat, host controls). Pure view.
import { playerColor } from "./colors.js";
let handlers = {
  onJoin: () => {}, onSpectate: () => {}, onChat: () => {}, onLeave: () => {},
  onStart: () => {}, onAddBot: () => {}, onKick: () => {},
};
let role = "guest"; // "host" | "guest"
let myName = "";

const roomList = document.getElementById("room-list");
const noRooms = document.getElementById("no-rooms");
const roomCount = document.getElementById("room-count");
const lobbyCode = document.getElementById("lobby-code");
const lobbyTitle = document.querySelector(".lobby-title");
const lobbySub = document.querySelector(".lobby-sub");
const lobbyPlayers = document.getElementById("lobby-players");
const playersCount = document.querySelector(".players-panel .players-count");
const chatLog = document.getElementById("chat-log");
const hostControls = document.getElementById("host-controls");
const guestWait = document.getElementById("guest-wait");
const startBtn = document.getElementById("start-btn");
const startHint = document.getElementById("start-hint");

// Pretty game names for the lobby subtitle / room rows.
const GAME_NAMES = { uno: "Uno", blackjack: "Blackjack", hangman: "Forca", velha: "Velha", domino: "Dominó" };
const gameName = (g) => GAME_NAMES[g] || (g ? g[0].toUpperCase() + g.slice(1) : "Jogo");

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

// First letters of a name → up to two uppercase initials for an avatar.
function initials(name) {
  const parts = String(name).trim().split(/\s+/).filter(Boolean);
  const a = parts[0]?.[0] || "?";
  const b = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (a + b).toUpperCase();
}
function avatar(name, extra = "", playerIdx = -1) {
  const style = playerIdx >= 0 ? ` style="--pc:${playerColor(playerIdx)}"` : "";
  return `<span class="avatar ${extra}"${style}>${esc(initials(name))}</span>`;
}

export function renderRooms(rooms) {
  roomList.replaceChildren();
  noRooms.style.display = rooms.length ? "none" : "block";
  roomCount.textContent = rooms.length ? `${rooms.length} salas · atualizar ↻` : "atualizar ↻";
  rooms.forEach((room, i) => {
    const li = document.createElement("li");
    li.className = "room";
    li.style.animationDelay = `${i * 60}ms`;
    const joinable = room.status === "waiting" && room.players < room.max_players;
    const statusBadge = room.status === "playing"
      ? `<span class="badge starting">em jogo</span>`
      : `<span class="badge open">aberta</span>`;
    const btnLabel = room.status === "playing" ? "em jogo" : joinable ? "entrar" : "cheia";

    li.innerHTML =
      `<span class="room-code">${esc(room.code || "—")}</span>` +
      `<span class="room-game">${esc(gameName(room.game))}</span>` +
      `<span class="room-host">${avatar(room.host)}<span>${esc(room.host)}</span></span>` +
      `<span class="room-players">${room.players} / ${room.max_players}</span>` +
      `<span>${statusBadge}</span>` +
      `<span class="ra"></span>`;
    const btn = document.createElement("button");
    btn.className = "btn primary small";
    btn.textContent = btnLabel;
    btn.disabled = !joinable;
    btn.addEventListener("click", () => handlers.onJoin(room));
    li.querySelector(".ra").appendChild(btn);
    const watch = document.createElement("button");
    watch.className = "btn ghost small";
    watch.textContent = "assistir";
    watch.addEventListener("click", () => handlers.onSpectate(room));
    li.querySelector(".ra").appendChild(watch);
    roomList.appendChild(li);
  });
}

export function renderState(state) {
  // Host migration: server made us host after the previous one left.
  if (state.host && state.host === myName && role !== "host") setRole("host", myName);

  lobbyCode.textContent = state.code ? `· ${state.code}` : "";
  if (lobbyTitle) lobbyTitle.textContent = state.host ? `A noite de ${state.host}` : "A noite começa";
  if (lobbySub) {
    const max = state.max_players ? ` · até ${state.max_players} jogadores` : "";
    lobbySub.textContent = `${gameName(state.game)}${max} · LAN privada`;
  }

  const players = state.players || [];
  if (playersCount) {
    playersCount.textContent = `Jogadores · ${players.length}${state.max_players ? ` de ${state.max_players}` : ""}`;
  }

  lobbyPlayers.replaceChildren();
  const bots = new Set(state.bots || []);
  players.forEach((name, playerIdx) => {
    const li = document.createElement("li");
    li.className = "seat";
    const isBot = bots.has(name);
    const isHost = name === state.host;
    const role_ = isBot ? "bot" : isHost ? "anfitrião" : "convidado";
    li.innerHTML =
      avatar(name, isHost ? "avatar-online" : "", playerIdx) +
      `<span class="seat-body">` +
      `<span class="seat-name">${esc(name)}${name === myName ? " · você" : ""}</span>` +
      `<span class="seat-role">${role_}</span></span>` +
      `<span class="chip seat-chip">${isBot ? "bot" : "pronto"}</span>`;
    if (role === "host" && !isHost) {
      const kick = document.createElement("button");
      kick.className = "kick-btn";
      kick.title = "Remover";
      kick.textContent = "✕";
      kick.addEventListener("click", () => handlers.onKick(name));
      li.appendChild(kick);
    }
    lobbyPlayers.appendChild(li);
  });
  // one empty seat hint while the table is not full
  if (state.max_players && players.length < state.max_players) {
    const empty = document.createElement("li");
    empty.className = "seat empty";
    empty.textContent = "cadeira livre";
    lobbyPlayers.appendChild(empty);
  }
  // watchers sit apart from the table
  (state.spectators || []).forEach((name) => {
    const li = document.createElement("li");
    li.className = "seat";
    li.innerHTML =
      avatar(name) +
      `<span class="seat-body">` +
      `<span class="seat-name">${esc(name)}${name === myName ? " · você" : ""}</span>` +
      `<span class="seat-role">espectador</span></span>` +
      `<span class="chip seat-chip">assistindo</span>`;
    lobbyPlayers.appendChild(li);
  });

  if (role === "host") {
    startBtn.disabled = !state.can_start;
    startHint.textContent = state.can_start
      ? ""
      : `Precisa de ${state.min_players} jogadores (${state.player_count} agora)`;
  }
}

const MAX_CHAT = 100;

export function addChat(name, text) {
  const li = document.createElement("li");
  const time = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  li.innerHTML =
    `<div class="chat-msg-head"><span class="chat-name">${esc(name)}</span>` +
    `<span class="chat-time">${time}</span></div>` +
    `<div class="chat-text">${esc(text)}</div>`;
  chatLog.appendChild(li);
  while (chatLog.children.length > MAX_CHAT) {
    chatLog.removeChild(chatLog.firstChild);
  }
  chatLog.scrollTop = chatLog.scrollHeight;
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]
  );
}
