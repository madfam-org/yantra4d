/**
 * Manages the debounced save-then-render cycle for the SCAD editor.
 *
 * When a file is edited, it saves via PUT /files/<path>, then triggers
 * the existing handleGenerate() from the render flow. The backend reads
 * the updated .scad from disk on next render — no render pipeline changes needed.
 */
import { useRef, useCallback } from 'react'
import { writeFile } from '../../services/domain/editorService'

const DEBOUNCE_MS = 800

interface EditorRenderOptions {
  slug: string
  handleGenerate: () => void
}

interface EditorRenderResult {
  saveAndRender: (path: string, content: string) => Promise<void>
  saveImmediate: (path: string, content: string) => Promise<void>
  cancel: () => void
}

export function useEditorRender({ slug, handleGenerate }: EditorRenderOptions): EditorRenderResult {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pendingRef = useRef<{ path: string; content: string } | null>(null)

  const saveAndRender = useCallback(async (path: string, content: string) => {
    // Cancel any pending debounce
    if (timerRef.current) clearTimeout(timerRef.current)

    // Store the latest content
    pendingRef.current = { path, content }

    timerRef.current = setTimeout(async () => {
      const { path: p, content: c } = pendingRef.current!
      try {
        await writeFile(slug, p, c)
        handleGenerate()
      } catch (e) {
        console.error('Editor save-and-render failed:', e)
      }
    }, DEBOUNCE_MS)
  }, [slug, handleGenerate])

  const saveImmediate = useCallback(async (path: string, content: string) => {
    if (timerRef.current) clearTimeout(timerRef.current)
    try {
      await writeFile(slug, path, content)
    } catch (e) {
      console.error('Editor save failed:', e)
      throw e
    }
  }, [slug])

  const cancel = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
  }, [])

  return { saveAndRender, saveImmediate, cancel }
}
