import { useState, useCallback } from 'react'
import { toast } from 'sonner'
import { downloadFile, downloadZip } from '../../lib/downloadUtils'
import { verify } from '../../services/engine/verifyService'
import { renderParts } from '../../services/engine/renderService'

const TOAST_DURATION_MS = 2000

interface RenderPart {
  type: string
  url?: string
  download_url?: string
  isGlb?: boolean
  blob?: Blob
  [key: string]: unknown
}

interface Manifest {
  modes: Array<{ id: string; parts: string[]; [key: string]: unknown }>
  parts: Array<{ id: string; render_mode: number; [key: string]: unknown }>
  [key: string]: unknown
}

interface UseProjectActionsOptions {
  parts: RenderPart[]
  mode: string
  projectSlug: string
  t: (key: string) => string
  setLogs: (updater: (prev: string) => string) => void
  getDefaultParams: () => Record<string, unknown>
  getDefaultColors: () => Record<string, unknown>
  setParams: (valueOrUpdater: Record<string, unknown> | ((prev: Record<string, unknown>) => Record<string, unknown>)) => void
  setColors: (colors: Record<string, unknown>) => void
  setWireframe: (val: boolean) => void
  copyShareUrl: () => Promise<boolean>
  exportFormat?: string
  handleExportImage: (view: string) => void
  handleExportAllViews: () => Promise<void>
  params: Record<string, unknown>
  manifest: Manifest
}

interface UseProjectActionsResult {
  shareToast: boolean
  handleShare: () => Promise<void>
  handleVerify: () => Promise<void>
  handleDownloadStl: () => Promise<void>
  handleReset: () => void
  handleExportImage: (view: string) => void
  handleExportAllViews: () => Promise<void>
}

/**
 * High-level user actions that operate on current render state:
 * verify, download STL, reset params, share URL, and image export.
 */
export function useProjectActions({
  parts, mode, projectSlug, t,
  setLogs, getDefaultParams, getDefaultColors,
  setParams, setColors, setWireframe,
  copyShareUrl, exportFormat,
  handleExportImage: exportImage,
  handleExportAllViews: exportAllViews,
  params, manifest,
}: UseProjectActionsOptions): UseProjectActionsResult {
  const [shareToast, setShareToast] = useState(false)

  const handleShare = useCallback(async () => {
    const ok = await copyShareUrl()
    if (ok) {
      setShareToast(true)
      setTimeout(() => setShareToast(false), TOAST_DURATION_MS)
      toast.success(t('act.share_copied'), { duration: TOAST_DURATION_MS })
    } else {
      toast.error(t('toast.share_failed'))
    }
  }, [copyShareUrl, t])

  const handleVerify = useCallback(async () => {
    setLogs(prev => prev + `\n${t("log.verify")}`)
    try {
      const res = await verify(parts as Array<{ type: string; url: string }>, mode, projectSlug)
      setLogs(prev => prev + "\n\n--- VERIFICATION REPORT ---\n" + res.output)
      if (res.passed) setLogs(prev => prev + `\n${t("log.pass")}`)
      else setLogs(prev => prev + `\n${t("log.fail")}`)
    } catch (e) {
      setLogs(prev => prev + `\n${t("log.error")}` + (e as Error).message)
    }
  }, [parts, mode, projectSlug, t, setLogs])

  const handleDownloadStl = useCallback(async () => {
    if (parts.length === 0) return
    const ext = exportFormat || 'stl'

    // Check if the viewer already has files in the requested format.
    const viewerHasFormat = parts.length > 0 && parts.every(p => {
      const dlUrl = (p.download_url || '').split('?')[0]
      const viewUrl = (p.url || '').split('?')[0]
      return dlUrl.endsWith(`.${ext}`) || viewUrl.endsWith(`.${ext}`) ||
        (ext === 'glb' && p.isGlb)
    })

    let downloadParts = parts
    if (!viewerHasFormat) {
      setLogs(prev => prev + `\nRendering ${ext.toUpperCase()} for download...`)
      try {
        downloadParts = await renderParts(mode, params, manifest as unknown as Parameters<typeof renderParts>[2], {
          project: projectSlug,
          exportFormat: ext,
        }) as unknown as RenderPart[]
      } catch (e) {
        setLogs(prev => prev + `\n${t("log.error")}${(e as Error).message}`)
        return
      }
    }

    // Pick the URL whose extension matches the requested format
    const pickUrl = (part: RenderPart): string => {
      const dlUrl = part.download_url || ''
      const viewUrl = part.url || ''
      if (dlUrl.split('?')[0].endsWith(`.${ext}`)) return dlUrl
      if (viewUrl.split('?')[0].endsWith(`.${ext}`)) return viewUrl
      if (ext === 'glb' && part.isGlb) return viewUrl
      return dlUrl || viewUrl
    }

    if (downloadParts.length === 1) {
      const part = downloadParts[0]
      await downloadFile(pickUrl(part), `${projectSlug}_${mode}_${part.type}.${ext}`)
      return
    }
    setLogs(prev => prev + `\n${t("log.zipping")}`)
    try {
      const items = downloadParts.map(part => ({
        url: pickUrl(part),
        filename: `${projectSlug}_${mode}_${part.type}.${ext}`
      }))
      await downloadZip(items, `${projectSlug}_${mode}_all_parts.zip`)
      setLogs(prev => prev + `\n${t("log.zip_done")}`)
    } catch (e) {
      setLogs(prev => prev + `\n${t("log.error")}` + (e as Error).message)
    }
  }, [parts, mode, projectSlug, t, setLogs, exportFormat, params, manifest])

  const handleReset = useCallback(() => {
    setParams(getDefaultParams())
    setColors(getDefaultColors())
    setWireframe(false)
  }, [getDefaultParams, getDefaultColors, setParams, setColors, setWireframe])

  return {
    shareToast,
    handleShare,
    handleVerify,
    handleDownloadStl,
    handleReset,
    handleExportImage: exportImage,
    handleExportAllViews: exportAllViews,
  }
}
