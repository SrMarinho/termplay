// ── one-time scene/camera/renderer/lighting setup ───────────────────────────────

import * as THREE from "three";
import { EffectComposer } from "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass }     from "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/postprocessing/UnrealBloomPass.js";
import { makeFeltTexture } from "./card-texture.js";

export function createScene(canvas) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a140a);
  scene.fog = new THREE.Fog(0x0a140a, 18, 40);

  const camera = new THREE.PerspectiveCamera(22, canvas.clientWidth / canvas.clientHeight, 0.1, 200);
  camera.position.set(0, 11, 6.5);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  composer.addPass(new UnrealBloomPass(
    new THREE.Vector2(canvas.clientWidth, canvas.clientHeight),
    0.22,  // strength
    0.5,   // radius
    0.45   // threshold
  ));

  _addLights(scene);
  _addTable(scene);

  new ResizeObserver(() => {
    camera.aspect = canvas.clientWidth / canvas.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    composer.setSize(canvas.clientWidth, canvas.clientHeight);
  }).observe(canvas);

  return { scene, camera, renderer, composer };
}

function _addLights(scene) {
  scene.add(new THREE.AmbientLight(0x335533, 0.25));

  const spot = new THREE.SpotLight(0xfff2d4, 60, 30, Math.PI / 5, 0.45, 1.2);
  spot.position.set(0, 11, 1);
  spot.target.position.set(0, 0, 0.5);
  spot.castShadow = true;
  spot.shadow.mapSize.set(2048, 2048);
  spot.shadow.camera.near = 1; spot.shadow.camera.far = 30;
  spot.shadow.bias = -0.0005;
  scene.add(spot); scene.add(spot.target);

  const fill = new THREE.DirectionalLight(0x4466aa, 0.15);
  fill.position.set(0, 4, 8);
  scene.add(fill);
}

function _addTable(scene) {
  const felt = new THREE.Mesh(
    new THREE.CircleGeometry(9, 64),
    new THREE.MeshStandardMaterial({ map: makeFeltTexture(), roughness: 0.95 })
  );
  felt.rotation.x = -Math.PI / 2; felt.receiveShadow = true;
  scene.add(felt);

  const rim = new THREE.Mesh(
    new THREE.RingGeometry(9, 9.6, 64),
    new THREE.MeshStandardMaterial({ color: 0x05210f, roughness: 1 })
  );
  rim.rotation.x = -Math.PI / 2; rim.position.y = 0.001;
  scene.add(rim);
}
