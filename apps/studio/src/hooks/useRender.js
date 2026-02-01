import { useState, useRef, useCallback } from 'react'
import { renderParts, cancelRender, estimateRenderTime } from '../services/renderService'

const INITIAL_PROGRESS = 5
const LOADING_RESET_DELAY_MS = 500

/**
 * Hook encapsulating render orchestration: generate, cancel, confirm dialog, cache.
 */
export function useRender({ mode, params, manifest, t, getCacheKey, project }) {
  const [parts, setParts] = useState([])
  const [logs, setLogs] = useState(t("log.ready"))
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressPhase, setProgressPhase] = useState('')

  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [pendingEstimate, setPendingEstimate] = useState(0)
  const [pendingPayload, setPendingPayload] = useState(null)

  const partsCacheRef = useRef({})

  const abortControllerRef = useRef(null)

  const handleGenerate = useCallback(async (forceRender = false, overridePayload = null) => {
    const payload = overridePayload || { ...params, mode }
    const cacheKey = getCacheKey(mode, params)

    if (!forceRender && partsCacheRef.current[cacheKey]) {
      setParts(partsCacheRef.current[cacheKey])
      setLogs(prev => prev + `\n⚡ ${t("log.cache_hit")}`)
      return
    }

    if (!forceRender) {
      const estimate = estimateRenderTime(mode, params, manifest)
      const threshold = manifest.estimate_constants?.warning_threshold_seconds || 60
      if (estimate > threshold) {
        setPendingEstimate(estimate)
        setPendingPayload(payload)
        setShowConfirmDialog(true)
        return
      }
    }

    setLoading(true)
    setProgress(INITIAL_PROGRESS)
    setProgressPhase(t("phase.compiling"))
    setLogs(prev => prev + `\n${t("log.generating")} (${mode})...`)

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const result = await renderParts(mode, params, manifest, {
        onProgress: ({ percent, phase, log }) => {
          if (percent !== undefined) setProgress(percent)
          if (phase) {
            const phaseKey = `phase.${phase}`
            const translated = t(phaseKey)
            if (translated !== phaseKey) setProgressPhase(translated)
          }
          if (log) setLogs(prev => prev + `\n${log}`)
        },
        abortSignal: controller.signal,
        project
      })

      setParts(result)
      partsCacheRef.current[cacheKey] = result
      setProgress(100)
      setLogs(prev => prev + `\n${t("log.gen_stl")}`)
    } catch (e) {
      if (e.name === 'AbortError') {
        setLogs(prev => prev + `\n${t("log.cancelled")}`)
      } else {
        setLogs(prev => prev + `\n${t("log.error")}` + e.message)
      }
    } finally {
      abortControllerRef.current = null
      setProgressPhase('')
      setTimeout(() => {
        setLoading(false)
        setProgress(0)
      }, LOADING_RESET_DELAY_MS)
    }
  }, [mode, params, manifest, t, getCacheKey, project])

  const handleCancelGenerate = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    await cancelRender()
  }, [])

  const handleConfirmRender = useCallback(() => {
    setShowConfirmDialog(false)
    handleGenerate(true, pendingPayload)
  }, [handleGenerate, pendingPayload])

  const handleCancelRender = useCallback(() => {
    setShowConfirmDialog(false)
    setPendingEstimate(0)
    setPendingPayload(null)
  }, [])

  return {
    parts,
    setParts,
    logs,
    setLogs,
    loading,
    progress,
    progressPhase,
    checkCache: (key) => partsCacheRef.current[key],
    showConfirmDialog,
    pendingEstimate,
    handleGenerate,
    handleCancelGenerate,
    handleConfirmRender,
    handleCancelRender,
  }
}
