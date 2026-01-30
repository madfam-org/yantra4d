/**
 * Trigger a file download via a temporary anchor element.
 */
export function downloadFile(url, filename) {
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
export function downloadDataUrl(dataUrl, filename) {
  downloadFile(dataUrl, filename)
}

/**
 * Create a ZIP from an array of { url, filename } items, then trigger download.
 * For blob URLs, fetches each one. Returns the generated blob.
 */
export async function downloadZip(items, zipFilename) {
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

/**
 * Create a ZIP from an array of { filename, data: Uint8Array } items, then trigger download.
 */
export async function downloadZipFromData(items, zipFilename) {
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
