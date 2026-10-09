import { useCallback } from 'react'
import { buildHash } from '../system/useHashNavigation'

/**
 * Encode parameter state into a compact URL-safe string.
 * Format: base64url-encoded JSON of non-default params.
 */
function encodeParams(params: Record<string, unknown>, defaultParams: Record<string, unknown>): string | null {
  const diff: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(params)) {
    const def = defaultParams[key]
    // Use loose equality to handle number vs string from inputs
     
    if (value != def) {
      diff[key] = value
    }
  }
  if (Object.keys(diff).length === 0) return null
  // btoa accepts bytes, not Unicode. Escape non-ASCII UTF-16 code units as
  // JSON escapes (including both halves of emoji surrogate pairs). Existing
  // atob -> JSON.parse readers can then open new links without a wire migration;
  // blindly decoding old Latin-1 links as UTF-8 would change some legacy text.
  const json = JSON.stringify(diff).replace(/[\u007f-\uffff]/g, character =>
    '\\u' + character.charCodeAt(0).toString(16).padStart(4, '0'),
  )
  // Use base64url encoding (URL-safe, no padding)
  return btoa(json).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/**
 * Decode a base64url-encoded parameter string back to an object.
 */
function decodeParams(encoded: string | null): Record<string, unknown> | null {
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
export function getSharedParams(): Record<string, unknown> | null {
  const url = new URL(window.location.href)
  const encoded = url.searchParams.get('p')
  return decodeParams(encoded)
}

interface UseShareableUrlOptions {
  params: Record<string, unknown>
  mode: string
  projectSlug: string
  defaultParams: Record<string, unknown>
}

interface UseShareableUrlResult {
  generateShareUrl: () => string
  copyShareUrl: () => Promise<boolean>
}

/**
 * Hook for generating and reading shareable configuration URLs.
 */
export function useShareableUrl({ params, mode, projectSlug, defaultParams }: UseShareableUrlOptions): UseShareableUrlResult {
  const generateShareUrl = useCallback((): string => {
    const encoded = encodeParams(params, defaultParams)
    const url = new URL(window.location.href)
    // Strip existing search params and hash
    url.search = ''
    url.hash = ''
    // Set pathname to current project/mode
    url.pathname = buildHash(projectSlug, mode)
    if (encoded) {
      url.searchParams.set('p', encoded)
    }
    return url.toString()
  }, [params, mode, projectSlug, defaultParams])

  const copyShareUrl = useCallback(async (): Promise<boolean> => {
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
