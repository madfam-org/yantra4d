import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, act } from '@testing-library/react'

const hooks = { frame: null, before: null, after: null }
const invalidate = vi.fn()
let gl
vi.mock('@react-three/fiber', () => ({
  useThree: (sel) => sel({ gl, scene: { id: 'scene' }, camera: { id: 'camera' }, invalidate }),
  useFrame: (cb) => { hooks.frame = cb },
  addEffect: (cb) => { hooks.before = cb; return () => { hooks.before = null } },
  addAfterEffect: (cb) => { hooks.after = cb; return () => { hooks.after = null } },
}))

import ViewerPerformance, { CompileGate, InvalidateOnCommit, KeepRendering } from './ViewerPerformance'
import { getQualityReadings, getRenderScale, setQualityMode } from '../../lib/viewerQuality'

class FakeWebGL2 {}
function fakeContext(gpuNs) {
  const ctx = new FakeWebGL2()
  Object.assign(ctx, {
    QUERY_RESULT_AVAILABLE: 4, QUERY_RESULT: 5, RENDERER: 6,
    getExtension: (name) => (name === 'EXT_disjoint_timer_query_webgl2' ? { TIME_ELAPSED_EXT: 1, GPU_DISJOINT_EXT: 2 }
      : name === 'WEBGL_debug_renderer_info' ? { UNMASKED_RENDERER_WEBGL: 3 } : null),
    getParameter: (p) => (p === 3 ? 'ANGLE (Intel, Test GPU)' : p === 2 ? false : 'gpu'),
    createQuery: () => ({}), beginQuery: vi.fn(), endQuery: vi.fn(), deleteQuery: vi.fn(),
    getQueryParameter: (_q, p) => (p === 4 ? true : gpuNs()),
    getContextAttributes: () => ({ antialias: true }),
  })
  return ctx
}
function fakeRenderer(ctx) {
  return {
    getContext: () => ctx,
    info: { autoReset: true, reset: vi.fn(), render: { frame: 0, calls: 0, triangles: 0 } },
    compileAsync: vi.fn(() => Promise.resolve()),
    getDrawingBufferSize: (v) => v.set(200, 100),
    getRenderTarget: () => null, setRenderTarget: vi.fn(), render: vi.fn(),
  }
}
function frame(triangles = 50_000) {
  hooks.before()
  gl.info.render.frame += 2
  gl.info.render.calls = 12
  gl.info.render.triangles = triangles
  hooks.after()
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.stubGlobal('WebGL2RenderingContext', FakeWebGL2)
  vi.stubGlobal('requestAnimationFrame', (cb) => setTimeout(() => cb(performance.now()), 16))
  setQualityMode('auto')
})
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.clearAllMocks() })

describe('<ViewerPerformance>', () => {
  it('publishes readings and lowers Auto scale when the probe shows no headroom', async () => {
    gl = fakeRenderer(fakeContext(() => 120e6)) // 30 ms per probe render
    const { unmount } = render(<ViewerPerformance />)
    expect(gl.info.autoReset).toBe(false)
    frame()
    await act(async () => { await vi.advanceTimersByTimeAsync(200) })
    expect(gl.render).toHaveBeenCalledTimes(8) // 4 renders at each of the two probe scales
    expect(getRenderScale()).toBe(0.55)
    for (let i = 0; i < 40; i++) frame()
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    const readings = getQualityReadings()
    expect(readings.gpu).toBe('Intel, Test GPU')
    expect(readings.timerQuery).toBe(true)
    expect(readings.drawCalls).toBe(12)
    expect(readings.gpuMsP90).toBe(120)
    act(() => setQualityMode('sharp'))
    expect(getRenderScale()).toBe(1)
    unmount()
    expect(gl.info.autoReset).toBe(true)
    expect(hooks.before).toBeNull()
  })

  it('keeps full resolution on a GPU with headroom and ignores loop ticks without a render', async () => {
    gl = fakeRenderer(fakeContext(() => 8e6)) // 2 ms per probe render
    render(<ViewerPerformance />)
    frame()
    await act(async () => { await vi.advanceTimersByTimeAsync(200) })
    expect(getRenderScale()).toBe(1)
    hooks.before(); hooks.after() // a tick in which nothing rendered
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(getQualityReadings().scale).toBe(1)
  })
})

describe('demand-rendering helpers', () => {
  it('KeepRendering invalidates every frame only while active', () => {
    gl = fakeRenderer(fakeContext(() => 1))
    const { rerender } = render(<KeepRendering active />)
    hooks.frame()
    expect(invalidate).toHaveBeenCalledTimes(2)
    rerender(<KeepRendering active={false} />)
    invalidate.mockClear()
    hooks.frame()
    expect(invalidate).not.toHaveBeenCalled()
  })

  it('InvalidateOnCommit requests a frame after each commit', () => {
    const { rerender } = render(<InvalidateOnCommit />)
    rerender(<InvalidateOnCommit />)
    expect(invalidate).toHaveBeenCalledTimes(2)
  })

  it('CompileGate reveals content once its programs are compiled', async () => {
    gl = fakeRenderer(fakeContext(() => 1))
    render(<CompileGate signature="a"><span>model</span></CompileGate>)
    expect(gl.compileAsync).toHaveBeenCalledTimes(1)
    expect(invalidate).not.toHaveBeenCalled()
    await act(async () => { await Promise.resolve() })
    expect(invalidate).toHaveBeenCalledTimes(1)
    gl.compileAsync = undefined
    render(<CompileGate signature="b"><span>model</span></CompileGate>)
    expect(invalidate).toHaveBeenCalledTimes(2)
  })
})
