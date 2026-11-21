import * as REAL from 'three';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// A renderer stand-in: jsdom has no WebGL. `failNext` makes the next construction throw.
const renderers: Array<{ render: ReturnType<typeof vi.fn>; dispose: ReturnType<typeof vi.fn>; forceContextLoss: ReturnType<typeof vi.fn>; domElement: HTMLCanvasElement }> = [];
let failNext = false;
vi.mock('three', async (importOriginal) => {
  const actual = await importOriginal<typeof import('three')>();
  class FakeRenderer {
    domElement = document.createElement('canvas');
    outputColorSpace = '';
    render = vi.fn();
    dispose = vi.fn();
    forceContextLoss = vi.fn();
    setPixelRatio() {}
    setSize() {}
    setClearColor() {}
    constructor() {
      if (failNext) {
        failNext = false;
        throw new Error('no WebGL');
      }
      renderers.push(this);
    }
  }
  return { ...actual, WebGLRenderer: FakeRenderer };
});

// Frames as the pipeline writes them: positions quantized to normalized int16 under a node scale.
function quantizedScene(length: number) {
  const scene = new REAL.Group();
  const node = new REAL.Group();
  node.scale.setScalar(length / 2);
  const g = new REAL.BufferGeometry();
  const q = new Int16Array([0, 0, 0, 32767, 0, 0, 0, 32767, 0, 0, 0, 32767]);
  g.setAttribute('position', new REAL.BufferAttribute(q, 3, true));
  g.setIndex([0, 1, 2, 0, 2, 3]);
  node.add(new REAL.Mesh(g));
  scene.add(node);
  return scene;
}
vi.mock('three/examples/jsm/loaders/GLTFLoader.js', () => ({
  GLTFLoader: class {
    setMeshoptDecoder() {}
    load(url: string, onLoad: (g: unknown) => void, _p: unknown, onError: (e: unknown) => void) {
      if (url.includes('missing')) return onError(new Error('404'));
      if (url.includes('empty')) return onLoad({ scene: new REAL.Group() });
      const i = Number(/\.(\d+)\.glb$/.exec(url)?.[1] ?? 0);
      onLoad({ scene: quantizedScene(100 + i * 100) });
    }
  },
}));
vi.mock('three/examples/jsm/libs/meshopt_decoder.module.js', () => ({ MeshoptDecoder: {} }));

import { createStage, mergePositions, worldPositions } from './hero-sweep-stage';

let intersect: (visible: boolean) => void = () => {};
let frames: Array<(t: number) => void> = [];
let now = 0;
const step = (ms: number) => {
  now += ms;
  const due = frames;
  frames = [];
  for (const f of due) f(now);
};

beforeEach(() => {
  renderers.length = 0;
  frames = [];
  now = 0;
  vi.stubGlobal(
    'IntersectionObserver',
    class {
      constructor(cb: (e: Array<{ isIntersecting: boolean }>) => void) {
        intersect = (v) => cb([{ isIntersecting: v }]);
      }
      observe() {}
      disconnect() {}
    },
  );
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} });
  vi.stubGlobal('requestAnimationFrame', (f: (t: number) => void) => (frames.push(f), frames.length));
  vi.stubGlobal('cancelAnimationFrame', () => {});
  vi.spyOn(performance, 'now').mockImplementation(() => now);
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const host = () => {
  const el = document.createElement('div');
  Object.defineProperty(el, 'clientWidth', { value: 800 });
  Object.defineProperty(el, 'clientHeight', { value: 400 });
  document.body.appendChild(el);
  return el;
};
const urls = [0, 1, 2, 3].map((i) => `/models/arm.reach.${i}.glb`);
const make = async (over: Partial<Parameters<typeof createStage>[0]> = {}) => {
  const seen: number[] = [];
  const live: boolean[] = [];
  const el = host();
  const stage = await createStage({
    host: el,
    frameUrls: urls,
    rest: 1,
    maxDpr: 1,
    reducedMotion: false,
    onFrame: (i) => seen.push(i),
    onAvailability: (v) => live.push(v),
    contextTaken: () => false,
    ...over,
  });
  return { stage, el, seen, live };
};

describe('decoding the pipeline meshes', () => {
  it('reads quantized positions at their real size instead of clamping them into a unit cube', () => {
    const scene = quantizedScene(480);
    scene.updateMatrixWorld(true);
    const mesh = scene.children[0].children[0] as REAL.Mesh;
    const g = worldPositions(mesh);
    g.computeBoundingBox();
    const size = g.boundingBox!.getSize(new REAL.Vector3());
    expect(size.x).toBeCloseTo(240, 0);
    expect(g.getAttribute('position').count).toBe(6);
  });

  it('concatenates parts', () => {
    const a = new REAL.BufferGeometry();
    a.setAttribute('position', new REAL.BufferAttribute(new Float32Array(9), 3));
    const b = new REAL.BufferGeometry();
    b.setAttribute('position', new REAL.BufferAttribute(new Float32Array(18), 3));
    expect(mergePositions([a, b]).getAttribute('position').count).toBe(9);
  });
});

describe('the hero stage', () => {
  it('shows the rest frame, draws when visible and steps through the frames on its own', async () => {
    const { el, seen, live } = await make();
    expect(seen).toEqual([1]);
    intersect(true);
    expect(el.querySelector('canvas')).not.toBeNull();
    expect(live).toEqual([true]);
    step(16);
    step(1700);
    step(16);
    expect(seen.at(-1)).toBe(2);
    expect(renderers[0].render).toHaveBeenCalled();
  });

  it('stops stepping when the visitor drives it, and when paused', async () => {
    const { stage, seen } = await make();
    intersect(true);
    step(16);
    stage.show(3);
    expect(seen.at(-1)).toBe(3);
    step(5000);
    expect(seen.at(-1)).toBe(3);
    stage.setPaused(true);
    step(5000);
    expect(seen.at(-1)).toBe(3);
  });

  it('in reduced motion it does not step on its own', async () => {
    const { seen } = await make({ reducedMotion: true });
    intersect(true);
    step(16);
    step(5000);
    expect(seen).toEqual([1]);
  });

  it('releases its WebGL context when the hero leaves the viewport', async () => {
    const { el } = await make();
    intersect(true);
    intersect(false);
    expect(el.querySelector('canvas')).toBeNull();
    expect(renderers[0].dispose).toHaveBeenCalled();
    expect(renderers[0].forceContextLoss).toHaveBeenCalled();
  });

  it('shows the still while another stage holds the page’s one WebGL context', async () => {
    const { el, live } = await make({ contextTaken: () => true });
    intersect(true);
    expect(el.querySelector('canvas')).toBeNull();
    expect(live).toEqual([false]);
    expect(renderers).toHaveLength(0);
  });

  it('falls back to the still when the renderer cannot be created or its context is lost', async () => {
    failNext = true;
    const a = await make();
    intersect(true);
    expect(a.live).toEqual([false]);
    const b = await make();
    intersect(true);
    b.el.querySelector('canvas')!.dispatchEvent(new Event('webglcontextlost', { cancelable: true }));
    expect(b.live).toEqual([true, false]);
    expect(b.el.querySelector('canvas')).toBeNull();
  });

  it('rejects when a frame cannot be loaded or holds no mesh, so the page keeps its still', async () => {
    await expect(make({ frameUrls: ['/models/arm.missing.0.glb'] })).rejects.toThrow('404');
    await expect(make({ frameUrls: ['/models/arm.empty.0.glb'] })).rejects.toThrow('no mesh');
  });

  it('disposes everything', async () => {
    const { stage, el } = await make();
    intersect(true);
    stage.dispose();
    expect(el.querySelector('canvas')).toBeNull();
  });
});
