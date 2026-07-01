// core/screens.js — screen router: which top-level screen is visible.

export class ScreenRouter {
  constructor() {
    this._screens = {
      rooms: document.getElementById("screen-rooms"),
      lobby: document.getElementById("screen-lobby"),
      game:  document.getElementById("screen-game"),
    };
    this._topbar = document.querySelector(".topbar");
  }

  show(name) {
    for (const [key, el] of Object.entries(this._screens)) {
      el.classList.toggle("active", key === name);
    }
    this._topbar?.classList.toggle("hidden", name === "game");
  }
}
