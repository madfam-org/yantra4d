/**
 * Authenticated file download helper.
 * Attaches Bearer token from Janua when available.
 */

export class AuthRequiredError extends Error {
  constructor(message = 'Authentication required') {
    super(message)
    this.name = 'AuthRequiredError'
  }
}

/**
 * Download a file with optional auth token.
 * @param {string} url - URL to fetch
 * @param {string} filename - Filename for the download
 * @param {Function} getAccessToken - Async function returning JWT or null
 */
export async function downloadAuthenticatedFile(url, filename, getAccessToken) {
  const token = await getAccessToken?.()
  const headers = token ? { Authorization: `Bearer ${token}` } : {}

  const res = await fetch(url, { headers })

  if (res.status === 401) {
    throw new AuthRequiredError('Authentication required to download this file')
  }

  if (!res.ok) {
    throw new Error(`Download failed: ${res.status} ${res.statusText}`)
  }

  const blob = await res.blob()
  const blobUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(blobUrl)
}
