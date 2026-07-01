// core/leaderboard.js — fetches /api/leaderboard and renders the hall of fame.

const REFRESH_MS = 30000;

export class LeaderboardPanel {
  constructor() {
    this._block = document.getElementById("leaderboard-block");
    this._list = document.getElementById("leaderboard-list");
  }

  start() {
    if (!this._block) return;
    this._refresh();
    setInterval(() => this._refresh(), REFRESH_MS);
  }

  async _refresh() {
    let rows;
    try {
      const res = await fetch("/api/leaderboard");
      rows = (await res.json()).leaderboard;
    } catch {
      return; // gateway briefly unavailable — keep the last render
    }
    this._render(rows || []);
  }

  _render(rows) {
    this._block.classList.toggle("hidden", rows.length === 0);
    this._list.replaceChildren(
      ...rows.map((row, i) => {
        const li = document.createElement("li");
        li.className = "room lb-row";
        const rank = document.createElement("span");
        rank.className = "room-code";
        rank.textContent = String(i + 1).padStart(2, "0");
        const name = document.createElement("span");
        name.className = "room-game";
        name.textContent = row.player;
        const wins = document.createElement("span");
        wins.className = "room-players";
        wins.textContent = String(row.wins);
        const played = document.createElement("span");
        played.className = "room-players ra";
        played.textContent = String(row.played);
        li.append(rank, name, wins, played);
        return li;
      })
    );
  }
}
