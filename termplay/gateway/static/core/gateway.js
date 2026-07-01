// core/gateway.js — transport layer: owns the WebSocket and JSON framing.
// Nothing above this layer touches the raw socket (Dependency Inversion).

export class GatewaySocket {
  /**
   * @param {{ onMessage: (msg: object) => void,
   *           onStatus:  (status: string) => void,
   *           onClose:   () => void }} handlers
   */
  constructor({ onMessage, onStatus, onClose }) {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    this._ws = new WebSocket(`${proto}://${location.host}/ws`);
    this._ws.onopen    = () => onStatus("connected");
    this._ws.onclose   = () => { onStatus("disconnected"); onClose(); };
    this._ws.onerror   = () => onStatus("error");
    this._ws.onmessage = (ev) => onMessage(JSON.parse(ev.data));
  }

  send(obj) {
    if (this._ws.readyState === WebSocket.OPEN) this._ws.send(JSON.stringify(obj));
  }
}
