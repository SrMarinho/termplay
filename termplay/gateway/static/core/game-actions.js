// core/game-actions.js — semantic game actions → protocol game_input strings.
// Views depend on this vocabulary, never on the wire format (Interface Segregation).

/**
 * @param {(text: string) => void} sendInput
 * @param {{ backToLobby: () => void }} hooks
 */
export function buildGameActions(sendInput, { backToLobby }) {
  return {
    play:         (idx) => sendInput(String(idx + 1)),
    draw:         ()    => sendInput("d"),
    pass:         ()    => sendInput("p"),
    chooseColor:  (c)   => sendInput(c),
    chooseTarget: (i)   => sendInput(String(i + 1)),
    skipSwap:     ()    => sendInput("skip"),
    tap:          ()    => sendInput("tap"),
    hit:          ()    => sendInput("h"),
    stand:        ()    => sendInput("s"),
    quit:         ()    => sendInput("q"),
    send:         (t)   => sendInput(t),
    backToLobby,
  };
}
