// core/nickname.js — nickname input: persistence + presence validation.

const NICK_KEY = "termplay.nick";
const MAX_LEN = 16;

export class NicknameField {
  constructor(input) {
    this._input = input;
    const saved = localStorage.getItem(NICK_KEY);
    if (saved) this._input.value = saved;
    this._input.addEventListener("input", () =>
      localStorage.setItem(NICK_KEY, this._input.value.trim())
    );
  }

  get value() {
    return this._input.value.trim().slice(0, MAX_LEN);
  }

  set value(nick) {
    this._input.value = nick;
  }

  /** True when a nickname is present; otherwise focuses the field and flags it. */
  require() {
    if (this.value) return true;
    this._input.focus();
    this._input.classList.add("field-error");
    this._input.addEventListener(
      "input",
      () => this._input.classList.remove("field-error"),
      { once: true }
    );
    return false;
  }
}
