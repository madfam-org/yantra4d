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

/** Sentinel used by the tier API and the rate-limit headers for "no ceiling". */
export const UNLIMITED = -1

/** Whether a tier limit or rate-limit header value means "no ceiling". */
export function isUnlimited(value: number | null | undefined): boolean {
  return typeof value === 'number' && value < 0
}

let _getToken: TokenGetter | null = null

// Rate limit state (module-level singleton)
const _rateLimitState: RateLimitState = { remaining: null, limit: null, tier: null }
const _rateLimitListeners: Set<RateLimitListener> = new Set()

function _notifyRateLimitListeners(): void {
  _rateLimitListeners.forEach(fn => fn({ ..._rateLimitState }))
}

/**
 * Parse one X-RateLimit-* header value.
 *
 * An unlimited tier answers `X-RateLimit-Limit: unlimited` (and sends no
 * Remaining/Reset), so a bare parseInt stored NaN — which is neither null nor
 * a number anything downstream can compare, and rendered as "NaN/hr".
 * `unlimited` maps to the same sentinel the tier API uses for "no ceiling",
 * -1; anything unparseable is "unknown", null.
 */
function _parseRateLimitHeader(value: string): number | null {
  if (value.trim().toLowerCase() === 'unlimited') return UNLIMITED
  const parsed = parseInt(value, 10)
  return Number.isNaN(parsed) ? null : parsed
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
      if (rlLimit !== null) {
        _rateLimitState.limit = _parseRateLimitHeader(rlLimit)
        // An unlimited tier sends no Remaining, so a count left over from an
        // earlier limited response would otherwise keep warning against a
        // ceiling that no longer applies.
        if (isUnlimited(_rateLimitState.limit)) _rateLimitState.remaining = null
      }
      if (rlRemaining !== null) {
        // Keep the invariant "remaining is a real count or null": an unlimited
        // tier has nothing to count down, so it must not read as a deficit.
        const parsedRemaining = _parseRateLimitHeader(rlRemaining)
        _rateLimitState.remaining = isUnlimited(parsedRemaining) ? null : parsedRemaining
      }
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
  if (isUnlimited(_rateLimitState.limit)) return false
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
