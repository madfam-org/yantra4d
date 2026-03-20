import { useState, useCallback, useRef, RefObject } from 'react'
import { toast } from 'sonner'
import { apiFetch } from '../../services/core/apiClient'

interface AssemblyStep {
  step: number
  label: Record<string, string>
  notes: Record<string, string>
  visible_parts: string[]
  highlight_parts: string[]
  camera: number[] | null
  camera_target: number[] | null
  [key: string]: unknown
}

interface Manifest {
  assembly_steps?: AssemblyStep[]
  [key: string]: unknown
}

interface ViewerRef {
  getCameraState?: () => { position: number[]; target: number[] }
}

interface AssemblyEditorResult {
  steps: AssemblyStep[]
  selectedIndex: number
  selectedStep: AssemblyStep | null
  isDirty: boolean
  saving: boolean
  selectStep: (index: number) => void
  addStep: () => void
  removeStep: (index: number) => void
  updateStep: (index: number, updates: Partial<AssemblyStep>) => void
  reorderStep: (fromIndex: number, direction: number) => void
  captureCamera: () => void
  save: () => Promise<void>
  discard: () => void
}

/**
 * Hook for managing assembly step editing state.
 * Provides CRUD operations on steps plus save/discard.
 */
export function useAssemblyEditor(
  manifest: Manifest | null,
  projectSlug: string,
  onStepChange?: ((step: AssemblyStep | null) => void) | null,
  viewerRef?: RefObject<ViewerRef | null>
): AssemblyEditorResult {
  const [steps, setSteps] = useState<AssemblyStep[]>(() => manifest?.assembly_steps || [])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [isDirty, setIsDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const originalRef = useRef<AssemblyStep[]>(manifest?.assembly_steps || [])

  const selectedStep = steps[selectedIndex] || null

  const notifyViewer = useCallback((step: AssemblyStep | null) => {
    onStepChange?.(step)
  }, [onStepChange])

  const selectStep = useCallback((index: number) => {
    const clamped = Math.max(0, Math.min(steps.length - 1, index))
    setSelectedIndex(clamped)
    notifyViewer(steps[clamped] || null)
  }, [steps, notifyViewer])

  const addStep = useCallback(() => {
    const newStep: AssemblyStep = {
      step: steps.length + 1,
      label: { en: '', es: '' },
      notes: { en: '', es: '' },
      visible_parts: [],
      highlight_parts: [],
      camera: null,
      camera_target: null,
    }

    // Auto-capture camera if viewer is available
    const cameraState = viewerRef?.current?.getCameraState?.()
    if (cameraState) {
      newStep.camera = cameraState.position.map(v => Math.round(v * 10) / 10)
      newStep.camera_target = cameraState.target.map(v => Math.round(v * 10) / 10)
    }

    const newSteps = [...steps, newStep]
    setSteps(newSteps)
    setSelectedIndex(newSteps.length - 1)
    setIsDirty(true)
    notifyViewer(newStep)
  }, [steps, viewerRef, notifyViewer])

  const removeStep = useCallback((index: number) => {
    if (steps.length <= 1) return
    const newSteps = steps.filter((_, i) => i !== index).map((s, i) => ({ ...s, step: i + 1 }))
    setSteps(newSteps)
    const newIndex = Math.min(index, newSteps.length - 1)
    setSelectedIndex(newIndex)
    setIsDirty(true)
    notifyViewer(newSteps[newIndex] || null)
  }, [steps, notifyViewer])

  const updateStep = useCallback((index: number, updates: Partial<AssemblyStep>) => {
    setSteps(prev => {
      const newSteps = [...prev]
      newSteps[index] = { ...newSteps[index], ...updates }
      return newSteps
    })
    setIsDirty(true)
  }, [])

  const reorderStep = useCallback((fromIndex: number, direction: number) => {
    const toIndex = fromIndex + direction
    if (toIndex < 0 || toIndex >= steps.length) return
    const newSteps = [...steps]
    const [moved] = newSteps.splice(fromIndex, 1)
    newSteps.splice(toIndex, 0, moved)
    // Re-number
    const renumbered = newSteps.map((s, i) => ({ ...s, step: i + 1 }))
    setSteps(renumbered)
    setSelectedIndex(toIndex)
    setIsDirty(true)
  }, [steps])

  const captureCamera = useCallback(() => {
    const cameraState = viewerRef?.current?.getCameraState?.()
    if (!cameraState) return
    updateStep(selectedIndex, {
      camera: cameraState.position.map(v => Math.round(v * 10) / 10),
      camera_target: cameraState.target.map(v => Math.round(v * 10) / 10),
    })
  }, [viewerRef, selectedIndex, updateStep])

  const save = useCallback(async () => {
    setSaving(true)
    try {
      await apiFetch(`/api/projects/${projectSlug}/manifest/assembly-steps`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assembly_steps: steps }),
      })
      originalRef.current = steps
      setIsDirty(false)
      toast.success('Assembly steps saved')
    } catch (err) {
      toast.error(`Save failed: ${(err as Error).message}`)
    } finally {
      setSaving(false)
    }
  }, [steps, projectSlug])

  const discard = useCallback(() => {
    setSteps(originalRef.current)
    setSelectedIndex(0)
    setIsDirty(false)
    notifyViewer(originalRef.current[0] || null)
  }, [notifyViewer])

  return {
    steps,
    selectedIndex,
    selectedStep,
    isDirty,
    saving,
    selectStep,
    addStep,
    removeStep,
    updateStep,
    reorderStep,
    captureCamera,
    save,
    discard,
  }
}
