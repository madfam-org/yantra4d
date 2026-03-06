const API_BASE: string = import.meta.env.VITE_API_BASE || ''

let _backendAvailable: boolean | null = null

/**
 * Check if the backend API is reachable. Caches the result after first call.
 */
export async function isBackendAvailable(): Promise<boolean> {
  if (_backendAvailable !== null) return _backendAvailable
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(2000) })
    _backendAvailable = res.ok
  } catch {
    _backendAvailable = false
  }
  return _backendAvailable
}

/**
 * Get the API base URL.
 */
export function getApiBase(): string {
  return API_BASE
}

/**
 * Reset cached detection (useful for testing).
 */
export function resetDetection(): void {
  _backendAvailable = null
}
