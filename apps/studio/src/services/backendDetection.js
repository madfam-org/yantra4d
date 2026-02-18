const API_BASE = import.meta.env.VITE_API_BASE || ''

let _backendAvailable = null

/**
 * Check if the backend API is reachable. Caches the result after first call.
 * @returns {Promise<boolean>}
 */
export async function isBackendAvailable() {
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
export function getApiBase() {
  return API_BASE
}

/**
 * Reset cached detection (useful for testing).
 */
export function resetDetection() {
  _backendAvailable = null
}
