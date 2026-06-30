import * as THREE from "three";
import { makeCardTexture, makeCardBack } from "./card-texture.js";

let _scene, _camera, _renderer, _raf, _canvas, _raycaster;
let _actions = {};
let _handCards = [];
let _drawMesh  = null;

export function init(canvas, actions) {
  _canvas  = canvas;
  _actions = actions;

  _scene = new THREE.Scene();
  _scene.background = new THREE.Color(0x163316);

  _camera = new THREE.PerspectiveCamera(45, canvas.clientWidth / canvas.clientHeight, 0.1, 100);
  _camera.position.set(0, 7, 6);
  _camera.lookAt(0, 0, 0);

  _renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  _renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  _renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);

  _scene.add(new THREE.AmbientLight(0xffffff, 0.65));
  const sun = new THREE.DirectionalLight(0xfffbee, 0.85);
  sun.position.set(4, 8, 5);
  _scene.add(sun);

  const felt = new THREE.Mesh(
    new THREE.PlaneGeometry(16, 12),
    new THREE.MeshLambertMaterial({ color: 0x1b5e20 })
  );
  felt.rotation.x = -Math.PI / 2;
  _scene.add(felt);

  _raycaster = new THREE.Raycaster();
  canvas.addEventListener("click", _onClick);
  canvas.addEventListener("mousemove", _onHover);

  new ResizeObserver(() => {
    _camera.aspect = canvas.clientWidth / canvas.clientHeight;
    _camera.updateProjectionMatrix();
    _renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
  }).observe(canvas);

  _raf = requestAnimationFrame(_loop);
}

export function reset() {
  if (_raf) { cancelAnimationFrame(_raf); _raf = null; }
  _canvas?.removeEventListener("click", _onClick);
  _canvas?.removeEventListener("mousemove", _onHover);
  _handCards = []; _drawMesh = null;
  _renderer?.dispose(); _renderer = null; _scene = null;
}

export function render(state) {
  if (!_scene) return;
  _handCards = []; _drawMesh = null;

  const rm = [];
  _scene.traverse(o => { if (o.userData.dyn) rm.push(o); });
  rm.forEach(o => { _scene.remove(o); o.geometry?.dispose(); });

  _drawDiscard(state);
  _drawDeck();
  _drawOpponents(state);
  _drawHand(state);
  _drawDirectionArrow(state);
}

// ── card factories ────────────────────────────────────────────────────────────

function _box(face, opts = {}) {
  const geo = new THREE.BoxGeometry(0.65, 0.95, 0.025);
  const mats = [
    new THREE.MeshLambertMaterial({ color: 0x777777 }),
    new THREE.MeshLambertMaterial({ color: 0x777777 }),
    new THREE.MeshLambertMaterial({ color: 0x777777 }),
    new THREE.MeshLambertMaterial({ color: 0x777777 }),
    new THREE.MeshLambertMaterial({ map: makeCardTexture(face, opts) }),
    new THREE.MeshLambertMaterial({ map: makeCardBack() }),
  ];
  const m = new THREE.Mesh(geo, mats);
  m.userData.dyn = true;
  return m;
}

function _backBox() {
  const geo = new THREE.BoxGeometry(0.65, 0.95, 0.025);
  const m = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ map: makeCardBack() }));
  m.userData.dyn = true;
  return m;
}

// ── scene sections ────────────────────────────────────────────────────────────

function _drawDiscard(state) {
  if (!state.top) return;
  const m = _box(state.top);
  m.rotation.x = -Math.PI / 2;
  m.rotation.z = 0.2;
  m.position.set(0.85, 0.02, 0.2);
  _scene.add(m);
}

function _drawDeck() {
  for (let k = 0; k < 3; k++) {
    const m = _backBox();
    m.rotation.x = -Math.PI / 2;
    m.position.set(-0.85, 0.02 + k * 0.006, 0.2);
    if (k === 2) { m.userData.isDeck = true; _drawMesh = m; }
    _scene.add(m);
  }
}

function _drawOpponents(state) {
  const players = state.players || [];
  const opps = players
    .map((p, i) => ({ name: p[0], cards: p[1], idx: i }))
    .filter(p => p.idx !== state.you);

  const spread = Math.min((opps.length - 1) * 1.8, 7);
  opps.forEach((opp, j) => {
    const x = opps.length > 1
      ? -spread / 2 + j * (spread / Math.max(opps.length - 1, 1))
      : 0;
    const n = Math.min(opp.cards, 12);
    const active = opp.idx === state.current;

    for (let k = 0; k < n; k++) {
      const m = _backBox();
      m.rotation.x = -Math.PI / 2;
      m.position.set(x + k * 0.07 - (n * 0.07) / 2, 0.02 + k * 0.003, -3.4);
      if (active) {
        m.material = new THREE.MeshLambertMaterial({ color: 0xffe066, emissive: 0x332200 });
      }
      _scene.add(m);
    }

    _scene.add(_sprite(opp.name + (active ? " ◀" : ""), x, 0.45, -4.0, active ? "#ffe066" : "#ccc"));
  });
}

function _drawHand(state) {
  const hand = state.hand || [];
  const playable = new Set(state.playable || []);
  const n = hand.length;
  if (!n) return;

  const spread = Math.min(n * 0.72, 8.5);
  const TILT = Math.PI / 2 - 0.45;

  hand.forEach((face, i) => {
    const isPlayable = state.your_turn && !state.need_color && playable.has(i);
    const isFaded    = state.your_turn && !state.need_color && !isPlayable;
    const m = _box(face, { playable: isPlayable, faded: isFaded });
    const x = n > 1 ? -spread / 2 + (i / (n - 1)) * spread : 0;
    m.rotation.x = -TILT;
    m.position.set(x, isPlayable ? 0.25 : 0.05, 3.5);
    m.userData.handIdx   = i;
    m.userData.isPlayable = isPlayable;
    _handCards.push(m);
    _scene.add(m);
  });
}

function _drawDirectionArrow(state) {
  const dir = state.direction === 1 ? "→ horário" : "← anti-horário";
  _scene.add(_sprite(dir, 0, 0.15, 0.2, "#aaffaa", 0.8));
}

// ── sprite labels ─────────────────────────────────────────────────────────────

function _sprite(text, x, y, z, color = "#fff", scale = 1) {
  const cv = document.createElement("canvas");
  cv.width = 256; cv.height = 64;
  const c = cv.getContext("2d");
  c.fillStyle = color;
  c.font = "bold 28px sans-serif";
  c.textAlign = "center"; c.textBaseline = "middle";
  c.fillText(text, 128, 32);
  const sp = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), transparent: true })
  );
  sp.scale.set(2.2 * scale, 0.55 * scale, 1);
  sp.position.set(x, y, z);
  sp.userData.dyn = true;
  return sp;
}

// ── input ─────────────────────────────────────────────────────────────────────

function _ndc(e) {
  const r = _canvas.getBoundingClientRect();
  return new THREE.Vector2(
    ((e.clientX - r.left) / r.width) * 2 - 1,
    -((e.clientY - r.top) / r.height) * 2 + 1
  );
}

function _onClick(e) {
  if (!_scene || !_camera) return;
  _raycaster.setFromCamera(_ndc(e), _camera);
  const targets = [..._handCards, _drawMesh].filter(Boolean);
  const hits = _raycaster.intersectObjects(targets, false);
  if (!hits.length) return;
  const o = hits[0].object;
  if (o.userData.isDeck)       { _actions.draw?.(); return; }
  if (o.userData.isPlayable)   { _actions.play?.(o.userData.handIdx); }
}

function _onHover(e) {
  if (!_scene || !_camera) return;
  _raycaster.setFromCamera(_ndc(e), _camera);
  const targets = [..._handCards, _drawMesh].filter(Boolean);
  const hits = _raycaster.intersectObjects(targets, false);

  _handCards.forEach(m => {
    m.position.y = m.userData.isPlayable ? 0.25 : 0.05;
  });

  if (hits.length) {
    const o = hits[0].object;
    o.position.y += 0.18;
    _canvas.style.cursor = (o.userData.isPlayable || o.userData.isDeck) ? "pointer" : "default";
  } else {
    _canvas.style.cursor = "default";
  }
}

function _loop() {
  _raf = requestAnimationFrame(_loop);
  _renderer?.render(_scene, _camera);
}
