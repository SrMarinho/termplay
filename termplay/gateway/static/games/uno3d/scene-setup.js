// ── one-time scene/camera/renderer/lighting setup ───────────────────────────────

import * as THREE from "three";
import { EffectComposer } from "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass }     from "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/postprocessing/UnrealBloomPass.js";
import { makeFeltTexture, makeWoodTexture } from "./card-texture.js";

export function createScene(canvas) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0806);
  scene.fog = new THREE.Fog(0x0a0806, 16, 36);

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
  // Warm candle-lit private salon: champagne key light, faint amber bounce.
  scene.add(new THREE.AmbientLight(0x40372a, 0.35));
  scene.add(new THREE.HemisphereLight(0x8a7a5c, 0x0a0806, 0.18));

  const spot = new THREE.SpotLight(0xffe9c4, 60, 30, Math.PI / 5, 0.5, 1.2);
  spot.position.set(0, 11, 1);
  spot.target.position.set(0, 0, 0.5);
  spot.castShadow = true;
  spot.shadow.mapSize.set(2048, 2048);
  spot.shadow.camera.near = 1; spot.shadow.camera.far = 30;
  spot.shadow.bias = -0.0005;
  scene.add(spot); scene.add(spot.target);

  const fill = new THREE.DirectionalLight(0xd4af37, 0.08);
  fill.position.set(0, 4, 8);
  scene.add(fill);
}

function _addTable(scene) {
  const felt = new THREE.Mesh(
    new THREE.CircleGeometry(7.2, 64),
    new THREE.MeshStandardMaterial({ map: makeFeltTexture(), roughness: 0.95 })
  );
  felt.rotation.x = -Math.PI / 2; felt.receiveShadow = true;
  scene.add(felt);

  // Champagne-gold inlay hairline between the felt and the wooden rail.
  const inlay = new THREE.Mesh(
    new THREE.RingGeometry(7.2, 7.28, 96),
    new THREE.MeshStandardMaterial({
      color: 0xd4af37, roughness: 0.35, metalness: 0.85,
      emissive: 0x3a2c08, emissiveIntensity: 0.6,
    })
  );
  inlay.rotation.x = -Math.PI / 2; inlay.position.y = 0.004;
  scene.add(inlay);

  // Walnut rail around the table edge.
  const rail = new THREE.Mesh(
    new THREE.RingGeometry(7.28, 9.6, 96),
    new THREE.MeshStandardMaterial({ map: makeWoodTexture(), roughness: 0.55, metalness: 0.1 })
  );
  rail.rotation.x = -Math.PI / 2; rail.position.y = 0.002;
  rail.receiveShadow = true;
  scene.add(rail);
}
