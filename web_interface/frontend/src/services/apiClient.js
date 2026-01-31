/**
 * Shared API client that injects Authorization header when a token is available.
 */

let _getToken = null

/**
 * Set the token getter function. Called once from App.jsx with auth context.
 * @param {() => Promise<string|null>} getter
 */
export function setTokenGetter(getter) {
  _getToken = getter
}

/**
 * Fetch wrapper that auto-injects Bearer token.
 * @param {string} url
 * @param {RequestInit} [options]
 * @returns {Promise<Response>}
 */
export async function apiFetch(url, options = {}) {
  const headers = { ...options.headers }

  if (_getToken) {
    try {
      const token = await _getToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
    } catch {
      // Token retrieval failed — proceed without auth
    }
  }

  return fetch(url, { ...options, headers })
}
