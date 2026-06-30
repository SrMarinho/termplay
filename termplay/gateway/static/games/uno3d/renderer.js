import * as THREE from "three";
import { EffectComposer } from "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass }     from "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/postprocessing/UnrealBloomPass.js";
import { makeCardTexture, makeCardBack, makeFeltTexture } from "./card-texture.js";

// ── persistent scene state ────────────────────────────────────────────────────
let _scene, _camera, _renderer, _composer, _raf, _canvas, _raycaster;
let _actions = {};
let _handCards  = [];
let _drawMesh   = null;
let _prevState  = null;
let _lastTime   = 0;
let _anims      = [];    // [{fn(dt)->bool}] — false = remove

// ── hand layout constants (shared by static + anim) ──────────────────────────
const ARC_X    = (n) => Math.min(n * 0.55, 6.0);
const ARC_D    = 0.4;   // Z depth at tips
const ARC_LIFT = 0.32;  // Y lift at tips
const FAN      = 0.10;  // rad rotation per tip
// Camera (0,17,10) → hand center (0,0.65,3.2): perpendicular = arcsin(Δy/d)
// Δy=16.35, Δz=6.8, d≈17.7 → arcsin(0.924) ≈ 1.17 rad
const TILT     = 1.17;
const BASE_Y   = 0.65;
const PLAY_Y   = 0.82;
const HAND_Z   = 3.2;   // base Z for hand (closer to camera)

function _handPos(i, n, isPlayable) {
  const t = n > 1 ? (i / (n - 1)) * 2 - 1 : 0;
  return {
    x:   t * (ARC_X(n) / 2),
    y:   (isPlayable ? PLAY_Y : BASE_Y) + Math.abs(t) * ARC_LIFT,
    z:   HAND_Z + Math.abs(t) * ARC_D,
    rx:  -TILT,
    rz:  -t * FAN,
    t,
  };
}

// ── easing ────────────────────────────────────────────────────────────────────
function _easeOut(p)  { return 1 - Math.pow(1 - p, 3); }
function _easeInOut(p){ return p < .5 ? 4*p*p*p : 1 - Math.pow(-2*p+2,3)/2; }
function _easeBack(p) { const c=1.70158; return (c+1)*p*p*p - c*p*p; }

// ── animation: fly card A→B with parabolic arc ────────────────────────────────
function _flyCard({ face, fromPos, fromRot, toPos, toRot, dur = 0.4,
                    isBack = false, arcH = 1.2, delay = 0 }) {
  const m = isBack ? _backBox() : _box(face ?? "W:", {});
  m.userData.dyn  = false;  // survives render() rebuild
  m.userData.anim = true;
  _scene.add(m);

  const fp = new THREE.Vector3(...fromPos);
  const tp = new THREE.Vector3(...toPos);
  const fr = new THREE.Euler(...fromRot, "ZYX");
  const tr = new THREE.Euler(...toRot,   "ZYX");

  let elapsed = -delay;
  _anims.push((dt) => {
    elapsed += dt;
    if (elapsed < 0) { m.visible = false; return true; }
    m.visible = true;
    const p = _easeInOut(Math.min(elapsed / dur, 1));
    m.position.lerpVectors(fp, tp, p);
    m.position.y += Math.sin(p * Math.PI) * arcH;
    m.rotation.x  = fr.x + (tr.x - fr.x) * p;
    m.rotation.y  = fr.y + (tr.y - fr.y) * p;
    m.rotation.z  = fr.z + (tr.z - fr.z) * p;
    if (elapsed >= dur) { _scene.remove(m); m.geometry?.dispose(); return false; }
    return true;
  });
}

// ── animation: card flips (face-down → face-up) ───────────────────────────────
function _flipCard({ face, fromPos, fromRot, toPos, toRot, dur = 0.42, delay = 0 }) {
  // First half: back-face flying, second half: show front face
  const mBack  = _backBox();
  const mFront = _box(face ?? "W:", {});
  mBack.userData.dyn = mFront.userData.dyn = false;
  mBack.userData.anim = mFront.userData.anim = true;
  mFront.visible = false;
  _scene.add(mBack); _scene.add(mFront);

  const fp = new THREE.Vector3(...fromPos);
  const tp = new THREE.Vector3(...toPos);
  const fr = new THREE.Euler(...fromRot, "ZYX");
  const tr = new THREE.Euler(...toRot,   "ZYX");

  let elapsed = -delay;
  _anims.push((dt) => {
    elapsed += dt;
    if (elapsed < 0) return true;
    const p   = _easeInOut(Math.min(elapsed / dur, 1));
    const pos = new THREE.Vector3().lerpVectors(fp, tp, p);
    pos.y    += Math.sin(p * Math.PI) * 1.0;
    const rx  = fr.x + (tr.x - fr.x) * p;
    const rz  = fr.z + (tr.z - fr.z) * p;
    const ry  = p * Math.PI * 2;           // full spin around Y during flight

    const setM = (m) => { m.position.copy(pos); m.rotation.set(rx, ry, rz, "ZYX"); };
    if (p < 0.5) { mBack.visible = true; mFront.visible = false; setM(mBack); }
    else         { mBack.visible = false; mFront.visible = true;  setM(mFront); }

    if (elapsed >= dur) {
      _scene.remove(mBack);  mBack.geometry?.dispose();
      _scene.remove(mFront); mFront.geometry?.dispose();
      return false;
    }
    return true;
  });
}

// ── diff prev→next state and spawn animations ─────────────────────────────────
function _diffAndAnimate(prev, next) {
  if (!prev || !next?.hand) return;

  const topChanged  = next.top !== prev.top;
  const handShrank  = next.hand.length < prev.hand.length;
  const handGrew    = next.hand.length > prev.hand.length;
  const prevHand    = prev.hand ?? [];
  const deckPos     = [-0.85, 0.04, 0.2];
  const deckRot     = [-Math.PI / 2, 0, 0];
  const discardPos  = [0.85, 0.04, 0.2];
  const discardRot  = [-Math.PI / 2, 0, 0.2];

  // ── card played: hand shrinks + top changed ──────────────────────────────
  if (handShrank && topChanged && next.top) {
    const face = next.top;
    // Find the played card index in previous hand (first match)
    const idx = prevHand.indexOf(face);
    const n   = prevHand.length;
    const pos = _handPos(idx >= 0 ? idx : Math.floor(n / 2), n, true);
    _flyCard({
      face,
      fromPos: [pos.x, pos.y, pos.z],
      fromRot: [pos.rx, 0, pos.rz],
      toPos:   discardPos,
      toRot:   discardRot,
      dur:     0.42,
      arcH:    1.4,
    });
  }

  // ── cards drawn: my hand grew ─────────────────────────────────────────────
  if (handGrew) {
    const added   = next.hand.length - prevHand.length;
    const isDeal  = prevHand.length === 0 && next.hand.length > 3;

    for (let k = 0; k < added; k++) {
      const targetIdx = prevHand.length + k;
      const face      = next.hand[targetIdx] ?? next.hand[next.hand.length - 1 - k];
      const pos       = _handPos(targetIdx, next.hand.length, false);
      _flipCard({
        face,
        fromPos: deckPos,
        fromRot: deckRot,
        toPos:   [pos.x, pos.y, pos.z],
        toRot:   [pos.rx, 0, pos.rz],
        dur:     0.38,
        delay:   isDeal ? k * 0.08 : 0,
      });
    }
  }

  // ── opponent drew or played a card ───────────────────────────────────────
  const players = next.players ?? [];
  const opps = players
    .map((p, i) => ({ idx: i, count: p[1] }))
    .filter(o => o.idx !== next.you);
  const spread = Math.min((opps.length - 1) * 1.8, 7);

  opps.forEach((opp, j) => {
    const x = opps.length > 1
      ? -spread / 2 + j * (spread / Math.max(opps.length - 1, 1))
      : 0;
    const oppPos  = [x, 0.06, -2.0];
    const oppRot  = [-Math.PI / 2, 0, 0];
    const prevCount = prev.players?.[opp.idx]?.[1] ?? 0;
    const gained    = opp.count - prevCount;
    const lost      = prevCount - opp.count;

    if (gained > 0) {
      for (let k = 0; k < Math.min(gained, 3); k++) {
        _flyCard({ face: "W:", fromPos: deckPos, fromRot: deckRot,
          toPos: oppPos, toRot: oppRot, dur: 0.45, arcH: 0.9, isBack: true, delay: k * 0.06 });
      }
    }

    if (lost > 0 && topChanged && next.top) {
      _flyCard({ face: next.top, fromPos: oppPos, fromRot: oppRot,
        toPos: discardPos, toRot: discardRot, dur: 0.48, arcH: 1.3 });
    }
  });
}

// ── public API ────────────────────────────────────────────────────────────────

export function init(canvas, actions) {
  _canvas  = canvas;
  _actions = actions;
  _anims   = [];
  _prevState = null;

  _scene = new THREE.Scene();
  _scene.background = new THREE.Color(0x0a140a);
  _scene.fog = new THREE.Fog(0x0a140a, 18, 40);

  _camera = new THREE.PerspectiveCamera(22, canvas.clientWidth / canvas.clientHeight, 0.1, 200);
  _camera.position.set(0, 17, 10);
  _camera.lookAt(0, 0, 0);

  _renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  _renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  _renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
  _renderer.shadowMap.enabled = true;
  _renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  _renderer.toneMapping = THREE.ACESFilmicToneMapping;
  _renderer.toneMappingExposure = 1.15;

  _composer = new EffectComposer(_renderer);
  _composer.addPass(new RenderPass(_scene, _camera));
  const bloom = new UnrealBloomPass(
    new THREE.Vector2(canvas.clientWidth, canvas.clientHeight),
    0.22,  // strength
    0.5,   // radius
    0.45   // threshold
  );
  _composer.addPass(bloom);

  _scene.add(new THREE.AmbientLight(0x335533, 0.25));

  const spot = new THREE.SpotLight(0xfff2d4, 60, 30, Math.PI / 5, 0.45, 1.2);
  spot.position.set(0, 11, 1);
  spot.target.position.set(0, 0, 0.5);
  spot.castShadow = true;
  spot.shadow.mapSize.set(2048, 2048);
  spot.shadow.camera.near = 1; spot.shadow.camera.far = 30;
  spot.shadow.bias = -0.0005;
  _scene.add(spot); _scene.add(spot.target);

  const fill = new THREE.DirectionalLight(0x4466aa, 0.15);
  fill.position.set(0, 4, 8); _scene.add(fill);

  const felt = new THREE.Mesh(
    new THREE.CircleGeometry(9, 64),
    new THREE.MeshStandardMaterial({ map: makeFeltTexture(), roughness: 0.95 })
  );
  felt.rotation.x = -Math.PI / 2; felt.receiveShadow = true; _scene.add(felt);

  const rim = new THREE.Mesh(
    new THREE.RingGeometry(9, 9.6, 64),
    new THREE.MeshStandardMaterial({ color: 0x05210f, roughness: 1 })
  );
  rim.rotation.x = -Math.PI / 2; rim.position.y = 0.001; _scene.add(rim);

  _raycaster = new THREE.Raycaster();
  canvas.addEventListener("click",     _onClick);
  canvas.addEventListener("mousemove", _onHover);

  new ResizeObserver(() => {
    _camera.aspect = canvas.clientWidth / canvas.clientHeight;
    _camera.updateProjectionMatrix();
    _renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    _composer?.setSize(canvas.clientWidth, canvas.clientHeight);
  }).observe(canvas);

  _lastTime = performance.now();
  _raf = requestAnimationFrame(_loop);
}

export function reset() {
  if (_canvas) _canvas.classList.add("hidden");  // hide before WebGL dispose to avoid white flash
  if (_raf) { cancelAnimationFrame(_raf); _raf = null; }
  _canvas?.removeEventListener("click",     _onClick);
  _canvas?.removeEventListener("mousemove", _onHover);
  _handCards = []; _drawMesh = null; _anims = []; _prevState = null;
  _composer?.dispose?.(); _composer = null;
  _renderer?.dispose(); _renderer = null; _scene = null; _canvas = null;
}

export function render(state) {
  if (!_scene) return;

  // Diff before rebuild
  _diffAndAnimate(_prevState, state);
  _prevState = state;

  // Clear static dynamic objects
  const rm = [];
  _scene.traverse(o => { if (o.userData.dyn) rm.push(o); });
  rm.forEach(o => { _scene.remove(o); o.geometry?.dispose(); });
  _handCards = []; _drawMesh = null;

  _buildDiscard(state);
  _buildDeck();
  _buildOpponents(state);
  _buildHand(state);
  _buildDirectionLabel(state);
}

// ── static scene builders ─────────────────────────────────────────────────────

function _buildDiscard(state) {
  if (!state.top) return;
  const m = _box(state.top);
  m.rotation.x = -Math.PI / 2; m.rotation.z = 0.2;
  m.position.set(0.85, 0.02, 0.2); _scene.add(m);
}

function _buildDeck() {
  const STACK = 14;
  for (let k = 0; k < STACK; k++) {
    const m = _backBox();
    m.rotation.x = -Math.PI / 2;
    m.position.set(-0.85, 0.02 + k * 0.012, 0.2);
    if (k === STACK - 1) { m.userData.isDeck = true; _drawMesh = m; }
    _scene.add(m);
  }
}

function _buildOpponents(state) {
  const players = state.players || [];
  const opps = players
    .map((p, i) => ({ name: p[0], cards: p[1], idx: i }))
    .filter(p => p.idx !== state.you);
  const spread = Math.min((opps.length - 1) * 1.8, 7);
  opps.forEach((opp, j) => {
    const x = opps.length > 1
      ? -spread / 2 + j * (spread / Math.max(opps.length - 1, 1))
      : 0;
    const n      = Math.min(opp.cards, 12);
    const active = opp.idx === state.current;
    for (let k = 0; k < n; k++) {
      const m = _backBox();
      m.rotation.x = -Math.PI / 2;
      m.position.set(x + k * 0.07 - (n * 0.07) / 2, 0.02 + k * 0.003, -2.0);
      _scene.add(m);
    }
    _scene.add(_sprite(opp.name + (active ? " ◀" : ""), x, 0.45, -2.8, active ? "#ffe066" : "#ccc"));
  });
}

function _buildHand(state) {
  const hand    = state.hand || [];
  const playable = new Set(state.playable || []);
  const n       = hand.length;
  if (!n) return;

  hand.forEach((face, i) => {
    const isPlayable = state.your_turn && !state.need_color && playable.has(i);
    const isFaded    = state.your_turn && !state.need_color && !isPlayable;
    const pos        = _handPos(i, n, isPlayable);
    const m          = _box(face, { playable: isPlayable, faded: isFaded });
    m.rotation.order = "ZYX";
    m.rotation.x     = pos.rx;
    m.rotation.z     = pos.rz;
    m.position.set(pos.x, pos.y, pos.z);
    m.renderOrder         = i;
    m.userData.handIdx    = i;
    m.userData.isPlayable = isPlayable;
    m.userData.baseY      = pos.y;
    m.userData.targetY    = pos.y;
    _handCards.push(m);
    _scene.add(m);
  });
}

function _buildDirectionLabel(state) {
  const dir = state.direction === 1 ? "→ horário" : "← anti-horário";
  _scene.add(_sprite(dir, 0, 0.15, 0.2, "#aaffaa", 0.8));
}

// ── card factories ────────────────────────────────────────────────────────────

function _box(face, opts = {}) {
  const geo  = new THREE.BoxGeometry(0.66, 0.96, 0.018);
  const edge = new THREE.MeshStandardMaterial({ color: 0x1a1510, roughness: 0.7 });
  const mats = [edge, edge, edge, edge,
    new THREE.MeshStandardMaterial({ map: makeCardTexture(face, opts), roughness: 0.55, metalness: 0.05, transparent: true, alphaTest: 0.5 }),
    new THREE.MeshStandardMaterial({ map: makeCardBack(), roughness: 0.55, transparent: true, alphaTest: 0.5 }),
  ];
  const m = new THREE.Mesh(geo, mats);
  m.castShadow = true; m.userData.dyn = true;
  return m;
}

function _backBox() {
  const geo = new THREE.BoxGeometry(0.66, 0.96, 0.018);
  const m   = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: makeCardBack(), roughness: 0.55, transparent: true, alphaTest: 0.5 }));
  m.castShadow = true; m.userData.dyn = true;
  return m;
}

// ── sprite label ──────────────────────────────────────────────────────────────

function _sprite(text, x, y, z, color = "#fff", scale = 1) {
  const cv = document.createElement("canvas");
  cv.width = 256; cv.height = 64;
  const c  = cv.getContext("2d");
  c.fillStyle = color; c.font = "bold 28px sans-serif";
  c.textAlign = "center"; c.textBaseline = "middle";
  c.fillText(text, 128, 32);
  const sp = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), transparent: true })
  );
  sp.scale.set(2.2 * scale, 0.55 * scale, 1);
  sp.position.set(x, y, z); sp.userData.dyn = true;
  return sp;
}

// ── input ─────────────────────────────────────────────────────────────────────

function _ndc(e) {
  const r = _canvas.getBoundingClientRect();
  return new THREE.Vector2(
    ((e.clientX - r.left) / r.width)  * 2 - 1,
    -((e.clientY - r.top)  / r.height) * 2 + 1
  );
}

function _onClick(e) {
  if (!_scene || !_camera) return;
  _raycaster.setFromCamera(_ndc(e), _camera);
  const hits = _raycaster.intersectObjects([..._handCards, _drawMesh].filter(Boolean), false);
  if (!hits.length) return;
  const o = hits[0].object;
  if (o.userData.isDeck)      { _actions.draw?.(); return; }
  if (o.userData.isPlayable)  { _actions.play?.(o.userData.handIdx); }
}

function _onHover(e) {
  if (!_scene || !_camera) return;
  _raycaster.setFromCamera(_ndc(e), _camera);
  const hits = _raycaster.intersectObjects([..._handCards, _drawMesh].filter(Boolean), false);
  _handCards.forEach(m => { m.userData.targetY = m.userData.baseY; });
  if (hits.length) {
    const o = hits[0].object;
    if (o.userData.handIdx !== undefined) o.userData.targetY = o.userData.baseY + 0.24;
    else if (o.userData.isDeck) o.position.y = (o.userData.baseY ?? 0.032) + 0.15;
    _canvas.style.cursor = (o.userData.isPlayable || o.userData.isDeck) ? "pointer" : "default";
  } else {
    _canvas.style.cursor = "default";
  }
}

// ── render loop ───────────────────────────────────────────────────────────────

function _loop() {
  _raf = requestAnimationFrame(_loop);
  const now = performance.now();
  const dt  = Math.min((now - _lastTime) / 1000, 0.1);
  _lastTime = now;

  // Tick animations
  for (let i = _anims.length - 1; i >= 0; i--) {
    if (!_anims[i](dt)) _anims.splice(i, 1);
  }

  // Smooth hover lerp for hand cards
  const LERP = 0.18;
  for (const m of _handCards) {
    if (m.userData.targetY !== undefined) {
      m.position.y += (m.userData.targetY - m.position.y) * LERP;
    }
  }

  _composer?.render();
}
