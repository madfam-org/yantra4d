import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('idleCallback polyfill', () => {
  let originalRIC
  let originalCIC

  beforeEach(() => {
    originalRIC = globalThis.requestIdleCallback
    originalCIC = globalThis.cancelIdleCallback
  })

  afterEach(() => {
    globalThis.requestIdleCallback = originalRIC
    globalThis.cancelIdleCallback = originalCIC
    vi.restoreAllMocks()
  })

  it('uses native requestIdleCallback when available', async () => {
    const nativeRIC = vi.fn((cb) => { cb({ didTimeout: false, timeRemaining: () => 10 }); return 42 })
    globalThis.requestIdleCallback = nativeRIC

    // Re-import to pick up the native version
    const mod = await import('./idleCallback.ts?native')
    expect(mod.requestIdleCallback).toBe(nativeRIC)
  })

  it('falls back to setTimeout when native rIC is unavailable', async () => {
    delete globalThis.requestIdleCallback
    delete globalThis.cancelIdleCallback

    vi.useFakeTimers()

    // Dynamic import to get fresh module without native rIC
    const mod = await import('./idleCallback.ts?fallback')

    const cb = vi.fn()
    mod.requestIdleCallback(cb, { timeout: 100 })

    expect(cb).not.toHaveBeenCalled()
    vi.advanceTimersByTime(200)
    expect(cb).toHaveBeenCalledTimes(1)

    // Verify the synthetic IdleDeadline shape
    const arg = cb.mock.calls[0][0]
    expect(arg.didTimeout).toBe(false)
    expect(typeof arg.timeRemaining).toBe('function')
    expect(arg.timeRemaining()).toBe(50)

    vi.useRealTimers()
  })

  it('cancelIdleCallback falls back to clearTimeout', async () => {
    delete globalThis.requestIdleCallback
    delete globalThis.cancelIdleCallback

    vi.useFakeTimers()

    const mod = await import('./idleCallback.ts?cancel')

    const cb = vi.fn()
    const id = mod.requestIdleCallback(cb, { timeout: 100 })
    mod.cancelIdleCallback(id)
    vi.advanceTimersByTime(200)
    expect(cb).not.toHaveBeenCalled()

    vi.useRealTimers()
  })
})
