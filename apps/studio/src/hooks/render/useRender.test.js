import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useRender } from './useRender'

vi.mock('../../services/engine/renderService', () => ({
  renderParts: vi.fn(() => Promise.resolve([{ type: 'main', url: 'blob:mock' }])),
  cancelRender: vi.fn(() => Promise.resolve()),
  cancelRenderOnUnload: vi.fn(() => true),
  cancelSupersededRender: vi.fn(() => false),
  estimateRenderTime: vi.fn(() => 10),
}))

vi.mock('../system/useUpgradePrompt', () => ({
  useUpgradePrompt: () => ({ triggerUpgradePrompt: vi.fn() }),
}))

vi.mock('sonner', () => ({
  toast: { info: vi.fn(), success: vi.fn(), error: vi.fn() },
}))

const mockManifest = {
  parameters: [{ id: 'size' }],
  estimate_constants: { warning_threshold_seconds: 60 },
}

// Stands in for LanguageProvider's t. Real locale strings are not loaded here,
// so the interpolation params are appended to the key instead of substituted
// into it — that keeps them assertable without pinning English wording.
const mockT = (key, params) =>
  params ? `${key} ${Object.values(params).join(' ')}` : key
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
    const { renderParts } = await import('../../services/engine/renderService')
    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate(true)
    })

    expect(renderParts).toHaveBeenCalled()
    expect(result.current.parts).toHaveLength(1)
  })

  it('cache hit returns cached parts without calling renderParts', async () => {
    const { renderParts } = await import('../../services/engine/renderService')
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

  // --- Automatic vs user-initiated generation ------------------------------
  // The studio auto-generates on load and on every param change (the debounced
  // effect in useProjectParams). Handing that path the same confirm modal meant
  // a cartridge whose default estimates over threshold — gridfinity's cadquery
  // `bin` is ~2 min — opened a pointer-blocking Radix alertdialog on every
  // single page load, before the visitor had asked for anything at all.

  it('an automatic render over the threshold renders nothing and opens no modal', async () => {
    const { estimateRenderTime, renderParts } = await import('../../services/engine/renderService')
    const { toast } = await import('sonner')
    estimateRenderTime.mockReturnValue(120)

    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate(false, null, { automatic: true })
    })

    expect(result.current.showConfirmDialog).toBe(false)
    expect(renderParts).not.toHaveBeenCalled()
    // The visitor is told, without being blocked.
    expect(toast.info).toHaveBeenCalledTimes(1)
    expect(toast.info.mock.calls[0][0]).toContain('toast.auto_render_skipped')
    // ~2 min, from the 120s estimate.
    expect(toast.info.mock.calls[0][0]).toContain('2')
    // The estimate is still recorded, so a later surface can show it.
    expect(result.current.pendingEstimate).toBe(120)
  })

  it('an automatic render under the threshold renders without a notice', async () => {
    const { estimateRenderTime, renderParts } = await import('../../services/engine/renderService')
    const { toast } = await import('sonner')
    estimateRenderTime.mockReturnValue(10)

    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate(false, null, { automatic: true })
    })

    expect(renderParts).toHaveBeenCalled()
    expect(result.current.parts).toHaveLength(1)
    expect(result.current.showConfirmDialog).toBe(false)
    expect(toast.info).not.toHaveBeenCalled()
  })

  it('a user-initiated render over the threshold still opens the confirm modal', async () => {
    const { estimateRenderTime, renderParts } = await import('../../services/engine/renderService')
    const { toast } = await import('sonner')
    estimateRenderTime.mockReturnValue(120)

    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate()
    })

    expect(result.current.showConfirmDialog).toBe(true)
    expect(result.current.pendingEstimate).toBe(120)
    expect(renderParts).not.toHaveBeenCalled()
    // The modal is the notice here; a toast on top of it would be noise.
    expect(toast.info).not.toHaveBeenCalled()
  })

  it('confirming after an automatic skip renders', async () => {
    // The skip leaves no pendingPayload, so Generate — not the skipped
    // automatic attempt — is what starts the render.
    const { estimateRenderTime, renderParts } = await import('../../services/engine/renderService')
    estimateRenderTime.mockReturnValue(120)

    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate(false, null, { automatic: true })
    })
    expect(renderParts).not.toHaveBeenCalled()

    await act(async () => {
      await result.current.handleGenerate()
    })
    expect(result.current.showConfirmDialog).toBe(true)

    await act(async () => {
      result.current.handleConfirmRender()
    })
    expect(renderParts).toHaveBeenCalled()
  })

  it('estimate above threshold opens confirm dialog', async () => {
    const { estimateRenderTime } = await import('../../services/engine/renderService')
    estimateRenderTime.mockReturnValue(120)

    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate()
    })

    expect(result.current.showConfirmDialog).toBe(true)
    expect(result.current.pendingEstimate).toBe(120)
  })

  it('handleCancelRender closes dialog', async () => {
    const { estimateRenderTime } = await import('../../services/engine/renderService')
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
    const { cancelRender } = await import('../../services/engine/renderService')
    const { result } = renderUseRender()

    await act(async () => {
      result.current.handleCancelGenerate()
    })

    expect(cancelRender).toHaveBeenCalled()
  })

  it('handleConfirmRender closes dialog and calls handleGenerate with forceRender', async () => {
    const { estimateRenderTime, renderParts } = await import('../../services/engine/renderService')
    estimateRenderTime.mockReturnValue(120)

    const { result } = renderUseRender()

    // Trigger confirm dialog
    await act(async () => {
      await result.current.handleGenerate()
    })
    expect(result.current.showConfirmDialog).toBe(true)

    // Confirm render
    await act(async () => {
      result.current.handleConfirmRender()
    })

    // Dialog should close
    expect(result.current.showConfirmDialog).toBe(false)
    // renderParts should have been called (forceRender bypasses estimate check)
    expect(renderParts).toHaveBeenCalled()
  })

  it('render error with HTTP 403 triggers upgrade prompt', async () => {
    const { renderParts } = await import('../../services/engine/renderService')
    renderParts.mockRejectedValueOnce(new Error('HTTP 403 Forbidden'))

    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate(true)
    })

    // After the timeout clears loading
    await act(async () => {
      await new Promise(r => setTimeout(r, 600))
    })

    expect(result.current.logs).toContain('Unlock cloud rendering')
    expect(result.current.loading).toBe(false)
  })

  it('render error with Pro tier required triggers upgrade prompt', async () => {
    const { renderParts } = await import('../../services/engine/renderService')
    renderParts.mockRejectedValueOnce(new Error('Pro tier required'))

    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate(true)
    })

    await act(async () => {
      await new Promise(r => setTimeout(r, 600))
    })

    expect(result.current.logs).toContain('Unlock cloud rendering')
  })

  it('render error with generic message does not trigger upgrade prompt', async () => {
    const { renderParts } = await import('../../services/engine/renderService')
    renderParts.mockRejectedValueOnce(new Error('OpenSCAD compilation error'))

    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate(true)
    })

    await act(async () => {
      await new Promise(r => setTimeout(r, 600))
    })

    expect(result.current.logs).toContain('OpenSCAD compilation error')
    expect(result.current.logs).not.toContain('Unlock cloud rendering')
  })

  it('abort error logs cancelled message', async () => {
    const { renderParts } = await import('../../services/engine/renderService')
    const abortErr = new Error('Aborted')
    abortErr.name = 'AbortError'
    renderParts.mockRejectedValueOnce(abortErr)

    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate(true)
    })

    expect(result.current.logs).toContain('log.cancelled')
  })

  it('checkCache returns cached parts or undefined', async () => {
    const { result } = renderUseRender()

    // Before render, cache is empty
    expect(result.current.checkCache('anything')).toBeUndefined()

    // After render, cache is populated
    await act(async () => {
      await result.current.handleGenerate(true)
    })

    const key = JSON.stringify({ mode: 'unit', size: 20 })
    expect(result.current.checkCache(key)).toHaveLength(1)
  })

  it('evictCache removes an entry from the L1 in-memory cache', async () => {
    const { result } = renderUseRender()

    // Populate cache via a force render
    await act(async () => {
      await result.current.handleGenerate(true)
    })

    const key = JSON.stringify({ mode: 'unit', size: 20 })
    expect(result.current.checkCache(key)).toHaveLength(1)

    // Evict the entry
    act(() => {
      result.current.evictCache(key)
    })

    // Cache should now be empty for that key
    expect(result.current.checkCache(key)).toBeUndefined()
  })

  it('evictCache after blob revocation causes next forced render to call backend', async () => {
    const { renderParts } = await import('../../services/engine/renderService')
    const { result } = renderUseRender()

    // First render populates L1 cache
    await act(async () => {
      await result.current.handleGenerate(true)
    })
    expect(renderParts).toHaveBeenCalledTimes(1)
    renderParts.mockClear()

    const key = JSON.stringify({ mode: 'unit', size: 20 })

    // Confirm cache is populated
    expect(result.current.checkCache(key)).toHaveLength(1)

    // Simulate blob revocation by evicting the cache key (as done in useProjectParams cleanup)
    act(() => {
      result.current.evictCache(key)
    })

    // L1 cache entry must now be gone
    expect(result.current.checkCache(key)).toBeUndefined()

    // A forced render (bypassing L2 as well) must call the backend
    await act(async () => {
      await result.current.handleGenerate(true)
    })
    expect(renderParts).toHaveBeenCalledTimes(1)
  })

  it('onProgress updates progress and phase', async () => {
    const { renderParts } = await import('../../services/engine/renderService')
    renderParts.mockImplementationOnce((_mode, _params, _manifest, opts) => {
      opts.onProgress({ percent: 50, phase: 'compiling', log: 'Step 1 done' })
      opts.onProgress({ percent: 75 })
      opts.onProgress({ phase: 'rendering' })
      return Promise.resolve([{ type: 'main', url: 'blob:x' }])
    })

    const { result } = renderUseRender()

    await act(async () => {
      await result.current.handleGenerate(true)
    })

    expect(result.current.logs).toContain('Step 1 done')
  })

  it('handleCancelGenerate with active abort controller calls abort', async () => {
    const { renderParts, cancelRender } = await import('../../services/engine/renderService')
    // Make renderParts hang to keep the controller alive
    let resolveRender
    renderParts.mockImplementationOnce(() => new Promise(r => { resolveRender = r }))

    const { result } = renderUseRender()

    // Start render (don't await)
    act(() => {
      result.current.handleGenerate(true)
    })

    // Cancel while render is in progress
    await act(async () => {
      await result.current.handleCancelGenerate()
    })

    expect(cancelRender).toHaveBeenCalled()
    // Resolve to clean up
    resolveRender([])
  })

  it('passes exportFormat to renderParts', async () => {
    const { renderParts } = await import('../../services/engine/renderService')
    const { result } = renderUseRender({ exportFormat: 'step' })

    await act(async () => {
      await result.current.handleGenerate(true)
    })

    expect(renderParts).toHaveBeenCalledWith(
      'unit',
      { size: 20 },
      mockManifest,
      expect.objectContaining({ exportFormat: 'step' })
    )
  })

  // --- Cancelling an abandoned render --------------------------------------
  // Nightly run #171 made ~95 navigations in 40 minutes and produced ZERO
  // `render-cancel` calls: nothing cancelled on the way out, so every abandoned
  // render ran to completion against the single render worker while a live
  // user's render queued behind it. Starvation, not waste.

  /** Start a render, let its `job` event land, and leave it in flight. */
  async function startRenderAndPublishJob(result, target = { request_id: 'req-1', job_ids: ['job-1'] }) {
    const { renderParts } = await import('../../services/engine/renderService')
    let resolveRender
    renderParts.mockImplementationOnce((mode, params, manifest, opts) => {
      opts.onJob?.(target)
      return new Promise(resolve => { resolveRender = resolve })
    })
    act(() => { result.current.handleGenerate(true) })
    return () => resolveRender?.([])
  }

  it('cancels on pagehide while a render is in flight', async () => {
    const { cancelRenderOnUnload } = await import('../../services/engine/renderService')
    const { result } = renderUseRender()
    const finish = await startRenderAndPublishJob(result)

    act(() => { window.dispatchEvent(new Event('pagehide')) })

    expect(cancelRenderOnUnload).toHaveBeenCalledTimes(1)
    await act(async () => { finish() })
  })

  it('cancels on unmount while a render is in flight', async () => {
    const { cancelRenderOnUnload } = await import('../../services/engine/renderService')
    const { result, unmount } = renderUseRender()
    const finish = await startRenderAndPublishJob(result)

    act(() => { unmount() })

    expect(cancelRenderOnUnload).toHaveBeenCalledTimes(1)
    finish()
  })

  it('sends nothing on pagehide when no render is in flight', async () => {
    const { cancelRenderOnUnload } = await import('../../services/engine/renderService')
    renderUseRender()

    act(() => { window.dispatchEvent(new Event('pagehide')) })

    expect(cancelRenderOnUnload).not.toHaveBeenCalled()
  })

  it('sends nothing on unmount after the render has finished', async () => {
    const { cancelRenderOnUnload } = await import('../../services/engine/renderService')
    const { result, unmount } = renderUseRender()

    await act(async () => { await result.current.handleGenerate(true) })
    act(() => { unmount() })

    // The stream is over: holding its ids would fire a cancel at a finished render.
    expect(cancelRenderOnUnload).not.toHaveBeenCalled()
  })

  it('cancels only once when pagehide is followed by unmount', async () => {
    const { cancelRenderOnUnload } = await import('../../services/engine/renderService')
    const { result, unmount } = renderUseRender()
    const finish = await startRenderAndPublishJob(result)

    act(() => { window.dispatchEvent(new Event('pagehide')) })
    act(() => { unmount() })

    expect(cancelRenderOnUnload).toHaveBeenCalledTimes(1)
    finish()
  })

  it('stops listening for pagehide after unmount', async () => {
    const { cancelRenderOnUnload } = await import('../../services/engine/renderService')
    const { unmount } = renderUseRender()

    act(() => { unmount() })
    act(() => { window.dispatchEvent(new Event('pagehide')) })

    expect(cancelRenderOnUnload).not.toHaveBeenCalled()
  })

  // --- Superseding renders --------------------------------------------------

  it('a new render cancels the one it supersedes, server-side as well as locally', async () => {
    const { cancelSupersededRender } = await import('../../services/engine/renderService')
    const { result } = renderUseRender()
    const finish = await startRenderAndPublishJob(result)

    // Aborting the fetch only stops THIS page reading the stream; the server
    // keeps rendering unless it is told to stop.
    await act(async () => { await result.current.handleGenerate(true) })

    expect(cancelSupersededRender).toHaveBeenCalled()
    finish()
  })

  it('the first render of a session supersedes nothing', async () => {
    const { cancelSupersededRender } = await import('../../services/engine/renderService')
    const { result } = renderUseRender()

    await act(async () => { await result.current.handleGenerate(true) })

    // It is still called — the service is the one that knows whether anything
    // is in flight — but it must report that there was nothing to cancel.
    expect(cancelSupersededRender).toHaveReturnedWith(false)
  })
})
