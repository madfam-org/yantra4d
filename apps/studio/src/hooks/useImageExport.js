import { useCallback } from 'react'
import { downloadDataUrl, downloadZipFromData } from '../lib/downloadUtils'

const CAMERA_SETTLE_MS = 100
const SCREENSHOT_DELAY_MS = 150

/**
 * Hook for exporting viewer snapshots as PNG images.
 */
export function useImageExport({ viewerRef, projectSlug, mode, parts, setLogs, t, cameraViews }) {
  const handleExportImage = useCallback((view) => {
    if (!viewerRef.current) return
    viewerRef.current.setCameraView(view)
    setTimeout(() => {
      const dataUrl = viewerRef.current.captureSnapshot()
      downloadDataUrl(dataUrl, `${projectSlug}_${mode}_${view}.png`)
    }, CAMERA_SETTLE_MS)
  }, [viewerRef, projectSlug, mode])

  const handleExportAllViews = useCallback(async () => {
    if (!viewerRef.current || parts.length === 0) return
    try {
      const views = (cameraViews || []).map(v => v.id)
      const items = []
      for (const view of views) {
        viewerRef.current.setCameraView(view)
        await new Promise(r => setTimeout(r, SCREENSHOT_DELAY_MS))
        const dataUrl = viewerRef.current.captureSnapshot()
        const data = atob(dataUrl.split(',')[1])
        const arr = new Uint8Array(data.length)
        for (let i = 0; i < data.length; i++) arr[i] = data.charCodeAt(i)
        items.push({ filename: `${projectSlug}_${mode}_${view}.png`, data: arr })
      }
      await downloadZipFromData(items, `${projectSlug}_${mode}_all_views.zip`)
    } catch (e) {
      console.error('Export all views failed:', e)
      setLogs(prev => prev + `\n${t("log.error")}` + e.message)
    }
  }, [viewerRef, projectSlug, mode, parts, setLogs, t, cameraViews])

  return { handleExportImage, handleExportAllViews }
}
