import { useState, useEffect, useRef, useCallback } from 'react'
import { renderParts } from '../../services/engine/renderService'
import * as idbCache from '../../services/cache/renderCache'
import { inferPreviewHint } from '../../lib/previewHintInference'
import { requestIdleCallback, cancelIdleCallback } from '../../lib/idleCallback'

const IDLE_DELAY_MS = 3000
const MAX_PRERENDER_PARAMS = 3

interface ParamDef {
  id: string
  type: string
  min?: number
  max?: number
  label?: Record<string, string>
  preview_hint?: { type: string; axis?: string; affected_parts?: string[] }
  [key: string]: unknown
}

interface Manifest {
  parameters?: ParamDef[]
  modes?: Array<{ id: string; parts: string[]; [key: string]: unknown }>
  parts?: Array<{ id: string; render_mode: number; [key: string]: unknown }>
  [key: string]: unknown
}

interface RenderPart {
  type: string
  url?: string
  blob?: Blob
  isGlb?: boolean
  [key: string]: unknown
}

interface CachedVariantParts {
  min?: RenderPart[]
  max?: RenderPart[]
}

interface UseParameterPreviewCacheOptions {
  manifest: Manifest
  mode: string
  params: Record<string, unknown>
  parts: RenderPart[]
  loading: boolean
  project?: string
}

interface UseParameterPreviewCacheResult {
  cachedVariants: Map<string, CachedVariantParts>
  preRenderStatus: string
}

/**
 * After a render completes, idle-pre-render the top dimensional params
 * at their min and max values into IDB. On hover, if cached variants exist,
 * they are returned for ghost geometry overlay rendering.
 */
export function useParameterPreviewCache({
  manifest, mode, params, parts, loading, project
}: UseParameterPreviewCacheOptions): UseParameterPreviewCacheResult {
  const [cachedVariants, setCachedVariants] = useState<Map<string, CachedVariantParts>>(new Map())
  const [preRenderStatus, setPreRenderStatus] = useState('idle')
  const abortRef = useRef<AbortController | null>(null)
  const lastRenderKeyRef = useRef<string | null>(null)

  // Identify dimensional params worth pre-rendering
  const getDimensionalParams = useCallback((): ParamDef[] => {
    if (!manifest?.parameters) return []
    return manifest.parameters
      .filter(p => {
        const hint = inferPreviewHint(p, manifest as Parameters<typeof inferPreviewHint>[1], mode)
        return hint.type === 'axis_scale' && p.min != null && p.max != null
      })
      .slice(0, MAX_PRERENDER_PARAMS)
  }, [manifest, mode])

  // After render completes + idle timeout, check/pre-render variants
  useEffect(() => {
    if (!parts.length || loading) return

    // Invalidate on param/mode change
    const renderKey = JSON.stringify({ mode, params })
    if (renderKey === lastRenderKeyRef.current) return
    lastRenderKeyRef.current = renderKey

    // Cancel any in-flight pre-renders
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const idleId = requestIdleCallback(async () => {
      if (controller.signal.aborted) return
      const hotParams = getDimensionalParams()
      if (!hotParams.length) { setPreRenderStatus('done'); return }

      setPreRenderStatus('checking')
      const newVariants = new Map<string, CachedVariantParts>()

      for (const paramDef of hotParams) {
        if (controller.signal.aborted) break
        const pid = paramDef.id
        const variants: CachedVariantParts = {}

        for (const bound of ['min', 'max'] as const) {
          const boundValue = paramDef[bound]
          if (boundValue === params[pid]) continue // skip if current value IS the bound
          const variantParams = { ...params, [pid]: boundValue }
          const idbKey = await idbCache.makeCacheKey(project || '', mode, variantParams, 'glb')
          const cached = await idbCache.get(idbKey)

          if (cached) {
            // Cache hit — restore blob URLs
            variants[bound] = cached.map(p => ({
              type: p.type,
              url: URL.createObjectURL(p.blob),
              isGlb: p.blob.type === 'model/gltf-binary',
            }))
          }
        }

        if (Object.keys(variants).length > 0) {
          newVariants.set(pid, variants)
        }
      }

      setCachedVariants(newVariants)
      setPreRenderStatus('done')

      // Background pre-render missing variants (one at a time)
      if (controller.signal.aborted) return
      setPreRenderStatus('rendering')

      for (const paramDef of hotParams) {
        if (controller.signal.aborted) break
        const pid = paramDef.id

        for (const bound of ['min', 'max'] as const) {
          if (controller.signal.aborted) break
          const boundValue = paramDef[bound]
          if (boundValue === params[pid]) continue
          const existing = newVariants.get(pid)?.[bound]
          if (existing) continue // already cached

          const variantParams = { ...params, [pid]: boundValue }
          try {
            const result = await renderParts(mode, variantParams, manifest as unknown as Parameters<typeof renderParts>[2], {
              project,
              abortSignal: controller.signal,
            })
            // Cache in IDB
            const idbKey = await idbCache.makeCacheKey(project || '', mode, variantParams, 'glb')
            await idbCache.put(idbKey, result)

            // Update state
            setCachedVariants(prev => {
              const next = new Map(prev)
              const entry = next.get(pid) || {}
              entry[bound] = result as unknown as RenderPart[]
              next.set(pid, entry)
              return next
            })
          } catch {
            // Background render failed — non-fatal, skip
          }
        }
      }

      setPreRenderStatus('done')
    }, { timeout: IDLE_DELAY_MS + 5000 })

    return () => {
      cancelIdleCallback(idleId)
      controller.abort()
    }
  }, [parts.length, loading, mode, params, manifest, project, getDimensionalParams])

  // Cleanup blob URLs on unmount or variant change
  useEffect(() => {
    return () => {
      for (const [, variants] of cachedVariants) {
        for (const bound of ['min', 'max'] as const) {
          variants[bound]?.forEach(p => {
            if (p.url?.startsWith('blob:')) URL.revokeObjectURL(p.url)
          })
        }
      }
    }
  }, [cachedVariants])

  return { cachedVariants, preRenderStatus }
}
