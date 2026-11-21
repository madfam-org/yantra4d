import { useCallback, useEffect, useState } from 'react'
import { fetchModeGraph } from '../../services/domain/graphViewService'
import type { ModeGraph } from '../../services/domain/graphViewService'

export type ModeGraphState =
  | { status: 'idle'; graph: null; error: null }
  | { status: 'loading'; graph: null; error: null }
  | { status: 'ready'; graph: ModeGraph; error: null }
  | { status: 'error'; graph: null; error: Error }

const IDLE: ModeGraphState = { status: 'idle', graph: null, error: null }
const LOADING: ModeGraphState = { status: 'loading', graph: null, error: null }

/**
 * Loaded graphs, per cartridge and mode, for the life of the page. Closing and
 * reopening the view, or switching modes back, costs no request; the server
 * still revalidates on the next page load (`Cache-Control: no-cache`).
 */
const cache = new Map<string, ModeGraph>()
const cacheKey = (slug: string, mode: string) => `${slug}\u0000${mode}`

/** Test seam: forget every loaded graph. */
export function clearModeGraphCache(): void {
  cache.clear()
}

/**
 * The graph document a mode declares, fetched only while `enabled` (the view is
 * open), so a visitor who never opens it costs no request.
 */
export function useModeGraph(slug: string | null | undefined, mode: string | null | undefined, enabled: boolean) {
  const key = slug && mode ? cacheKey(slug, mode) : null
  const cached = key ? cache.get(key) : undefined
  const [attempt, setAttempt] = useState(0)
  // The settled result of one request, tagged with what it answered: anything
  // else (a new mode, a retry) reads as loading until its own answer lands.
  const [state, setState] = useState<{ key: string | null; attempt: number; value: ModeGraphState }>(
    { key: null, attempt: -1, value: IDLE },
  )

  useEffect(() => {
    if (!enabled || !slug || !mode || !key || cache.has(key)) return
    const controller = new AbortController()
    fetchModeGraph(slug, mode, controller.signal)
      .then((graph) => {
        cache.set(key, graph)
        setState({ key, attempt, value: { status: 'ready', graph, error: null } })
      })
      .catch((error: Error) => {
        if (controller.signal.aborted) return
        setState({ key, attempt, value: { status: 'error', graph: null, error } })
      })
    return () => controller.abort()
  }, [enabled, slug, mode, key, attempt])

  const retry = useCallback(() => setAttempt((n) => n + 1), [])

  let value: ModeGraphState
  if (cached) value = { status: 'ready', graph: cached, error: null }
  else if (!enabled || !key) value = IDLE
  else if (state.key === key && state.attempt === attempt) value = state.value
  else value = LOADING
  return { ...value, retry }
}
