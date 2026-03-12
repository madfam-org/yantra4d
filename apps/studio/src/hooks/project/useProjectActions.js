import { useState, useCallback } from 'react'
import { toast } from 'sonner'
import { downloadFile, downloadZip } from '../../lib/downloadUtils'
import { verify } from '../../services/engine/verifyService'
import { renderParts } from '../../services/engine/renderService'

const TOAST_DURATION_MS = 2000

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
}) {
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
      const res = await verify(parts, mode, projectSlug)
      setLogs(prev => prev + "\n\n--- VERIFICATION REPORT ---\n" + res.output)
      if (res.passed) setLogs(prev => prev + `\n${t("log.pass")}`)
      else setLogs(prev => prev + `\n${t("log.fail")}`)
    } catch (e) {
      setLogs(prev => prev + `\n${t("log.error")}` + e.message)
    }
  }, [parts, mode, projectSlug, t, setLogs])

  const handleDownloadStl = useCallback(async () => {
    if (parts.length === 0) return
    const ext = exportFormat || 'stl'

    // Viewer always holds GLB. For any non-GLB download, trigger a dedicated
    // render in the requested format so the user gets the real file content.
    let downloadParts = parts
    if (ext !== 'glb') {
      setLogs(prev => prev + `\nRendering ${ext.toUpperCase()} for download...`)
      try {
        downloadParts = await renderParts(mode, params, manifest, {
          project: projectSlug,
          exportFormat: ext,
        })
      } catch (e) {
        setLogs(prev => prev + `\n${t("log.error")}${e.message}`)
        return
      }
    }

    if (downloadParts.length === 1) {
      const part = downloadParts[0]
      const fileUrl = part.download_url || part.url
      downloadFile(fileUrl, `${projectSlug}_${mode}_${part.type}.${ext}`)
      return
    }
    setLogs(prev => prev + `\n${t("log.zipping")}`)
    try {
      const items = downloadParts.map(part => ({
        url: part.download_url || part.url,
        filename: `${projectSlug}_${mode}_${part.type}.${ext}`
      }))
      await downloadZip(items, `${projectSlug}_${mode}_all_parts.zip`)
      setLogs(prev => prev + `\n${t("log.zip_done")}`)
    } catch (e) {
      setLogs(prev => prev + `\n${t("log.error")}` + e.message)
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
