// core/registry.js — open/closed registry of game views, keyed by state tag.
//
// A "view" is any object implementing: init(actions), reset(), render(state),
// gameOver(). Each game self-registers on import; app.js routes incoming state
// snapshots to the matching view by their `v` tag (e.g. "uno.state").

const _views = new Map();

export function registerView(tag, view) {
  _views.set(tag, view);
}

export function getView(tag) {
  return _views.get(tag) || null;
}

export function allViews() {
  return [..._views.values()];
}
