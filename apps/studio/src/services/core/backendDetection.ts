const API_BASE: string = import.meta.env.VITE_API_BASE || ''

let _backendAvailable: boolean | null = null
let _lastCheckTime = 0
const NEGATIVE_TTL_MS = 30_000  // retry after 30s if backend was down
const POSITIVE_TTL_MS = 300_000 // re-check every 5 min if backend was up

/**
 * Check if the backend API is reachable.
 * Caches the result with TTL: 30s for negative, 5min for positive.
 */
export async function isBackendAvailable(): Promise<boolean> {
  const now = Date.now()
  if (_backendAvailable !== null) {
    const ttl = _backendAvailable ? POSITIVE_TTL_MS : NEGATIVE_TTL_MS
    if (now - _lastCheckTime < ttl) return _backendAvailable
  }
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(2000) })
    _backendAvailable = res.ok
  } catch {
    _backendAvailable = false
  }
  _lastCheckTime = now
  return _backendAvailable
}

/**
 * Get the API base URL.
 */
export function getApiBase(): string {
  return API_BASE
}

/**
 * Reset cached detection (clears both result and TTL timer).
 */
export function resetDetection(): void {
  _backendAvailable = null
  _lastCheckTime = 0
}
