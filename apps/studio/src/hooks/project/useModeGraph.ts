import { useCallback, useEffect, useState } from 'react'
import { fetchModeGraph } from '../../services/domain/graphViewService'
import type { ModeGraph } from '../../services/domain/graphViewService'
import { sourceRevision } from '../../services/cache/sourceRevision'

export type ModeGraphState =
  | { status: 'idle'; graph: null; error: null }
  | { status: 'loading'; graph: null; error: null }
  | { status: 'ready'; graph: ModeGraph; error: null }
  | { status: 'error'; graph: null; error: Error }

const IDLE: ModeGraphState = { status: 'idle', graph: null, error: null }
const LOADING: ModeGraphState = { status: 'loading', graph: null, error: null }

interface Settled {
  key: string | null
  attempt: number
  value: ModeGraphState
}

/**
 * The graph document a mode declares, fetched only while `enabled` (the view is
 * open), so a visitor who never opens it costs no request.
 *
 * A loaded graph is kept while the caller stays mounted, so closing and
 * reopening the view costs nothing. The key carries the project's source
 * revision (`services/cache/sourceRevision`), which a graph save bumps: after
 * an owner saves a fork's graph, reopening the view loads the saved one.
 * Nothing is kept across mounts or in module state; the server revalidates
 * every load (`Cache-Control: no-cache` + ETag).
 */
export function useModeGraph(slug: string | null | undefined, mode: string | null | undefined, enabled: boolean) {
  const key = slug && mode ? `${slug}\u0000${mode}\u0000${sourceRevision(slug)}` : null
  const [attempt, setAttempt] = useState(0)
  // The settled result of one request, tagged with what it answered: anything
  // else (another mode, a newer source revision, a retry) reads as loading
  // until its own answer lands.
  const [settled, setSettled] = useState<Settled>({ key: null, attempt: -1, value: IDLE })
  const isLoaded = settled.key === key && settled.value.status === 'ready'

  // Reopening the view after a failure is a retry, not a second look at the error.
  const [wasEnabled, setWasEnabled] = useState(enabled)
  if (wasEnabled !== enabled) {
    setWasEnabled(enabled)
    if (enabled && settled.key === key && settled.value.status === 'error') setAttempt((n) => n + 1)
  }

  useEffect(() => {
    if (!enabled || !slug || !mode || !key || isLoaded) return
    const controller = new AbortController()
    fetchModeGraph(slug, mode, controller.signal)
      .then((graph) => setSettled({ key, attempt, value: { status: 'ready', graph, error: null } }))
      .catch((error: Error) => {
        if (controller.signal.aborted) return
        setSettled({ key, attempt, value: { status: 'error', graph: null, error } })
      })
    return () => controller.abort()
  }, [enabled, slug, mode, key, attempt, isLoaded])

  const retry = useCallback(() => setAttempt((n) => n + 1), [])

  let value: ModeGraphState
  if (isLoaded) value = settled.value
  else if (!enabled || !key) value = IDLE
  else if (settled.key === key && settled.attempt === attempt) value = settled.value
  else value = LOADING
  return { ...value, retry }
}
