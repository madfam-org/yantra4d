import { apiFetch } from '../services/core/apiClient'
import { getApiBase } from '../services/core/backendDetection'

async function fetchArtifact(url: string): Promise<Response> {
  const target = new URL(url, window.location.href)
  const api = new URL(getApiBase() || '/', window.location.href)
  const trusted = target.origin === api.origin &&
    (target.pathname.startsWith('/api/') || target.pathname.startsWith('/static/'))
  const response = await (trusted ? apiFetch(url) : fetch(url))
  if (!response.ok) throw new Error(`Download failed (HTTP ${response.status})`)
  return response
}

/**
 * Trigger a file download. Fetches the file as a blob first so that the
 * `download` attribute's filename is respected even for cross-origin URLs.
 */
export async function downloadFile(url: string, filename: string): Promise<void> {
  const response = await fetchArtifact(url)
  triggerBlobDownload(await response.blob(), filename)
}

function triggerBlobDownload(blob: Blob, filename: string): void {
  const blobUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  try {
    link.href = blobUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
  } finally {
    link.remove()
    URL.revokeObjectURL(blobUrl)
  }
}

/**
 * Download a data URL as a file.
 */
export function downloadDataUrl(dataUrl: string, filename: string): Promise<void> {
  return downloadFile(dataUrl, filename)
}

interface ZipUrlItem {
  url: string
  filename: string
}

/**
 * Create a ZIP from an array of { url, filename } items, then trigger download.
 * For blob URLs, fetches each one. Returns the generated blob.
 */
export async function downloadZip(items: ZipUrlItem[], zipFilename: string): Promise<Blob> {
  const { default: JSZip } = await import('jszip')
  const zip = new JSZip()
  for (const item of items) {
    const res = await fetchArtifact(item.url)
    const blob = await res.blob()
    zip.file(item.filename, blob)
  }
  const content = await zip.generateAsync({ type: 'blob' })
  triggerBlobDownload(content, zipFilename)
  return content
}

interface ZipDataItem {
  filename: string
  data: Uint8Array
}

/**
 * Create a ZIP from an array of { filename, data: Uint8Array } items, then trigger download.
 */
export async function downloadZipFromData(items: ZipDataItem[], zipFilename: string): Promise<Blob> {
  const { default: JSZip } = await import('jszip')
  const zip = new JSZip()
  for (const item of items) {
    zip.file(item.filename, item.data)
  }
  const blob = await zip.generateAsync({ type: 'blob' })
  triggerBlobDownload(blob, zipFilename)
  return blob
}
