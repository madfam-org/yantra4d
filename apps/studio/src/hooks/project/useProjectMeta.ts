/**
 * Hook to fetch project.meta.json for a given project slug.
 * Returns the parsed meta object or null if not available.
 */
import { useState, useEffect } from 'react'
import { getApiBase } from '../../services/core/backendDetection'
import { apiFetch } from '../../services/core/apiClient'

interface ProjectMeta {
  [key: string]: unknown
}

export function useProjectMeta(slug: string | null): ProjectMeta | null {
  const [meta, setMeta] = useState<ProjectMeta | null>(null)

  useEffect(() => {
    if (!slug) return
    let cancelled = false

    apiFetch(`${getApiBase()}/api/projects/${slug}/meta`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (!cancelled) setMeta(data) })
      .catch(() => { if (!cancelled) setMeta(null) })

    return () => { cancelled = true }
  }, [slug])

  return meta
}
