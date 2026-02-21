import { useState, useCallback } from 'react'
import { toast } from 'sonner'
import { downloadFile, downloadZip } from '../../lib/downloadUtils'
import { verify } from '../../services/engine/verifyService'

const TOAST_DURATION_MS = 2000

/**
 * High-level user actions that operate on current render state:
 * verify, download STL, reset params, share URL, and image export.
 */
export function useProjectActions({
  parts, mode, projectSlug, t,
  setLogs, getDefaultParams, getDefaultColors,
  setParams, setColors, setWireframe,
  copyShareUrl,
  handleExportImage: exportImage,
  handleExportAllViews: exportAllViews,
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
    if (parts.length === 1) {
      downloadFile(parts[0].url, `${projectSlug}_${mode}_${parts[0].type}.stl`)
      return
    }
    setLogs(prev => prev + `\n${t("log.zipping")}`)
    try {
      const items = parts.map(part => ({
        url: part.url,
        filename: `${projectSlug}_${mode}_${part.type}.stl`
      }))
      await downloadZip(items, `${projectSlug}_${mode}_all_parts.zip`)
      setLogs(prev => prev + `\n${t("log.zip_done")}`)
    } catch (e) {
      setLogs(prev => prev + `\n${t("log.error")}` + e.message)
    }
  }, [parts, mode, projectSlug, t, setLogs])

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
