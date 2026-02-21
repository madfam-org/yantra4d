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

export function useEditorRender({ slug, handleGenerate }) {
  const timerRef = useRef(null)
  const pendingRef = useRef(null)

  const saveAndRender = useCallback(async (path, content) => {
    // Cancel any pending debounce
    if (timerRef.current) clearTimeout(timerRef.current)

    // Store the latest content
    pendingRef.current = { path, content }

    timerRef.current = setTimeout(async () => {
      const { path: p, content: c } = pendingRef.current
      try {
        await writeFile(slug, p, c)
        handleGenerate()
      } catch (e) {
        console.error('Editor save-and-render failed:', e)
      }
    }, DEBOUNCE_MS)
  }, [slug, handleGenerate])

  const saveImmediate = useCallback(async (path, content) => {
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
