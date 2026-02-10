import { useState, useCallback } from 'react'

/**
 * Manages assembly guide state: active flag, highlighted parts,
 * visible parts, editor toggle, and camera animation triggers.
 */
export function useAssemblyGuide(viewerRef) {
  const [assemblyActive, setAssemblyActive] = useState(false)
  const [highlightedParts, setHighlightedParts] = useState([])
  const [visibleParts, setVisibleParts] = useState([])
  const [assemblyEditorOpen, setAssemblyEditorOpen] = useState(false)

  const handleHighlightParts = useCallback((parts) => {
    setHighlightedParts(parts || [])
  }, [])

  const handleSetAssemblyCamera = useCallback((position, target) => {
    viewerRef.current?.animateTo?.(position, target)
  }, [viewerRef])

  const handleAssemblyStepChange = useCallback((step) => {
    if (!step) {
      setAssemblyActive(false)
      setHighlightedParts([])
      setVisibleParts([])
      return
    }
    setAssemblyActive(true)
    setVisibleParts(step.visible_parts || [])
    setHighlightedParts(step.highlight_parts || [])
    if (step.camera) {
      handleSetAssemblyCamera(step.camera, step.camera_target)
    }
  }, [handleSetAssemblyCamera])

  return {
    assemblyActive,
    highlightedParts,
    visibleParts,
    assemblyEditorOpen,
    setAssemblyEditorOpen,
    handleHighlightParts,
    handleSetAssemblyCamera,
    handleAssemblyStepChange,
  }
}
