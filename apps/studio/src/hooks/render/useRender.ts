import { useState, useRef, useCallback } from 'react'
import { renderParts, cancelRender, estimateRenderTime } from '../../services/engine/renderService'
import { useUpgradePrompt } from '../system/useUpgradePrompt'
import * as idbCache from '../../services/cache/renderCache'

const INITIAL_PROGRESS = 5
const LOADING_RESET_DELAY_MS = 500

interface Manifest {
  modes: Array<{ id: string; parts: string[]; [key: string]: unknown }>
  parts: Array<{ id: string; render_mode: number; [key: string]: unknown }>
  parameters: Array<{ id: string; [key: string]: unknown }>
  estimate_constants?: {
    base_time: number
    per_unit: number
    per_part: number
    wasm_multiplier?: number
    warning_threshold_seconds?: number
  }
  [key: string]: unknown
}

interface RenderPart {
  type: string
  url?: string
  blob?: Blob
  download_url?: string
  isGlb?: boolean
  [key: string]: unknown
}

interface UseRenderOptions {
  mode: string
  params: Record<string, unknown>
  manifest: Manifest
  t: (key: string) => string
  getCacheKey: (mode: string, params: Record<string, unknown>) => string
  project?: string
  exportFormat?: string
}

interface UseRenderResult {
  parts: RenderPart[]
  setParts: React.Dispatch<React.SetStateAction<RenderPart[]>>
  logs: string
  setLogs: React.Dispatch<React.SetStateAction<string>>
  loading: boolean
  progress: number
  progressPhase: string
  checkCache: (key: string) => RenderPart[] | undefined
  evictCache: (key: string) => void
  showConfirmDialog: boolean
  pendingEstimate: number
  handleGenerate: (forceRender?: boolean, overridePayload?: Record<string, unknown> | null) => Promise<void>
  handleCancelGenerate: () => Promise<void>
  handleConfirmRender: () => void
  handleCancelRender: () => void
}

/**
 * Hook encapsulating render orchestration: generate, cancel, confirm dialog, cache.
 */
export function useRender({ mode, params, manifest, t, getCacheKey, project, exportFormat }: UseRenderOptions): UseRenderResult {
  const [parts, setParts] = useState<RenderPart[]>([])
  const [logs, setLogs] = useState(t("log.ready"))
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressPhase, setProgressPhase] = useState('')
  const { triggerUpgradePrompt } = useUpgradePrompt()

  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [pendingEstimate, setPendingEstimate] = useState(0)
  const [pendingPayload, setPendingPayload] = useState<Record<string, unknown> | null>(null)

  const partsCacheRef = useRef<Record<string, RenderPart[]>>({})

  const abortControllerRef = useRef<AbortController | null>(null)

  /** Evict a specific key from the L1 in-memory cache. Called externally when blobs are revoked. */
  const evictCache = useCallback((key: string) => {
    delete partsCacheRef.current[key]
  }, [])

  const handleGenerate = useCallback(async (forceRender: boolean = false, overridePayload: Record<string, unknown> | null = null) => {
    const payload = overridePayload || { ...params, mode }
    const cacheKey = getCacheKey(mode, params)

    // L1: In-memory cache (instant)
    if (!forceRender && partsCacheRef.current[cacheKey]) {
      setParts(partsCacheRef.current[cacheKey])
      setLogs(prev => prev + `\n⚡ ${t("log.cache_hit")}`)
      return
    }

    // L2: IndexedDB persistent cache (~5ms)
    if (!forceRender) {
      try {
        const idbKey = await idbCache.makeCacheKey(project || '', mode, params, exportFormat || 'glb')
        const cached = await idbCache.get(idbKey)
        if (cached) {
          const restoredParts: RenderPart[] = cached.map(p => {
            const part: RenderPart = {
              type: p.type,
              url: URL.createObjectURL(p.blob),
              isGlb: p.blob.type === 'model/gltf-binary',
            }
            if ((p as { downloadBlob?: Blob }).downloadBlob) {
              // Append #.stl so URL extension checks in handleDownloadStl work
              // for blob URLs. Browsers strip fragments before fetch, so the
              // blob URL still resolves correctly.
              part.download_url = URL.createObjectURL((p as { downloadBlob: Blob }).downloadBlob) + '#.stl'
            }
            return part
          })
          setParts(restoredParts)
          partsCacheRef.current[cacheKey] = restoredParts
          setLogs(prev => prev + `\n⚡ ${t("log.cache_hit")}`)
          return
        }
      } catch {
        // IndexedDB unavailable — fall through to backend
      }
    }

    if (!forceRender) {
      const estimate = estimateRenderTime(mode, params, manifest as unknown as Parameters<typeof estimateRenderTime>[2])
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
      const result = await renderParts(mode, params, manifest as unknown as Parameters<typeof renderParts>[2], {
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
        project,
        ignoreCache: forceRender,
        exportFormat
      })

      setParts(result as unknown as RenderPart[])
      partsCacheRef.current[cacheKey] = result as unknown as RenderPart[]
      setProgress(100)
      setLogs(prev => prev + `\n${t("log.gen_stl")}`)

      // Populate IndexedDB cache in the background
      idbCache.makeCacheKey(project || '', mode, params, exportFormat || 'glb')
        .then(idbKey => idbCache.put(idbKey, result))
        .catch(() => {})
    } catch (e) {
      if ((e as Error).name === 'AbortError') {
        setLogs(prev => prev + `\n${t("log.cancelled")}`)
      } else {
        const isProGate = (e as Error).message.includes('HTTP 403') || (e as Error).message.includes('Pro tier required');
        const msg = isProGate
          ? "✨ Unlock cloud rendering by upgrading to a Pro or MadFam plan."
          : (e as Error).message;
        setLogs(prev => prev + `\n${t("log.error")} ${msg}`)

        if (isProGate) {
          triggerUpgradePrompt('CadQuery Cloud Rendering')
        }
      }
    } finally {
      abortControllerRef.current = null
      setProgressPhase('')
      setTimeout(() => {
        setLoading(false)
        setProgress(0)
      }, LOADING_RESET_DELAY_MS)
    }
  }, [mode, params, manifest, t, getCacheKey, project, exportFormat, triggerUpgradePrompt])

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
    /** Look up cached render result by cache key. Returns part array or undefined. */
    checkCache: (key: string) => partsCacheRef.current[key],
    /** Evict a cache key from L1 when its blob URLs have been revoked. */
    evictCache,
    showConfirmDialog,
    pendingEstimate,
    handleGenerate,
    handleCancelGenerate,
    handleConfirmRender,
    handleCancelRender,
  }
}
