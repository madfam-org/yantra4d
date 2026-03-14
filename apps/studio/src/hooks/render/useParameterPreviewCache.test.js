import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

// Mock dependencies
vi.mock('../../services/engine/renderService', () => ({
  renderParts: vi.fn(),
}))

vi.mock('../../services/cache/renderCache', () => ({
  makeCacheKey: vi.fn(async (project, mode, params) => `key-${mode}-${JSON.stringify(params)}`),
  get: vi.fn(async () => null),
  put: vi.fn(async () => {}),
}))

const mockInferPreviewHint = vi.fn((paramDef) => {
  if (paramDef._hintType) return { type: paramDef._hintType, affected_parts: ['base'] }
  return { type: 'axis_scale', axis: 'x', affected_parts: ['base'] }
})

vi.mock('../../lib/previewHintInference', () => ({
  inferPreviewHint: (...args) => mockInferPreviewHint(...args),
}))

vi.mock('../../lib/idleCallback', () => ({
  requestIdleCallback: vi.fn((cb) => {
    // Execute callback synchronously for deterministic testing
    Promise.resolve().then(() => cb({ didTimeout: false, timeRemaining: () => 50 }))
    return 1
  }),
  cancelIdleCallback: vi.fn(),
}))

import { useParameterPreviewCache } from './useParameterPreviewCache'
import * as idbCache from '../../services/cache/renderCache'
import { renderParts } from '../../services/engine/renderService'
import { requestIdleCallback, cancelIdleCallback } from '../../lib/idleCallback'

const makeManifest = (params = []) => ({
  parameters: params,
  modes: [{ id: 'unit', parts: [{ id: 'base' }] }],
})

const dimensionalParam = (id, min, max) => ({
  id,
  type: 'slider',
  min,
  max,
  label: { en: id.charAt(0).toUpperCase() + id.slice(1) },
})

describe('useParameterPreviewCache', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    globalThis.URL.revokeObjectURL = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('starts with empty variants and idle status', () => {
    const { result } = renderHook(() =>
      useParameterPreviewCache({
        manifest: makeManifest([]),
        mode: 'unit',
        params: { width: 50 },
        parts: [],
        loading: false,
        project: 'test',
      })
    )
    expect(result.current.cachedVariants.size).toBe(0)
    expect(result.current.preRenderStatus).toBe('idle')
  })

  it('does not pre-render when no parts loaded', async () => {
    renderHook(() =>
      useParameterPreviewCache({
        manifest: makeManifest([dimensionalParam('width', 10, 100)]),
        mode: 'unit',
        params: { width: 50 },
        parts: [],
        loading: false,
        project: 'test',
      })
    )

    await act(async () => { await new Promise(r => setTimeout(r, 10)) })
    expect(requestIdleCallback).not.toHaveBeenCalled()
  })

  it('does not pre-render when loading is true', async () => {
    renderHook(() =>
      useParameterPreviewCache({
        manifest: makeManifest([dimensionalParam('width', 10, 100)]),
        mode: 'unit',
        params: { width: 50 },
        parts: [{ type: 'base', url: '/render/base.glb' }],
        loading: true,
        project: 'test',
      })
    )

    await act(async () => { await new Promise(r => setTimeout(r, 10)) })
    expect(requestIdleCallback).not.toHaveBeenCalled()
  })

  it('checks IDB cache after render completes and idle fires', async () => {
    renderHook(() =>
      useParameterPreviewCache({
        manifest: makeManifest([dimensionalParam('width', 10, 100)]),
        mode: 'unit',
        params: { width: 50 },
        parts: [{ type: 'base', url: '/render/base.glb' }],
        loading: false,
        project: 'test',
      })
    )

    expect(requestIdleCallback).toHaveBeenCalledTimes(1)

    await act(async () => { await new Promise(r => setTimeout(r, 10)) })

    // Should have checked IDB for min and max variants
    expect(idbCache.makeCacheKey).toHaveBeenCalled()
    expect(idbCache.get).toHaveBeenCalled()
  })

  it('restores cached variants from IDB', async () => {
    const fakeBlob = new Blob(['test'], { type: 'model/gltf-binary' })
    idbCache.get.mockResolvedValue([{ type: 'base', blob: fakeBlob }])

    const { result } = renderHook(() =>
      useParameterPreviewCache({
        manifest: makeManifest([dimensionalParam('width', 10, 100)]),
        mode: 'unit',
        params: { width: 50 },
        parts: [{ type: 'base', url: '/render/base.glb' }],
        loading: false,
        project: 'test',
      })
    )

    await act(async () => { await new Promise(r => setTimeout(r, 10)) })

    expect(result.current.cachedVariants.size).toBe(1)
    expect(result.current.cachedVariants.has('width')).toBe(true)
    const widthVariants = result.current.cachedVariants.get('width')
    expect(widthVariants.min).toBeDefined()
    expect(widthVariants.max).toBeDefined()
  })

  it('skips bound when current value equals the bound value', async () => {
    renderHook(() =>
      useParameterPreviewCache({
        manifest: makeManifest([dimensionalParam('width', 10, 100)]),
        mode: 'unit',
        params: { width: 10 }, // width === min
        parts: [{ type: 'base', url: '/render/base.glb' }],
        loading: false,
        project: 'test',
      })
    )

    await act(async () => { await new Promise(r => setTimeout(r, 10)) })

    // Should only check max (width: 100) but not min (width: 10 === current)
    const calls = idbCache.makeCacheKey.mock.calls
    // There should be exactly 1 call (for max), not 2
    expect(calls.length).toBe(1)
    // Verify the call was for width: 100 (max)
    expect(calls[0][2].width).toBe(100)
  })

  it('limits pre-rendering to MAX_PRERENDER_PARAMS (3)', async () => {
    const params = { width: 50, height: 25, depth: 30, radius: 5 }
    const manifest = makeManifest([
      dimensionalParam('width', 10, 100),
      dimensionalParam('height', 5, 50),
      dimensionalParam('depth', 10, 60),
      dimensionalParam('radius', 1, 10),
    ])

    renderHook(() =>
      useParameterPreviewCache({
        manifest,
        mode: 'unit',
        params,
        parts: [{ type: 'base', url: '/render/base.glb' }],
        loading: false,
        project: 'test',
      })
    )

    await act(async () => { await new Promise(r => setTimeout(r, 10)) })

    // Should have been called for at most 3 params * 2 bounds = 6 cache keys
    expect(idbCache.makeCacheKey.mock.calls.length).toBeLessThanOrEqual(6)
  })

  it('triggers background renderParts for uncached variants', async () => {
    idbCache.get.mockResolvedValue(null) // cache miss
    renderParts.mockResolvedValue([{ type: 'base', url: '/render/base-min.glb' }])

    renderHook(() =>
      useParameterPreviewCache({
        manifest: makeManifest([dimensionalParam('width', 10, 100)]),
        mode: 'unit',
        params: { width: 50 },
        parts: [{ type: 'base', url: '/render/base.glb' }],
        loading: false,
        project: 'test',
      })
    )

    // Let the idle callback + async operations complete
    await act(async () => { await new Promise(r => setTimeout(r, 50)) })

    expect(renderParts).toHaveBeenCalled()
    expect(idbCache.put).toHaveBeenCalled()
  })

  it('cancels pre-render on cleanup', async () => {
    const { unmount } = renderHook(() =>
      useParameterPreviewCache({
        manifest: makeManifest([dimensionalParam('width', 10, 100)]),
        mode: 'unit',
        params: { width: 50 },
        parts: [{ type: 'base', url: '/render/base.glb' }],
        loading: false,
        project: 'test',
      })
    )

    unmount()

    // cancelIdleCallback should have been called on cleanup
    expect(cancelIdleCallback).toHaveBeenCalled()
  })

  it('filters out non-dimensional params', async () => {
    mockInferPreviewHint.mockImplementation((paramDef) => {
      if (paramDef.id === 'quality') return { type: 'part_highlight', affected_parts: ['base'] }
      return { type: 'axis_scale', axis: 'x', affected_parts: ['base'] }
    })

    renderHook(() =>
      useParameterPreviewCache({
        manifest: makeManifest([
          dimensionalParam('width', 10, 100),
          { id: 'quality', type: 'slider', min: 1, max: 100, label: { en: 'Quality' } },
        ]),
        mode: 'unit',
        params: { width: 50, quality: 50 },
        parts: [{ type: 'base', url: '/render/base.glb' }],
        loading: false,
        project: 'test',
      })
    )

    await act(async () => { await new Promise(r => setTimeout(r, 10)) })

    // Only width should be checked, not quality
    const calls = idbCache.makeCacheKey.mock.calls
    expect(calls.length).toBeGreaterThan(0)
    // All calls should have width changed, none should have quality as the varying param
    calls.forEach(call => {
      // The params object is the 3rd argument — verify none vary quality
      expect(call[2].quality).toBe(50) // quality stays at current value
    })
  })

  it('revokes blob URLs on unmount', async () => {
    const fakeBlob = new Blob(['test'], { type: 'model/gltf-binary' })
    idbCache.get.mockResolvedValue([{ type: 'base', blob: fakeBlob }])

    const { unmount } = renderHook(() =>
      useParameterPreviewCache({
        manifest: makeManifest([dimensionalParam('width', 10, 100)]),
        mode: 'unit',
        params: { width: 50 },
        parts: [{ type: 'base', url: '/render/base.glb' }],
        loading: false,
        project: 'test',
      })
    )

    await act(async () => { await new Promise(r => setTimeout(r, 10)) })

    unmount()

    expect(URL.revokeObjectURL).toHaveBeenCalled()
  })

  it('does nothing when manifest has no parameters', async () => {
    renderHook(() =>
      useParameterPreviewCache({
        manifest: makeManifest([]),
        mode: 'unit',
        params: {},
        parts: [{ type: 'base', url: '/render/base.glb' }],
        loading: false,
        project: 'test',
      })
    )

    await act(async () => { await new Promise(r => setTimeout(r, 10)) })

    expect(idbCache.makeCacheKey).not.toHaveBeenCalled()
  })
})
