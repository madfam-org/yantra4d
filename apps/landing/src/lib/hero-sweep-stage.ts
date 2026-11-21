/**
 * The hero's 3D stage: one cartridge turning slowly while one parameter steps through the values
 * the pipeline rendered. Plain three.js, imported lazily by the hero on the lite/full tiers only,
 * so it lands in the `vendor-three` chunk and nothing here costs the first paint.
 *
 * Time comes from the frame timestamps `requestAnimationFrame` passes, never from a wall clock of
 * its own, so a frame-stepped recorder films it exactly.
 *
 * The page budget allows one WebGL context: the stage releases its context whenever the hero
 * leaves the viewport and builds a new one when it returns. The loop also stops while the tab is
 * hidden.
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';

export interface StageOptions {
  host: HTMLElement;
  frameUrls: string[];
  /** Frame shown first. */
  rest: number;
  /** Device-pixel-ratio ceiling for this tier. */
  maxDpr: number;
  /** No turning and no automatic stepping: the visitor drives it. */
  reducedMotion: boolean;
  /** Called with the frame index whenever the shown frame changes. */
  onFrame: (index: number) => void;
}

export interface Stage {
  /** Show frame `index` now and stop stepping on its own: the visitor has taken over. */
  show(index: number): void;
  dispose(): void;
}

/** Seconds each value is held while the sweep runs on its own. */
const HOLD_SECONDS = 1.6;
/** Turntable speed, radians per second. */
const TURN_RATE = 0.22;
/** Heading at rest, radians about the base: reaching toward the viewer, three-quarter on. */
const REST_ANGLE = -0.75;
/** Seconds a change of frame takes to settle. */
const SETTLE_SECONDS = 0.32;

const MATERIAL_COLOR = 0xcbd5e1;

function loadFrames(urls: string[]): Promise<THREE.BufferGeometry[]> {
  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  return Promise.all(
    urls.map(
      (url) =>
        new Promise<THREE.BufferGeometry>((resolve, reject) => {
          loader.load(
            url,
            (gltf) => {
              const parts: THREE.BufferGeometry[] = [];
              gltf.scene.updateMatrixWorld(true);
              gltf.scene.traverse((child) => {
                const mesh = child as THREE.Mesh;
                if (mesh.isMesh) parts.push(worldPositions(mesh));
              });
              if (parts.length === 0) return reject(new Error(`${url} has no mesh`));
              const merged = parts.length === 1 ? parts[0] : mergePositions(parts);
              // The pipeline exports in the CAD convention, Z up; the scene is Y up.
              merged.rotateX(-Math.PI / 2);
              merged.computeVertexNormals();
              resolve(merged);
            },
            undefined,
            reject,
          );
        }),
    ),
  );
}

/**
 * A mesh's triangles as plain float positions in world space. The pipeline's files are
 * meshopt-compressed with quantized positions (normalized 16-bit integers plus a node scale);
 * transforming the attribute in place would clamp every point into the unit cube, so the values
 * are read out as floats first.
 */
function worldPositions(mesh: THREE.Mesh): THREE.BufferGeometry {
  const source = mesh.geometry.getAttribute('position');
  const index = mesh.geometry.getIndex();
  const count = index ? index.count : source.count;
  const out = new Float32Array(count * 3);
  const v = new THREE.Vector3();
  for (let i = 0; i < count; i++) {
    v.fromBufferAttribute(source, index ? index.getX(i) : i).applyMatrix4(mesh.matrixWorld);
    out[i * 3] = v.x;
    out[i * 3 + 1] = v.y;
    out[i * 3 + 2] = v.z;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(out, 3));
  return geometry;
}

/** The pipeline's meshes carry positions only, so merging is a concatenation. */
function mergePositions(parts: THREE.BufferGeometry[]): THREE.BufferGeometry {
  const total = parts.reduce((n, g) => n + g.getAttribute('position').count, 0);
  const out = new Float32Array(total * 3);
  let offset = 0;
  for (const g of parts) {
    const p = g.getAttribute('position').array as Float32Array;
    out.set(p, offset);
    offset += p.length;
  }
  const merged = new THREE.BufferGeometry();
  merged.setAttribute('position', new THREE.BufferAttribute(out, 3));
  return merged;
}

export async function createStage(options: StageOptions): Promise<Stage> {
  const { host, frameUrls, reducedMotion, onFrame } = options;
  const geometries = await loadFrames(frameUrls);

  // One frame of reference for every frame, scaled by the largest, so a longer reach reads as
  // longer instead of every frame filling the view. The part turns about its own origin, which for
  // the pipeline's kinematic cartridges is the base: an arm sweeps around its shoulder, as it does.
  const bounds = new THREE.Box3();
  let radius = 0;
  for (const g of geometries) {
    g.computeBoundingBox();
    bounds.union(g.boundingBox as THREE.Box3);
    const p = g.getAttribute('position');
    for (let i = 0; i < p.count; i++) radius = Math.max(radius, Math.hypot(p.getX(i), p.getZ(i)));
  }
  const centre = new THREE.Vector3(0, bounds.getCenter(new THREE.Vector3()).y, 0);
  const scale = 2.45 / Math.max(radius, 1e-6);

  let renderer: THREE.WebGLRenderer | null = null;
  let raf = 0;
  let current = Math.min(Math.max(options.rest, 0), geometries.length - 1);
  let previous = current;
  let changedAt = -Infinity;
  let driven = false;
  let start: number | null = null;
  let lastStep = 0;
  let visible = false;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 50);
  // A three-quarter view from above, so the gear's face and teeth both read.
  camera.position.set(0, 2.5, 4.7);
  camera.lookAt(0, -0.15, 0);
  scene.add(new THREE.HemisphereLight(0xe2e8f0, 0x0f172a, 1.1));
  const key = new THREE.DirectionalLight(0xffffff, 1.6);
  key.position.set(3, 5, 4);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x60a5fa, 1.2);
  rim.position.set(-4, 2, -3);
  scene.add(rim);

  const material = new THREE.MeshStandardMaterial({
    color: MATERIAL_COLOR,
    roughness: 0.42,
    metalness: 0.18,
    flatShading: true,
  });
  const rig = new THREE.Group();
  scene.add(rig);
  const part = new THREE.Mesh(geometries[current], material);
  part.scale.setScalar(scale);
  part.position.set(-centre.x * scale, -centre.y * scale, -centre.z * scale);
  rig.add(part);

  const resize = () => {
    if (!renderer) return;
    const { clientWidth: w, clientHeight: h } = host;
    if (w === 0 || h === 0) return;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, options.maxDpr));
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };

  const setFrame = (index: number, at: number) => {
    if (index === current) return;
    previous = current;
    current = index;
    changedAt = at;
    part.geometry = geometries[current];
    onFrame(current);
  };

  const tick = (now: number) => {
    raf = 0;
    if (!renderer || !visible || document.hidden) return;
    if (start === null) {
      start = now;
      lastStep = now;
    }
    const t = (now - start) / 1000;
    // At rest the arm reaches toward the viewer's right, three-quarter on.
    rig.rotation.y = REST_ANGLE + (reducedMotion ? 0 : t * TURN_RATE);
    if (!reducedMotion && !driven && now - lastStep >= HOLD_SECONDS * 1000) {
      lastStep = now;
      setFrame((current + 1) % geometries.length, now);
    }
    // A change settles from a slight lift and scale, never a jump cut.
    const p = Math.min(1, (now - changedAt) / (SETTLE_SECONDS * 1000));
    const ease = 1 - Math.pow(1 - p, 4);
    const grow = current > previous ? 1 : -1;
    const settle = reducedMotion ? 1 : 1 - 0.035 * grow * (1 - ease);
    part.scale.setScalar(scale * settle);
    renderer.render(scene, camera);
    // With reduced motion nothing moves on its own: draw once per change, then rest.
    if (!reducedMotion || p < 1) raf = requestAnimationFrame(tick);
  };

  const run = () => {
    if (!raf && renderer && visible && !document.hidden) raf = requestAnimationFrame(tick);
  };

  const mount = () => {
    if (renderer) return;
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.domElement.setAttribute('aria-hidden', 'true');
    renderer.domElement.className = 'hero-sweep-canvas';
    host.appendChild(renderer.domElement);
    resize();
    run();
  };

  const unmount = () => {
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    if (!renderer) return;
    renderer.domElement.remove();
    renderer.dispose();
    renderer.forceContextLoss();
    renderer = null;
  };

  const observer = new IntersectionObserver(
    (entries) => {
      visible = entries.some((e) => e.isIntersecting);
      if (visible) mount();
      else unmount();
    },
    { rootMargin: '80px 0px' },
  );
  observer.observe(host);
  const sizes = new ResizeObserver(resize);
  sizes.observe(host);
  const onVisibility = () => run();
  document.addEventListener('visibilitychange', onVisibility);
  onFrame(current);

  return {
    show(index: number) {
      driven = true;
      setFrame(Math.min(Math.max(index, 0), geometries.length - 1), performance.now());
      if (!raf && renderer) {
        // Draw the new frame even when nothing else is moving (reduced motion).
        run();
      }
    },
    dispose() {
      observer.disconnect();
      sizes.disconnect();
      document.removeEventListener('visibilitychange', onVisibility);
      unmount();
      material.dispose();
      for (const g of geometries) g.dispose();
    },
  };
}
