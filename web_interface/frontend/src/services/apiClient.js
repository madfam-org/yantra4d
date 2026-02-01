/**
 * Shared API client that injects Authorization header when a token is available.
 * Tracks rate limit headers from render responses.
 */
import { useState } from 'react'

let _getToken = null

// Rate limit state (module-level singleton)
let _rateLimitState = { remaining: null, limit: null, tier: null }
let _rateLimitListeners = new Set()

function _notifyRateLimitListeners() {
  _rateLimitListeners.forEach(fn => fn({ ..._rateLimitState }))
}

/**
 * Set the token getter function. Called once from App.jsx with auth context.
 * @param {() => Promise<string|null>} getter
 */
export function setTokenGetter(getter) {
  _getToken = getter
}

/**
 * Fetch wrapper that auto-injects Bearer token and extracts rate limit headers.
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

  const response = await fetch(url, { ...options, headers })

  // Extract rate limit headers if present
  if (response.headers?.get) {
    const rlLimit = response.headers.get('X-RateLimit-Limit')
    const rlRemaining = response.headers.get('X-RateLimit-Remaining')
    const rlTier = response.headers.get('X-RateLimit-Tier')
    if (rlLimit !== null || rlRemaining !== null) {
      if (rlLimit !== null) _rateLimitState.limit = parseInt(rlLimit, 10)
      if (rlRemaining !== null) _rateLimitState.remaining = parseInt(rlRemaining, 10)
      if (rlTier !== null) _rateLimitState.tier = rlTier
      _notifyRateLimitListeners()
    }
  }

  return response
}

/**
 * React hook to subscribe to rate limit state changes.
 */
export function useRateLimit() {
  const [state, setState] = useState({ ..._rateLimitState })

  // Subscribe on first call via module-level set
  // Using useState initializer to register only once
  useState(() => {
    const listener = (newState) => setState(newState)
    _rateLimitListeners.add(listener)
    // Return cleanup (not used by useState, but we store ref)
    return () => _rateLimitListeners.delete(listener)
  })

  return state
}
