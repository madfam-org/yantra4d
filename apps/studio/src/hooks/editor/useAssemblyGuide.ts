import { useState, useCallback, RefObject } from 'react'

interface AssemblyStep {
  visible_parts?: string[]
  highlight_parts?: string[]
  camera?: number[]
  camera_target?: number[]
}

interface ViewerRef {
  animateTo?: (position: number[], target: number[]) => void
}

interface AssemblyGuideResult {
  assemblyActive: boolean
  highlightedParts: string[]
  visibleParts: string[]
  assemblyEditorOpen: boolean
  setAssemblyEditorOpen: (open: boolean) => void
  handleHighlightParts: (parts: string[] | null) => void
  handleSetAssemblyCamera: (position: number[], target: number[]) => void
  handleAssemblyStepChange: (step: AssemblyStep | null) => void
}

/**
 * Manages assembly guide state: active flag, highlighted parts,
 * visible parts, editor toggle, and camera animation triggers.
 */
export function useAssemblyGuide(viewerRef: RefObject<ViewerRef | null>): AssemblyGuideResult {
  const [assemblyActive, setAssemblyActive] = useState(false)
  const [highlightedParts, setHighlightedParts] = useState<string[]>([])
  const [visibleParts, setVisibleParts] = useState<string[]>([])
  const [assemblyEditorOpen, setAssemblyEditorOpen] = useState(false)

  const handleHighlightParts = useCallback((parts: string[] | null) => {
    setHighlightedParts(parts || [])
  }, [])

  const handleSetAssemblyCamera = useCallback((position: number[], target: number[]) => {
    viewerRef.current?.animateTo?.(position, target)
  }, [viewerRef])

  const handleAssemblyStepChange = useCallback((step: AssemblyStep | null) => {
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
      handleSetAssemblyCamera(step.camera, step.camera_target || [])
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
