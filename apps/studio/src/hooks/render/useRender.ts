import { useState, useRef, useCallback, useEffect } from 'react'
import { toast } from 'sonner'
import {
  renderParts,
  cancelRender,
  cancelRenderOnUnload,
  cancelSupersededRender,
  estimateRenderTime,
} from '../../services/engine/renderService'
import type { RenderCancelTarget } from '../../services/engine/renderService'
import { useUpgradePrompt } from '../system/useUpgradePrompt'
import * as idbCache from '../../services/cache/renderCache'

const INITIAL_PROGRESS = 5
const LOADING_RESET_DELAY_MS = 500
const SKIPPED_TOAST_DURATION_MS = 6000
/** One id, so a run of param edits replaces the notice instead of stacking it. */
const SKIPPED_TOAST_ID = 'auto-render-over-threshold'

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
  /** The format `url` holds, when the URL cannot say so (a `blob:` URL). */
  format?: string
  /** The format `download_url` holds, when the URL cannot say so. */
  download_format?: string
  [key: string]: unknown
}

interface UseRenderOptions {
  mode: string
  params: Record<string, unknown>
  manifest: Manifest
  /** LanguageProvider's t; `params` fills {placeholders} in the translation. */
  t: (key: string, params?: Record<string, string | number>) => string
  getCacheKey: (mode: string, params: Record<string, unknown>) => string
  project?: string
  exportFormat?: string
}

/** How a render was asked for. */
export interface GenerateOptions {
  /**
   * True when nothing the user did asked for THIS render — the debounced
   * on-load / param-change effect in useProjectParams. An automatic render that
   * is estimated over the cartridge's warning threshold is skipped with a
   * toast rather than confirmed with a modal; see handleGenerate.
   */
  automatic?: boolean
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
  handleGenerate: (forceRender?: boolean, overridePayload?: Record<string, unknown> | null, options?: GenerateOptions) => Promise<void>
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

  /**
   * The cancellable identity of the backend render this hook has in flight,
   * as `/api/render-stream` published it on its `job` event. Null whenever
   * nothing is running, or when the render is a browser (WASM) one — those have
   * nothing server-side to cancel.
   *
   * A ref, not state: it is read from an unload handler and from the effect
   * cleanup, neither of which may depend on a re-render having happened, and
   * nothing in the UI displays it.
   */
  const activeTargetRef = useRef<RenderCancelTarget | null>(null)

  /** Evict a specific key from the L1 in-memory cache. Called externally when blobs are revoked. */
  const evictCache = useCallback((key: string) => {
    delete partsCacheRef.current[key]
  }, [])

  const handleGenerate = useCallback(async (forceRender: boolean = false, overridePayload: Record<string, unknown> | null = null, { automatic = false }: GenerateOptions = {}) => {
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
            const isGlb = p.blob.type === 'model/gltf-binary'
            const part: RenderPart = {
              type: p.type,
              url: URL.createObjectURL(p.blob),
              isGlb,
              // What these bytes ARE, stated on the part.
              //
              // Everything a cache round-trip returns is behind a `blob:` URL,
              // which carries no extension, so `handleDownloadStl` cannot read
              // the format off the URL the way it can for a server render. It
              // used to be told via a `#.stl` fragment appended below; that is
              // wrong twice over. `URL.revokeObjectURL` does not resolve past a
              // fragment (measured in Chromium 1169: revoking `blob:…#.stl`
              // leaves the base URL alive and fetchable), so the cleanup effect
              // in useProjectParams silently leaked every restored download
              // blob; and a part cached from a BROWSER render has no
              // `downloadBlob` at all, so it never got the marker and pressing
              // Download STL re-rendered geometry the page was displaying.
              //
              // `downloadBlob` is only ever written for the download format, and
              // the viewer blob is GLB or STL — the two the cache serialises.
              format: (p as { downloadBlob?: Blob }).downloadBlob
                ? undefined
                : (isGlb ? 'glb' : 'stl'),
            }
            if ((p as { downloadBlob?: Blob }).downloadBlob) {
              part.download_url = URL.createObjectURL((p as { downloadBlob: Blob }).downloadBlob)
              part.download_format = 'stl'
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
        // An AUTOMATIC render — the debounced on-load / param-change effect —
        // is one the visitor never asked for, so it must not seize the page.
        // The confirm dialog is a Radix alertdialog over a pointer-blocking
        // overlay, and for a cartridge whose default estimates over threshold
        // (gridfinity's cadquery `bin` is ~2 min) that meant every single load
        // of /project/<slug> opened a modal the visitor had to answer before
        // the UI would respond to anything. Say so without blocking and leave
        // the render to an explicit Generate, which still confirms below.
        if (automatic) {
          toast.info(
            t('toast.auto_render_skipped', { minutes: Math.max(1, Math.round(estimate / 60)) }),
            { id: SKIPPED_TOAST_ID, duration: SKIPPED_TOAST_DURATION_MS },
          )
          return
        }
        setPendingPayload(payload)
        setShowConfirmDialog(true)
        return
      }
    }

    setLoading(true)
    setProgress(INITIAL_PROGRESS)
    setProgressPhase(t("phase.compiling"))
    setLogs(prev => prev + `\n${t("log.generating")} (${mode})...`)

    // A new render supersedes whatever is still running. Aborting the fetch
    // only stops THIS page reading the stream — the server keeps rendering,
    // and against a single worker that abandoned job sits in front of the one
    // the user is now waiting for. Both halves are needed: abort the read, and
    // tell the server to stop. Taken synchronously, before the new stream can
    // publish its own identity into the same slot.
    abortControllerRef.current?.abort()
    cancelSupersededRender()
    activeTargetRef.current = null

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
        exportFormat,
        onJob: target => { activeTargetRef.current = target },
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
          ? t("tier.upgrade_cloud_render")
          : (e as Error).message;
        setLogs(prev => prev + `\n${t("log.error")} ${msg}`)

        if (isProGate) {
          triggerUpgradePrompt('CadQuery Cloud Rendering')
        }
      }
    } finally {
      abortControllerRef.current = null
      // The stream is over either way, so the target is spent: holding it would
      // let a later unload fire a cancel at a render that already finished.
      activeTargetRef.current = null
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
    activeTargetRef.current = null
    await cancelRender()
  }, [])

  /**
   * Tell the server when this page abandons a render.
   *
   * Nightly run #171 made ~95 navigations in 40 minutes and produced ZERO
   * `render-cancel` calls: nothing here ever cancelled on the way out, so every
   * abandoned render ran to completion against the single render worker while a
   * live user's render waited behind it. Starvation, not waste.
   *
   * `pagehide` rather than `beforeunload`: `beforeunload` is not fired for a
   * page entering the back/forward cache and is unreliable on mobile Safari,
   * where a backgrounded tab is simply discarded. `pagehide` fires in both
   * cases. The cleanup covers the other way a render is abandoned — the hook
   * unmounting on an in-app route change, where no page event fires at all.
   *
   * `cancelRenderOnUnload` is synchronous and returns false when nothing is in
   * flight, so this sends nothing on an ordinary navigation away from an idle
   * page. The target check keeps that decision readable at the call site.
   */
  useEffect(() => {
    const cancelIfRendering = () => {
      if (!activeTargetRef.current) return
      activeTargetRef.current = null
      cancelRenderOnUnload()
    }

    window.addEventListener('pagehide', cancelIfRendering)
    return () => {
      window.removeEventListener('pagehide', cancelIfRendering)
      cancelIfRendering()
    }
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
