import { useCallback, RefObject } from 'react'
import { downloadDataUrl, downloadZipFromData } from '../../lib/downloadUtils'

const CAMERA_SETTLE_MS = 100
const SCREENSHOT_DELAY_MS = 150

interface CameraView {
  id: string
  [key: string]: unknown
}

interface ViewerRef {
  setCameraView: (view: string) => void
  captureSnapshot: () => string
}

interface RenderPart {
  type: string
  url?: string
  [key: string]: unknown
}

interface ImageExportOptions {
  viewerRef: RefObject<ViewerRef | null>
  projectSlug: string
  mode: string
  parts: RenderPart[]
  setLogs: (updater: (prev: string) => string) => void
  t: (key: string) => string
  cameraViews?: CameraView[]
}

interface ImageExportResult {
  handleExportImage: (view: string) => void
  handleExportAllViews: () => Promise<void>
}

/**
 * Hook for exporting viewer snapshots as PNG images.
 */
export function useImageExport({
  viewerRef, projectSlug, mode, parts, setLogs, t, cameraViews
}: ImageExportOptions): ImageExportResult {
  const handleExportImage = useCallback((view: string) => {
    if (!viewerRef.current) return
    viewerRef.current.setCameraView(view)
    setTimeout(() => {
      const dataUrl = viewerRef.current!.captureSnapshot()
      downloadDataUrl(dataUrl, `${projectSlug}_${mode}_${view}.png`)
    }, CAMERA_SETTLE_MS)
  }, [viewerRef, projectSlug, mode])

  const handleExportAllViews = useCallback(async () => {
    if (!viewerRef.current || parts.length === 0) return
    try {
      const views = (cameraViews || []).map(v => v.id)
      const items: Array<{ filename: string; data: Uint8Array }> = []
      for (const view of views) {
        viewerRef.current!.setCameraView(view)
        await new Promise<void>(r => setTimeout(r, SCREENSHOT_DELAY_MS))
        const dataUrl = viewerRef.current!.captureSnapshot()
        let data: string
        try {
          data = atob(dataUrl.split(',')[1])
        } catch (decodeErr) {
          console.warn(`Failed to decode snapshot for view "${view}":`, (decodeErr as Error).message)
          continue
        }
        const arr = new Uint8Array(data.length)
        for (let i = 0; i < data.length; i++) arr[i] = data.charCodeAt(i)
        items.push({ filename: `${projectSlug}_${mode}_${view}.png`, data: arr })
      }
      await downloadZipFromData(items, `${projectSlug}_${mode}_all_views.zip`)
    } catch (e) {
      console.error('Export all views failed:', e)
      setLogs(prev => prev + `\n${t("log.error")}` + (e as Error).message)
    }
  }, [viewerRef, projectSlug, mode, parts, setLogs, t, cameraViews])

  return { handleExportImage, handleExportAllViews }
}
