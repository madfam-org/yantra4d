import { useCallback } from 'react'
import { getApiBase } from '../services/core/backendDetection'

/**
 * Lightweight analytics hook.
 * Sends non-blocking fire-and-forget events to the backend.
 * No PII collected — only aggregate counts.
 */
export function useAnalytics(projectSlug) {
  const track = useCallback((event, data = null) => {
    try {
      const payload = { project: projectSlug, event, data }
      // Use sendBeacon for non-blocking delivery, fallback to fetch
      const body = JSON.stringify(payload)
      const url = `${getApiBase()}/api/analytics/track`

      if (navigator.sendBeacon) {
        navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }))
      } else {
        fetch(url, { method: 'POST', body, headers: { 'Content-Type': 'application/json' }, keepalive: true })
          .catch(() => {}) // Silent fail — analytics should never break the app
      }
    } catch {
      // Silent fail
    }
  }, [projectSlug])

  return { track }
}
