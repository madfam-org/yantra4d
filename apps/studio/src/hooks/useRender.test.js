import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useRender } from './useRender'

vi.mock('../services/renderService', () => ({
  renderParts: vi.fn(() => Promise.resolve([{ type: 'main', url: 'blob:mock' }])),
  cancelRender: vi.fn(() => Promise.resolve()),
  estimateRenderTime: vi.fn(() => 10),
}))

const mockManifest = {
  parameters: [{ id: 'size' }],
  estimate_constants: { warning_threshold_seconds: 60 },
}

const mockT = (key) => key
const mockGetCacheKey = (m, p) => JSON.stringify({ mode: m, ...p })

function renderUseRender(overrides = {}) {
  return renderHook(() =>
    useRender({
      mode: 'unit',
      params: { size: 20 },
      manifest: mockManifest,
      t: mockT,
      getCacheKey: mockGetCacheKey,
      project: 'test',
      ...overrides,
    })
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useRender', () => {
  it('returns initial state', () => {
    const { result } = renderUseRender()
    expect(result.current.parts).toEqual([])
    expect(result.current.loading).toBe(false)
    expect(result.current.progress).toBe(0)
  })

  it('handleGenerate calls renderParts and sets parts', async () => {
    const { renderParts } = await import('../services/renderService')
    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate(true)
    })

    expect(renderParts).toHaveBeenCalled()
    expect(result.current.parts).toHaveLength(1)
  })

  it('cache hit returns cached parts without calling renderParts', async () => {
    const { renderParts } = await import('../services/renderService')
    const { result } = renderUseRender()

    // First call populates cache
    await act(async () => {
      await result.current.handleGenerate(true)
    })
    renderParts.mockClear()

    // Second call should hit cache
    await act(async () => {
      await result.current.handleGenerate()
    })
    expect(renderParts).not.toHaveBeenCalled()
  })

  it('estimate above threshold opens confirm dialog', async () => {
    const { estimateRenderTime } = await import('../services/renderService')
    estimateRenderTime.mockReturnValue(120)

    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate()
    })

    expect(result.current.showConfirmDialog).toBe(true)
    expect(result.current.pendingEstimate).toBe(120)
  })

  it('handleCancelRender closes dialog', async () => {
    const { estimateRenderTime } = await import('../services/renderService')
    estimateRenderTime.mockReturnValue(120)

    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate()
    })

    act(() => {
      result.current.handleCancelRender()
    })

    expect(result.current.showConfirmDialog).toBe(false)
  })

  it('handleCancelGenerate aborts and calls cancelRender', async () => {
    const { cancelRender } = await import('../services/renderService')
    const { result } = renderUseRender()

    await act(async () => {
      result.current.handleCancelGenerate()
    })

    expect(cancelRender).toHaveBeenCalled()
  })
})
