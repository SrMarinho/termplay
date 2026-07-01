// core/view-manager.js — active game view lifecycle: picks the registered view
// for each render payload and swaps views when the game type changes.

import { allViews, getView } from "./registry.js";

export class ViewManager {
  constructor() {
    this._active = null;
    this._gameKey = "uno";
  }

  get gameKey() {
    return this._gameKey;
  }

  initAll(actions) {
    for (const view of allViews()) view.init(actions);
  }

  render(content) {
    let state;
    try { state = JSON.parse(content); } catch { return; }
    if (state.v) this._gameKey = state.v.split(".")[0];
    const view = getView(state.v);
    if (!view) return;
    if (view !== this._active) { this._active?.reset?.(); this._active = view; }
    view.render(state);
  }

  reset() {
    this._active?.reset?.();
    this._active = null;
  }

  gameOver() {
    this._active?.gameOver();
  }
}
