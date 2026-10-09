import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  AdaptiveScaler, BUDGET_FRACTION, FRAME_BUDGET_MS, SCALE_LADDER, createGpuTimer, createRenderBudget, describeBrowser,
  percentile, scaleFromProbe, targetScale,
} from './renderBudget'

const BUDGET = FRAME_BUDGET_MS * BUDGET_FRACTION
const feed = (scaler, ms, now, n = AdaptiveScaler.WINDOW) => {
  let out = null
  for (let i = 0; i < n; i++) out = scaler.push(ms, now) ?? out
  return out
}

describe('percentile', () => {
  it('returns null for no samples and nearest-rank values otherwise', () => {
    expect(percentile([], 0.5)).toBeNull()
    expect(percentile([5, 1, 3, 2, 4], 0.5)).toBe(3)
    expect(percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9)).toBe(9)
    expect(percentile([7], 0.99)).toBe(7)
  })
})

describe('scaleFromProbe', () => {
  it('keeps full resolution when the full-scale frame fits the budget', () => {
    expect(scaleFromProbe(BUDGET - 1, 2, 0.6)).toBe(1)
  })
  it('picks the sharpest ladder scale whose predicted time fits', () => {
    // t(s) = 2 + 20·s²: full = 22 ms, 0.6 → 9.2 ms. 0.7 → 11.8 ms fits 13.3 ms; 0.85 → 16.45 ms does not.
    expect(scaleFromProbe(22, 2 + 20 * 0.36, 0.6)).toBe(0.7)
  })
  it('falls back to the lowest scale when nothing fits, and to 1 for bad input', () => {
    expect(scaleFromProbe(80, 70, 0.6)).toBe(SCALE_LADDER[SCALE_LADDER.length - 1])
    expect(scaleFromProbe(Number.NaN, 1, 0.6)).toBe(1)
  })
})

describe('AdaptiveScaler', () => {
  it('steps down when p90 exceeds the budget, respecting the cooldown', () => {
    const scaler = new AdaptiveScaler(1)
    expect(feed(scaler, BUDGET * 1.5, 0)).toBe(0.85)
    expect(feed(scaler, BUDGET * 1.5, 500)).toBeNull() // cooldown
    expect(feed(scaler, BUDGET * 1.5, 1600)).toBe(0.7)
  })
  it('steps up only after sustained headroom and the up-cooldown', () => {
    const scaler = new AdaptiveScaler(0.7)
    expect(feed(scaler, 1, 0)).toBeNull()
    expect(feed(scaler, 1, 100)).toBeNull()
    expect(feed(scaler, 1, 200)).toBe(0.85)
    expect(feed(scaler, 1, 300, AdaptiveScaler.WINDOW * 3)).toBeNull() // cooldown after the change
    expect(feed(scaler, 1, 4000, AdaptiveScaler.WINDOW * 3)).toBe(1)
  })
  it('resets headroom when a window is neither over budget nor clearly under it, and clamps at the ends', () => {
    const scaler = new AdaptiveScaler(1)
    expect(feed(scaler, 1, 0, AdaptiveScaler.WINDOW * 4)).toBeNull() // already sharpest
    feed(scaler, BUDGET * 0.7, 10)
    expect(scaler.scale).toBe(1)
    const low = new AdaptiveScaler(SCALE_LADDER[SCALE_LADDER.length - 1])
    expect(feed(low, BUDGET * 3, 0)).toBeNull()
    low.reset(1)
    expect(low.scale).toBe(1)
  })

  const feedPaced = (scaler, ms, now, frameMs, n = AdaptiveScaler.WINDOW) => {
    let out = null
    for (let i = 0; i < n; i++) out = scaler.push(ms, now, frameMs) ?? out
    return out
  }
  it('holds the scale while frames keep pace, however busy the GPU looks', () => {
    const scaler = new AdaptiveScaler(1)
    expect(feedPaced(scaler, BUDGET * 1.5, 0, FRAME_BUDGET_MS)).toBeNull()
    expect(feedPaced(scaler, BUDGET * 1.5, 5000, FRAME_BUDGET_MS)).toBeNull()
    expect(scaler.scale).toBe(1)
  })
  it('steps down on late frames, straight to the scale a probe suggested', () => {
    const scaler = new AdaptiveScaler(1)
    expect(feedPaced(scaler, BUDGET * 1.5, 0, FRAME_BUDGET_MS * 2)).toBe(0.85)
    const probed = new AdaptiveScaler(1)
    probed.suggest(0.55)
    expect(feedPaced(probed, BUDGET * 1.5, 0, FRAME_BUDGET_MS * 2)).toBe(0.55)
  })
  it('reads long gaps as pauses between on-demand renders, not as late frames', () => {
    const scaler = new AdaptiveScaler(1)
    expect(feedPaced(scaler, BUDGET * 1.5, 0, AdaptiveScaler.IDLE_GAP_MS + 1)).toBeNull()
    expect(scaler.scale).toBe(1)
  })
})

describe('describeBrowser', () => {
  it('names common engines', () => {
    expect(describeBrowser('Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/152.0.0.0 Safari/537.36')).toBe('Chrome 152')
    expect(describeBrowser('Mozilla/5.0 Chrome/150.0 Safari/537.36 Edg/150.0')).toBe('Edge 150')
    expect(describeBrowser('Mozilla/5.0 (X11; Linux) Gecko/20100101 Firefox/140.0')).toBe('Firefox 140')
    expect(describeBrowser('Mozilla/5.0 (Macintosh) AppleWebKit/605.1.15 Version/18.2 Safari/605.1.15')).toBe('Safari 18')
    expect(describeBrowser('curl/8')).toBe('Unknown')
  })
})

describe('targetScale', () => {
  it('maps modes to render scales', () => {
    expect(targetScale('auto', 0.7)).toBe(0.7)
    expect(targetScale('sharp', 0.7)).toBe(1)
    expect(targetScale('balanced', 1)).toBe(0.75)
    expect(targetScale('battery', 1)).toBe(0.5)
  })
})

class FakeWebGL2 {}
function fakeContext(gpuNs) {
  const ctx = new FakeWebGL2()
  Object.assign(ctx, {
    QUERY_RESULT_AVAILABLE: 4, QUERY_RESULT: 5, RENDERER: 6,
    getExtension: (name) => (name === 'EXT_disjoint_timer_query_webgl2' ? { TIME_ELAPSED_EXT: 1, GPU_DISJOINT_EXT: 2 } : null),
    getParameter: (p) => (p === 2 ? false : p === 6 ? 'Plain GPU' : null),
    createQuery: () => ({}), beginQuery: vi.fn(), endQuery: vi.fn(), deleteQuery: vi.fn(),
    getQueryParameter: (_q, p) => (p === 4 ? true : gpuNs()),
    getContextAttributes: () => ({ antialias: false }),
  })
  return ctx
}
function fakeRenderer(ctx) {
  return {
    getContext: () => ctx,
    info: { autoReset: true, reset: vi.fn(), render: { frame: 0, calls: 0, triangles: 0 } },
    getDrawingBufferSize: (v) => v.set(200, 100),
    getRenderTarget: () => null, setRenderTarget: vi.fn(), render: vi.fn(function () { this.info.render.frame++ }),
  }
}

describe('createGpuTimer', () => {
  beforeEach(() => vi.stubGlobal('WebGL2RenderingContext', FakeWebGL2))
  afterEach(() => vi.unstubAllGlobals())
  it('times queries and reports them by tag', () => {
    const timer = createGpuTimer(fakeContext(() => 4e6))
    expect(timer.available).toBe(true)
    timer.begin(); timer.end(true)
    timer.begin(); timer.end(false)
    timer.begin(); timer.end(true, 'probe')
    expect(timer.poll()).toEqual([{ ms: 4, tag: 'frame' }, { ms: 4, tag: 'probe' }])
    timer.begin(); timer.dispose()
  })
  it('is inert without WebGL2 timer queries', () => {
    const timer = createGpuTimer({ getExtension: () => null })
    expect(timer.available).toBe(false)
    timer.begin(); timer.end(true)
    expect(timer.poll()).toEqual([])
  })
})

describe('createRenderBudget', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal('WebGL2RenderingContext', FakeWebGL2)
    vi.stubGlobal('requestAnimationFrame', (cb) => setTimeout(() => cb(performance.now()), 16))
  })
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks() })

  it('times frames, follows modes and restores the renderer on dispose', () => {
    const renderer = fakeRenderer(fakeContext(() => 5e6))
    const onScale = vi.fn()
    const budget = createRenderBudget(renderer, { onScale })
    expect(renderer.info.autoReset).toBe(false)
    for (let i = 0; i < 3; i++) budget.onFrame(() => renderer.render())
    budget.beginFrame(); budget.endFrame() // tick without a render: ignored
    const stats = budget.stats()
    expect(stats).toMatchObject({ gpu: 'Plain GPU', timerQuery: true, scale: 1, fps: 3, gpuMsP50: 5 })
    budget.setMode('battery')
    expect(onScale).toHaveBeenLastCalledWith(0.5)
    budget.setMode('battery')
    expect(onScale).toHaveBeenCalledTimes(1)
    expect(budget.scale).toBe(0.5)
    budget.dispose()
    expect(renderer.info.autoReset).toBe(true)
  })

  it('probes two scales offscreen when a larger scene appears, and drops to the fitting scale only once frames run late', async () => {
    let clock = 0
    vi.spyOn(performance, 'now').mockImplementation(() => clock)
    const renderer = fakeRenderer(fakeContext(() => 120e6))
    const onScale = vi.fn()
    const budget = createRenderBudget(renderer, { onScale, probeTarget: () => ({ scene: {}, camera: {} }) })
    budget.onFrame(() => { renderer.render(); renderer.info.render.triangles = 50_000 })
    await vi.advanceTimersByTimeAsync(200)
    expect(renderer.render).toHaveBeenCalledTimes(9)
    expect(onScale).not.toHaveBeenCalled() // the probe only arms the step down
    for (let i = 0; i < AdaptiveScaler.WINDOW + 2; i++) {
      clock += FRAME_BUDGET_MS * 2 // every frame a frame late
      budget.onFrame(() => renderer.render())
    }
    expect(onScale).toHaveBeenLastCalledWith(SCALE_LADDER[SCALE_LADDER.length - 1])
    budget.dispose()
  })

  it('keeps full resolution through a heavy scene that the screen still shows on time', async () => {
    let clock = 0
    vi.spyOn(performance, 'now').mockImplementation(() => clock)
    const renderer = fakeRenderer(fakeContext(() => 15e6)) // over 80% of the budget, under one frame
    const onScale = vi.fn()
    const budget = createRenderBudget(renderer, { onScale, probeTarget: () => ({ scene: {}, camera: {} }) })
    budget.onFrame(() => { renderer.render(); renderer.info.render.triangles = 50_000 })
    await vi.advanceTimersByTimeAsync(200)
    for (let i = 0; i < AdaptiveScaler.WINDOW * 3; i++) {
      clock += FRAME_BUDGET_MS
      budget.onFrame(() => renderer.render())
    }
    expect(onScale).not.toHaveBeenCalled()
    expect(budget.scale).toBe(1)
    budget.dispose()
  })
})
