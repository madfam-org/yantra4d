import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

vi.mock('../../services/core/apiClient', () => ({
  apiFetch: vi.fn().mockResolvedValue({ ok: true }),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

import { useAssemblyEditor } from './useAssemblyEditor'
import { apiFetch } from '../../services/core/apiClient'
import { toast } from 'sonner'

const baseManifest = {
  assembly_steps: [
    { step: 1, label: { en: 'Step 1' }, notes: { en: '' }, visible_parts: ['bottom'], highlight_parts: [], camera: null, camera_target: null },
    { step: 2, label: { en: 'Step 2' }, notes: { en: '' }, visible_parts: ['top'], highlight_parts: [], camera: null, camera_target: null },
  ],
}

describe('useAssemblyEditor', () => {
  beforeEach(() => vi.clearAllMocks())

  it('initializes with manifest steps', () => {
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', vi.fn(), { current: null }))
    expect(result.current.steps).toHaveLength(2)
    expect(result.current.selectedIndex).toBe(0)
    expect(result.current.isDirty).toBe(false)
  })

  it('initializes empty when no manifest', () => {
    const { result } = renderHook(() => useAssemblyEditor(null, 'test', vi.fn(), { current: null }))
    expect(result.current.steps).toEqual([])
  })

  it('selectStep clamps index', () => {
    const onStep = vi.fn()
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', onStep, { current: null }))
    act(() => result.current.selectStep(99))
    expect(result.current.selectedIndex).toBe(1) // clamped to max
    act(() => result.current.selectStep(-5))
    expect(result.current.selectedIndex).toBe(0) // clamped to 0
  })

  it('addStep appends and selects new step', () => {
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', vi.fn(), { current: null }))
    act(() => result.current.addStep())
    expect(result.current.steps).toHaveLength(3)
    expect(result.current.selectedIndex).toBe(2)
    expect(result.current.isDirty).toBe(true)
  })

  it('addStep captures camera when available', () => {
    const viewerRef = { current: { getCameraState: () => ({ position: [1.123, 2.456, 3.789], target: [0, 0, 0] }) } }
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', vi.fn(), viewerRef))
    act(() => result.current.addStep())
    const newStep = result.current.steps[2]
    expect(newStep.camera).toEqual([1.1, 2.5, 3.8])
    expect(newStep.camera_target).toEqual([0, 0, 0])
  })

  it('removeStep removes and renumbers', () => {
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', vi.fn(), { current: null }))
    act(() => result.current.removeStep(0))
    expect(result.current.steps).toHaveLength(1)
    expect(result.current.steps[0].step).toBe(1)
    expect(result.current.isDirty).toBe(true)
  })

  it('removeStep does nothing when only one step', () => {
    const manifest = { assembly_steps: [{ step: 1, label: { en: 'Only' } }] }
    const { result } = renderHook(() => useAssemblyEditor(manifest, 'test', vi.fn(), { current: null }))
    act(() => result.current.removeStep(0))
    expect(result.current.steps).toHaveLength(1)
  })

  it('updateStep modifies step', () => {
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', vi.fn(), { current: null }))
    act(() => result.current.updateStep(0, { label: { en: 'Updated' } }))
    expect(result.current.steps[0].label.en).toBe('Updated')
    expect(result.current.isDirty).toBe(true)
  })

  it('reorderStep swaps steps', () => {
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', vi.fn(), { current: null }))
    act(() => result.current.reorderStep(0, 1))
    expect(result.current.steps[0].label.en).toBe('Step 2')
    expect(result.current.steps[1].label.en).toBe('Step 1')
    expect(result.current.selectedIndex).toBe(1)
  })

  it('reorderStep does nothing for out-of-bounds', () => {
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', vi.fn(), { current: null }))
    act(() => result.current.reorderStep(0, -1))
    expect(result.current.steps[0].label.en).toBe('Step 1') // unchanged
  })

  it('captureCamera updates selected step', () => {
    const viewerRef = { current: { getCameraState: () => ({ position: [10, 20, 30], target: [1, 2, 3] }) } }
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', vi.fn(), viewerRef))
    act(() => result.current.captureCamera())
    expect(result.current.steps[0].camera).toEqual([10, 20, 30])
  })

  it('captureCamera does nothing without viewer', () => {
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', vi.fn(), { current: null }))
    act(() => result.current.captureCamera())
    expect(result.current.steps[0].camera).toBeNull()
  })

  it('save calls API and resets dirty', async () => {
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', vi.fn(), { current: null }))
    act(() => result.current.addStep())
    await act(async () => result.current.save())
    expect(apiFetch).toHaveBeenCalledWith('/api/projects/test/manifest/assembly-steps', expect.objectContaining({ method: 'PUT' }))
    expect(result.current.isDirty).toBe(false)
    expect(toast.success).toHaveBeenCalled()
  })

  it('save shows error on failure', async () => {
    apiFetch.mockRejectedValueOnce(new Error('Network'))
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', vi.fn(), { current: null }))
    act(() => result.current.addStep())
    await act(async () => result.current.save())
    expect(toast.error).toHaveBeenCalled()
  })

  it('discard restores original steps', () => {
    const { result } = renderHook(() => useAssemblyEditor(baseManifest, 'test', vi.fn(), { current: null }))
    act(() => result.current.addStep())
    expect(result.current.steps).toHaveLength(3)
    act(() => result.current.discard())
    expect(result.current.steps).toHaveLength(2)
    expect(result.current.isDirty).toBe(false)
  })
})
