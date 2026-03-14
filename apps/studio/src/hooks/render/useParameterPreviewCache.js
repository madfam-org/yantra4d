import { useState, useEffect, useRef, useCallback } from 'react'
import { renderParts } from '../../services/engine/renderService'
import * as idbCache from '../../services/cache/renderCache'
import { inferPreviewHint } from '../../lib/previewHintInference'
import { requestIdleCallback, cancelIdleCallback } from '../../lib/idleCallback'

const IDLE_DELAY_MS = 3000
const MAX_PRERENDER_PARAMS = 3

/**
 * After a render completes, idle-pre-render the top dimensional params
 * at their min and max values into IDB. On hover, if cached variants exist,
 * they are returned for ghost geometry overlay rendering.
 *
 * @param {Object} opts
 * @param {Object} opts.manifest - Project manifest
 * @param {string} opts.mode - Current mode ID
 * @param {Object} opts.params - Current parameter values
 * @param {Array} opts.parts - Current rendered parts (non-empty = render complete)
 * @param {boolean} opts.loading - Whether a user render is in progress
 * @param {string} opts.project - Project slug
 * @returns {{ cachedVariants: Map, preRenderStatus: string }}
 */
export function useParameterPreviewCache({ manifest, mode, params, parts, loading, project }) {
  const [cachedVariants, setCachedVariants] = useState(new Map())
  const [preRenderStatus, setPreRenderStatus] = useState('idle')
  const abortRef = useRef(null)
  const lastRenderKeyRef = useRef(null)

  // Identify dimensional params worth pre-rendering
  const getDimensionalParams = useCallback(() => {
    if (!manifest?.parameters) return []
    return manifest.parameters
      .filter(p => {
        const hint = inferPreviewHint(p, manifest, mode)
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
      const newVariants = new Map()

      for (const paramDef of hotParams) {
        if (controller.signal.aborted) break
        const pid = paramDef.id
        const variants = {}

        for (const bound of ['min', 'max']) {
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

        for (const bound of ['min', 'max']) {
          if (controller.signal.aborted) break
          const boundValue = paramDef[bound]
          if (boundValue === params[pid]) continue
          const existing = newVariants.get(pid)?.[bound]
          if (existing) continue // already cached

          const variantParams = { ...params, [pid]: boundValue }
          try {
            const result = await renderParts(mode, variantParams, manifest, {
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
              entry[bound] = result
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
        for (const bound of ['min', 'max']) {
          variants[bound]?.forEach(p => {
            if (p.url?.startsWith('blob:')) URL.revokeObjectURL(p.url)
          })
        }
      }
    }
  }, [cachedVariants])

  return { cachedVariants, preRenderStatus }
}
