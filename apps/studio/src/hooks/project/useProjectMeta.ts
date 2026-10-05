/**
 * Hook to fetch project.meta.json for a given project slug.
 * Returns the parsed meta object or null if not available.
 *
 * The API adds two per-caller flags: `can_write` (whether the write routes —
 * editor, assembly steps, git — accept this caller for this cartridge) and
 * `is_owner`. They depend on who is signed in, so the meta is refetched when
 * the auth state changes.
 */
import { useState, useEffect } from 'react'
import { getApiBase } from '../../services/core/backendDetection'
import { apiFetch } from '../../services/core/apiClient'
import { useAuth } from '../../contexts/auth/AuthProvider'

export interface ProjectMeta {
  can_write?: boolean
  is_owner?: boolean
  [key: string]: unknown
}

/** True only when the API said this caller may write the cartridge. */
export function canWriteCartridge(meta: ProjectMeta | null): boolean {
  return meta?.can_write === true
}

export function useProjectMeta(slug: string | null): ProjectMeta | null {
  // The answer is kept with the slug it is for: after navigating from your own
  // fork to another cartridge, the previous cartridge's `can_write` must not
  // stand in for this one's while its meta loads.
  const [state, setState] = useState<{ slug: string | null; meta: ProjectMeta | null }>({ slug: null, meta: null })
  const { isAuthenticated } = useAuth()

  useEffect(() => {
    if (!slug) return
    let cancelled = false

    apiFetch(`${getApiBase()}/api/projects/${slug}/meta`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (!cancelled) setState({ slug, meta: data }) })
      .catch(() => { if (!cancelled) setState({ slug, meta: null }) })

    return () => { cancelled = true }
  }, [slug, isAuthenticated])

  return slug && state.slug === slug ? state.meta : null
}
