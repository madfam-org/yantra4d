import { useCallback, useEffect, useState } from 'react'
import {
  loadPrerenderManifest,
  previewFromManifest,
  resolveModelsBase,
  type PrerenderCandidate,
  type PrerenderedPreviewInfo,
} from '../../lib/prerenderedPreview'

export interface PrerenderedPreviewState {
  /** The mesh to show now, or null (no manifest, slug not listed, every LOD failed). */
  current: (PrerenderCandidate & Omit<PrerenderedPreviewInfo, 'candidates'>) | null
  /** The viewer could not load `current.url`: try the next LOD, else show nothing. */
  reportFailure: (url: string) => void
}

/**
 * The prerendered default preview for `slug` (see lib/prerenderedPreview.ts).
 *
 * lod0 first, lod1 when lod0 is absent from the manifest or fails to load.
 * Failures are silent: the stage simply stays as it was.
 */
export function usePrerenderedPreview(slug: string | null | undefined): PrerenderedPreviewState {
  const [info, setInfo] = useState<{ slug: string; preview: PrerenderedPreviewInfo | null } | null>(null)
  const [failed, setFailed] = useState<ReadonlySet<string>>(() => new Set())

  useEffect(() => {
    if (!slug) return
    let active = true
    const base = resolveModelsBase()
    loadPrerenderManifest(base).then(manifest => {
      if (!active) return
      setInfo({ slug, preview: previewFromManifest(manifest, slug, base) })
      setFailed(new Set())
    })
    return () => { active = false }
  }, [slug])

  const reportFailure = useCallback((url: string) => {
    setFailed(prev => (prev.has(url) ? prev : new Set([...prev, url])))
  }, [])

  const preview = info && info.slug === slug ? info.preview : null
  const candidate = preview?.candidates.find(c => !failed.has(c.url)) ?? null
  return {
    current: preview && candidate
      ? { ...candidate, slug: preview.slug, commonsPin: preview.commonsPin, generated: preview.generated }
      : null,
    reportFailure,
  }
}
