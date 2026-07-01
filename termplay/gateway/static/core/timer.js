// core/timer.js — shared rAF deadline-countdown, extracted out of the three
// near-identical implementations each game view used to carry on its own
// (Uno's effects.js, Blackjack's index.js, Truco's index.js).
//
// Callers own all visuals (label text, urgent styling, SVG ring, bar width);
// this module only owns the rAF loop + deadline math.

export function createTurnTimer({ onTick, onExpire } = {}) {
  let raf = null;
  let deadline = 0;

  function tick() {
    const remaining = Math.max(0, deadline - Date.now() / 1000);
    onTick?.(remaining);
    if (remaining > 0) {
      raf = requestAnimationFrame(tick);
    } else {
      raf = null;
      onExpire?.();
    }
  }

  function start(deadlineUnix) {
    stop();
    deadline = deadlineUnix;
    tick();
  }

  function stop() {
    if (raf !== null) { cancelAnimationFrame(raf); raf = null; }
  }

  return { start, stop };
}
