import { useCallback } from 'react'

/**
 * Encode parameter state into a compact URL-safe string.
 * Format: base64url-encoded JSON of non-default params.
 */
function encodeParams(params, defaultParams) {
  const diff = {}
  for (const [key, value] of Object.entries(params)) {
    const def = defaultParams[key]
    // Use loose equality to handle number vs string from inputs
    if (value != def) {
      diff[key] = value
    }
  }
  if (Object.keys(diff).length === 0) return null
  const json = JSON.stringify(diff)
  // Use base64url encoding (URL-safe, no padding)
  return btoa(json).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/**
 * Decode a base64url-encoded parameter string back to an object.
 */
function decodeParams(encoded) {
  if (!encoded) return null
  try {
    const base64 = encoded.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64 + '='.repeat((4 - base64.length % 4) % 4)
    const json = atob(padded)
    return JSON.parse(json)
  } catch {
    return null
  }
}

/**
 * Extract encoded params from URL search params (?p=...).
 */
export function getSharedParams() {
  const url = new URL(window.location.href)
  const encoded = url.searchParams.get('p')
  return decodeParams(encoded)
}

/**
 * Hook for generating and reading shareable configuration URLs.
 */
export function useShareableUrl({ params, mode, projectSlug, defaultParams }) {
  const generateShareUrl = useCallback(() => {
    const encoded = encodeParams(params, defaultParams)
    const url = new URL(window.location.href)
    // Strip existing search params
    url.search = ''
    // Set hash to current project/mode
    url.hash = `/${projectSlug}/share/${mode}`
    if (encoded) {
      url.searchParams.set('p', encoded)
    }
    return url.toString()
  }, [params, mode, projectSlug, defaultParams])

  const copyShareUrl = useCallback(async () => {
    const url = generateShareUrl()
    try {
      await navigator.clipboard.writeText(url)
      return true
    } catch {
      return false
    }
  }, [generateShareUrl])

  return { generateShareUrl, copyShareUrl }
}
