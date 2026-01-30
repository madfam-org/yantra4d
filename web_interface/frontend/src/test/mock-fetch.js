import { vi } from 'vitest'

/**
 * Mock fetch to reject (simulates no backend), triggering fallback manifest.
 * Call in beforeEach.
 */
export function mockFetchNoBackend() {
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('no backend'))
}

/**
 * Mock fetch to resolve health check as OK (backend available).
 * Returns the mock so you can chain additional mockResolvedValueOnce calls.
 */
export function mockFetchBackendAvailable() {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({ ok: true })
}
