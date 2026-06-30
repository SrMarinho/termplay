// core/help-modal.js — "Como Jogar" modal, content keyed by game name.

const GAME_HELP = {
  uno: {
    title: "Como jogar Uno",
    sections: [
      { heading: "Objetivo", body: "Ser o primeiro a descartar todas as cartas da mão." },
      { heading: "Turno", body: "Jogue uma carta que combine em cor ou número com o topo da pilha. Se não tiver, compre uma." },
      { heading: "Cartas especiais", body: "+2 faz o próximo comprar 2 e perder a vez. Pular salta o próximo. Inverter muda o sentido. Wild escolhe a cor. Wild+4 escolhe cor e faz o próximo comprar 4." },
      { heading: "Comandos", body: "Digite 1–N para jogar carta · D para comprar · T para chamar UNO (automático)." },
    ],
  },
  blackjack: {
    title: "Como jogar Blackjack",
    sections: [
      { heading: "Objetivo", body: "Chegar o mais perto de 21 sem ultrapassar. Quem mais se aproximar vence a rodada." },
      { heading: "Valores", body: "Ás vale 1 ou 11. Figuras (J, Q, K) valem 10. Demais valem seu número." },
      { heading: "Turno", body: "Comprar (Hit) adiciona uma carta. Parar (Stand) encerra sua vez. Ultrapassar 21 é estourar — você perde a rodada." },
      { heading: "Pontuação", body: "Vitórias acumulam pontos ao longo da sessão. Blackjack natural (Ás + figura) paga 1.5×." },
    ],
  },
  truco: {
    title: "Como jogar Truco",
    sections: [
      { heading: "Objetivo", body: "Primeiro time a chegar a 12 pontos vence a partida." },
      { heading: "Deck & Vira", body: "40 cartas (sem 8 e 9). Uma carta é virada antes de cada rodada. O rank imediatamente acima dela vira a Manilha — a carta mais forte." },
      { heading: "Força das Manilhas", body: "Zap ♣ > Copas ♥ > Espadilha ♠ > Escopeta ♦. Demais cartas: 3 > 2 > A > K > J > Q > 7 > 6 > 5 > 4." },
      { heading: "Rodada", body: "Cada jogador recebe 3 cartas. São disputadas 3 levadas. Quem vencer 2 das 3 levadas vence a rodada e marca pontos." },
      { heading: "Envite", body: "No seu turno, diga Truco para apostar 3 pts. O adversário pode aceitar (vale 3), correr (você leva 1 pt) ou aumentar para Seis, Nove ou Doze." },
      { heading: "Comandos", body: "1–3 jogar carta · T truco · A aceitar · R aumentar · C correr." },
    ],
  },
  hangman: {
    title: "Como jogar Forca",
    sections: [
      { heading: "Objetivo", body: "Adivinhar a palavra secreta antes de completar o boneco da forca." },
      { heading: "Turno", body: "Digite uma letra. Se estiver na palavra, ela é revelada em todas as posições. Se não estiver, o boneco avança." },
      { heading: "Vitória & Derrota", body: "Acerte a palavra antes de 6 erros para vencer. No 7º erro o boneco é completo e você perde." },
    ],
  },
  velha: {
    title: "Como jogar Velha",
    sections: [
      { heading: "Objetivo", body: "Formar uma sequência de 3 marcas iguais — em linha, coluna ou diagonal." },
      { heading: "Turno", body: "Clique em uma célula vazia. X sempre começa. Os jogadores se alternam." },
      { heading: "Empate", body: "Se o tabuleiro encher sem que ninguém forme linha, a partida termina empatada." },
    ],
  },
};

const _modal = document.getElementById("help-modal");

function _open(game) {
  const help = GAME_HELP[game];
  if (!help) return;
  _modal.querySelector(".modal-title").textContent = help.title;
  const body = _modal.querySelector(".help-body");
  body.replaceChildren();
  for (const { heading, body: text } of help.sections) {
    const section = document.createElement("div");
    section.className = "help-section";
    section.innerHTML =
      `<h4 class="help-heading">${heading}</h4>` +
      `<p class="help-text">${text}</p>`;
    body.appendChild(section);
  }
  _modal.classList.remove("hidden");
  requestAnimationFrame(() => _modal.classList.add("open"));
}

function _close() {
  _modal.classList.remove("open");
  setTimeout(() => _modal.classList.add("hidden"), 200);
}

export function init() {
  _modal.querySelector(".help-close").addEventListener("click", _close);
  _modal.addEventListener("click", (e) => { if (e.target === _modal) _close(); });
}

export function open(game) { _open(game); }
