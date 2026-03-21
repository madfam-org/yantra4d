/**
 * Shared API client that injects Authorization header when a token is available.
 * Tracks rate limit headers from render responses.
 */
import { useState } from 'react'

type TokenGetter = () => Promise<string | null>

interface RateLimitState {
  remaining: number | null
  limit: number | null
  tier: string | null
}

type RateLimitListener = (state: RateLimitState) => void

let _getToken: TokenGetter | null = null

// Rate limit state (module-level singleton)
const _rateLimitState: RateLimitState = { remaining: null, limit: null, tier: null }
const _rateLimitListeners: Set<RateLimitListener> = new Set()

function _notifyRateLimitListeners(): void {
  _rateLimitListeners.forEach(fn => fn({ ..._rateLimitState }))
}

/**
 * Set the token getter function. Called once from App.jsx with auth context.
 */
export function setTokenGetter(getter: TokenGetter): void {
  _getToken = getter
}

/**
 * Fetch wrapper that auto-injects Bearer token and extracts rate limit headers.
 */
export async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) }

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
/**
 * Check if the backend render rate limit has been exhausted.
 */
export function isRateLimitExhausted(): boolean {
  return _rateLimitState.remaining !== null && _rateLimitState.remaining <= 0
}

export function useRateLimit(): RateLimitState {
  const [state, setState] = useState<RateLimitState>({ ..._rateLimitState })

  // Subscribe on first call via module-level set
  // Using useState initializer to register only once
  useState(() => {
    const listener: RateLimitListener = (newState) => setState(newState)
    _rateLimitListeners.add(listener)
    // Return cleanup (not used by useState, but we store ref)
    return () => _rateLimitListeners.delete(listener)
  })

  return state
}
