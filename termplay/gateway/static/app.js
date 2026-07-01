// app.js — composition root: wires transport, session, screens and views,
// and routes server messages to the right collaborator.
import * as lobby from "./core/lobby.js";
import * as rulesModal from "./core/rules-modal.js";
import * as helpModal from "./core/help-modal.js";
import * as session from "./core/session.js";
import { GatewaySocket } from "./core/gateway.js";
import { LeaderboardPanel } from "./core/leaderboard.js";
import { NicknameField } from "./core/nickname.js";
import { ScreenRouter } from "./core/screens.js";
import { ViewManager } from "./core/view-manager.js";
import { buildGameActions } from "./core/game-actions.js";
import "./games/games.js"; // side-effect: every game view self-registers

class ConnectionBadge {
  constructor(el) {
    this._el = el;
    this._labels = {
      connected: "LAN · estável",
      disconnected: "LAN · offline",
      error: "LAN · erro",
      connecting: "LAN · conectando",
    };
  }

  set(status) {
    this._el.textContent = this._labels[status] || `LAN · ${status}`;
    this._el.className = `conn ${status}`;
  }
}

class App {
  constructor() {
    this._screens = new ScreenRouter();
    this._views = new ViewManager();
    this._nick = new NicknameField(document.getElementById("nick"));
    this._badge = new ConnectionBadge(document.getElementById("conn"));
    this._hostBtn = document.getElementById("host-btn");
    this._hostHint = document.getElementById("host-hint");

    this._selectedGame = "uno";
    this._pendingServer = null;
    this._reconnectAttempts = 0;

    this._connect();
  }

  _connect() {
    this._gateway = new GatewaySocket({
      onMessage: (msg) => this._route(msg),
      onStatus: (status) => this._onStatus(status),
      onClose: () => {
        this._hostBtn.disabled = false;
        this._hostHint.textContent = "";
        this._scheduleReconnect();
      },
    });
  }

  /** Recreate the socket with backoff while a resumable session exists. */
  _scheduleReconnect() {
    if (!session.load()?.token || this._reconnectAttempts >= 8) return;
    const delay = Math.min(500 * 2 ** this._reconnectAttempts, 8000);
    this._reconnectAttempts += 1;
    setTimeout(() => this._connect(), delay);
  }

  start() {
    lobby.init({
      onJoin:   (room) => this._joinRoom(room),
      onSpectate: (room) => this._spectateRoom(room),
      onChat:   (text) => this._gateway.send({ action: "chat", text }),
      onLeave:  () => { this._gateway.send({ action: "leave" }); this._leaveRoom(); },
      onStart:  () => this._gateway.send({ action: "start_game", rules: rulesModal.getRulesSpec() }),
      onAddBot: () => this._gateway.send({ action: "add_bot" }),
      onKick:   (name) => this._gateway.send({ action: "kick", target: name }),
    });

    const actions = buildGameActions(
      (text) => this._gateway.send({ action: "game_input", text }),
      { backToLobby: () => { this._views.reset(); this._screens.show("lobby"); } }
    );
    this._views.initAll(actions);

    this._hostBtn.addEventListener("click", () => this._hostRoom());
    document.getElementById("host-btn-2")?.addEventListener("click", () => this._hostRoom());
    document.getElementById("uno-quit")?.addEventListener("click", () => {
      actions.quit();
      this._leaveRoom();
    });

    this._initGameGrid();
    new LeaderboardPanel().start();
    rulesModal.init();
    helpModal.init();
    document.getElementById("help-btn")
      ?.addEventListener("click", () => helpModal.open(this._selectedGame));
    document.getElementById("help-btn-game")
      ?.addEventListener("click", () => helpModal.open(this._views.gameKey));
  }

  // ── message routing ─────────────────────────────────────────────────────────

  _route(msg) {
    switch (msg.type) {
      case "room_list":
        lobby.renderRooms(msg.rooms);
        break;
      case "room_created":
        this._screens.show("lobby");
        lobby.setRole("host", msg.you);
        session.save({ code: msg.code, nick: this._nick.value, token: msg.session_token });
        rulesModal.setGame(this._selectedGame);
        break;
      case "room_joined":
        this._screens.show("lobby");
        lobby.setRole("guest", msg.you);
        session.save({
          code: msg.code,
          nick: this._nick.value,
          token: msg.session_token,
          ...(this._pendingServer || {}),
        });
        break;
      case "reconnected":
        this._screens.show(msg.in_game ? "game" : "lobby");
        if (!msg.in_game) lobby.setRole("guest", msg.you);
        session.save({ code: msg.code, token: msg.session_token });
        break;
      case "spectate_joined":
        this._screens.show("lobby");
        lobby.setRole("guest", msg.you);
        session.save({
          code: msg.code,
          nick: this._nick.value,
          token: msg.session_token,
          ...(this._pendingServer || {}),
        });
        break;
      case "room_state":
        lobby.renderState(msg);
        break;
      case "chat":
        lobby.addChat(msg.name, msg.text);
        break;
      case "game_start":
        this._screens.show("game");
        this._views.reset();
        break;
      case "game_render":
        this._views.render(msg.content);
        break;
      case "game_over":
        this._views.gameOver();
        break;
      case "error":
        alert(msg.message || "Server error");
        if (msg.fatal) this._leaveRoom();
        break;
    }
  }

  _onStatus(status) {
    this._badge.set(status);
    if (status === "connected") {
      this._reconnectAttempts = 0;
      this._attemptRejoin();
    }
  }

  // ── room lifecycle ──────────────────────────────────────────────────────────

  _attemptRejoin() {
    const s = session.load();
    if (!s) return;
    if (s.nick) this._nick.value = s.nick;
    if (s.token) {
      this._gateway.send({ action: "reconnect", token: s.token, ip: s.ip, port: s.port });
    } else if (s.code) {
      this._gateway.send({ action: "join_room", code: s.code, name: s.nick || this._nick.value });
    }
  }

  _leaveRoom() {
    session.clear();
    location.reload();
  }

  _hostRoom() {
    if (!this._nick.require()) return;
    this._gateway.send({ action: "create_room", name: this._nick.value, game: this._selectedGame });
    this._hostBtn.disabled = true;
    this._hostHint.textContent = "Creating…";
  }

  _joinRoom(room) {
    if (!this._nick.require()) return;
    this._pendingServer = { ip: room.ip, port: room.port };
    this._gateway.send({ action: "join_room", ip: room.ip, port: room.port, name: this._nick.value });
  }

  _spectateRoom(room) {
    if (!this._nick.require()) return;
    this._pendingServer = { ip: room.ip, port: room.port };
    this._gateway.send({
      action: "spectate", ip: room.ip, port: room.port,
      code: room.code || "", name: this._nick.value,
    });
  }

  _initGameGrid() {
    const tiles = document.querySelectorAll(".game-tile");
    for (const tile of tiles) {
      tile.addEventListener("click", () => {
        tiles.forEach((t) => t.classList.remove("selected"));
        tile.classList.add("selected");
        this._selectedGame = tile.dataset.game || "uno";
      });
    }
  }
}

new App().start();
