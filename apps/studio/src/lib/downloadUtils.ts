/**
 * Trigger a file download via a temporary anchor element.
 */
export function downloadFile(url: string, filename: string): void {
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

/**
 * Download a data URL as a file.
 */
export function downloadDataUrl(dataUrl: string, filename: string): void {
  downloadFile(dataUrl, filename)
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
    const res = await fetch(item.url)
    const blob = await res.blob()
    zip.file(item.filename, blob)
  }
  const content = await zip.generateAsync({ type: 'blob' })
  const url = URL.createObjectURL(content)
  try {
    downloadFile(url, zipFilename)
  } finally {
    URL.revokeObjectURL(url)
  }
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
  const url = URL.createObjectURL(blob)
  try {
    downloadFile(url, zipFilename)
  } finally {
    URL.revokeObjectURL(url)
  }
  return blob
}
