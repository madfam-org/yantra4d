/**
 * Save-then-render for the graph editor, on Studio's existing save path.
 *
 * The graph is written with the same `PUT /api/projects/<slug>/files/<path>`
 * the text editor uses (the server re-validates it with the transpiler), and
 * changed manifest bindings follow through `PUT .../manifest/bindings` — in
 * that order, because the server checks bindings against the graph ON DISK.
 * Then the existing render runs, which is the preview. It is forced: the
 * parameters did not change, so the client render caches would otherwise hand
 * back the pre-edit parts without asking the API. The project's source revision
 * is bumped too, so no later render can be answered by a pre-edit cache entry.
 *
 * Callers decide whether a project may be written at all: this hook is only
 * ever handed a fork or an imported repository, never a commons cartridge.
 */
import { useCallback, useRef, useState } from 'react'
import { updateGraphBindings, writeFile } from '../../services/domain/editorService'
import { bumpSourceRevision } from '../../services/cache/sourceRevision'
import type { GraphBindingsResponse } from '../../services/domain/editorService'

const DEBOUNCE_MS = 800

export type BindingChanges = Record<string, string | string[] | null>

export interface GraphPersistOptions {
  slug: string
  /** The render flow's generate; called with `true` (force) after a save. */
  handleGenerate: (forceRender?: boolean) => void
  /** Called with the server's binding map after bindings were saved. */
  onBindingsSaved?: (response: GraphBindingsResponse) => void
  /** Called with what was written, so the caller can mark that buffer clean. */
  onSaved?: (path: string, content: string) => void
}

export interface GraphPersistence {
  status: 'idle' | 'pending' | 'saving' | 'saved' | 'error'
  error: string | null
  /** Debounced: the latest call within the window wins. */
  schedule: (path: string, content: string, bindings: BindingChanges | null) => void
  /** Immediate; resolves true when everything was written. */
  saveNow: (path: string, content: string, bindings: BindingChanges | null) => Promise<boolean>
  cancel: () => void
}

export function useGraphPersistence({ slug, handleGenerate, onBindingsSaved, onSaved }: GraphPersistOptions): GraphPersistence {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [status, setStatus] = useState<GraphPersistence['status']>('idle')
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(async (path: string, content: string, bindings: BindingChanges | null) => {
    setStatus('saving')
    setError(null)
    try {
      await writeFile(slug, path, content)
      if (bindings && Object.keys(bindings).length > 0) {
        const saved = await updateGraphBindings(slug, bindings)
        onBindingsSaved?.(saved)
      }
      bumpSourceRevision(slug)
      setStatus('saved')
      onSaved?.(path, content)
      handleGenerate(true)
      return true
    } catch (e) {
      setStatus('error')
      setError((e as Error).message)
      return false
    }
  }, [slug, handleGenerate, onBindingsSaved, onSaved])

  const cancel = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = null
  }, [])

  const schedule = useCallback((path: string, content: string, bindings: BindingChanges | null) => {
    cancel()
    setStatus('pending')
    timerRef.current = setTimeout(() => {
      timerRef.current = null
      void run(path, content, bindings)
    }, DEBOUNCE_MS)
  }, [cancel, run])

  const saveNow = useCallback((path: string, content: string, bindings: BindingChanges | null) => {
    cancel()
    return run(path, content, bindings)
  }, [cancel, run])

  return { status, error, schedule, saveNow, cancel }
}
