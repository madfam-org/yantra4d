import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

vi.mock('../lib/downloadUtils', () => ({
  downloadDataUrl: vi.fn(),
  downloadZipFromData: vi.fn().mockResolvedValue(),
}))

import { useImageExport } from './useImageExport'
import { downloadDataUrl, downloadZipFromData } from '../lib/downloadUtils'

beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers()
})

describe('useImageExport', () => {
  const mockViewerRef = {
    current: {
      setCameraView: vi.fn(),
      captureSnapshot: vi.fn().mockReturnValue('data:image/png;base64,AAAA'),
    }
  }

  it('handleExportImage captures and downloads snapshot', async () => {
    const { result } = renderHook(() => useImageExport({
      viewerRef: mockViewerRef,
      projectSlug: 'proj',
      mode: 'unit',
      parts: [{ type: 'main' }],
      setLogs: vi.fn(),
      t: (k) => k,
      cameraViews: [{ id: 'front' }],
    }))

    act(() => {
      result.current.handleExportImage('front')
    })

    expect(mockViewerRef.current.setCameraView).toHaveBeenCalledWith('front')

    // Advance past CAMERA_SETTLE_MS (100ms)
    act(() => {
      vi.advanceTimersByTime(150)
    })

    expect(mockViewerRef.current.captureSnapshot).toHaveBeenCalled()
    expect(downloadDataUrl).toHaveBeenCalledWith(
      'data:image/png;base64,AAAA',
      'proj_unit_front.png'
    )
  })

  it('handleExportImage does nothing without viewer ref', () => {
    const { result } = renderHook(() => useImageExport({
      viewerRef: { current: null },
      projectSlug: 'proj',
      mode: 'unit',
      parts: [],
      setLogs: vi.fn(),
      t: (k) => k,
      cameraViews: [],
    }))

    act(() => {
      result.current.handleExportImage('front')
    })

    expect(downloadDataUrl).not.toHaveBeenCalled()
  })

  it('handleExportAllViews captures all views and creates zip', async () => {
    vi.useRealTimers()
    const { result } = renderHook(() => useImageExport({
      viewerRef: mockViewerRef,
      projectSlug: 'proj',
      mode: 'unit',
      parts: [{ type: 'main' }],
      setLogs: vi.fn(),
      t: (k) => k,
      cameraViews: [{ id: 'front' }, { id: 'top' }],
    }))

    await act(async () => {
      await result.current.handleExportAllViews()
    })

    expect(mockViewerRef.current.setCameraView).toHaveBeenCalledWith('front')
    expect(mockViewerRef.current.setCameraView).toHaveBeenCalledWith('top')
    expect(downloadZipFromData).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ filename: 'proj_unit_front.png' }),
        expect.objectContaining({ filename: 'proj_unit_top.png' }),
      ]),
      'proj_unit_all_views.zip'
    )
    vi.useFakeTimers()
  })

  it('handleExportAllViews handles error', async () => {
    vi.useRealTimers()
    const setLogs = vi.fn()
    const badViewer = {
      current: {
        setCameraView: vi.fn(),
        captureSnapshot: vi.fn().mockImplementation(() => { throw new Error('fail') }),
      }
    }
    const { result } = renderHook(() => useImageExport({
      viewerRef: badViewer,
      projectSlug: 'proj',
      mode: 'unit',
      parts: [{ type: 'main' }],
      setLogs,
      t: (k) => k,
      cameraViews: [{ id: 'front' }],
    }))
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    await act(async () => {
      await result.current.handleExportAllViews()
    })
    expect(setLogs).toHaveBeenCalled()
    spy.mockRestore()
    vi.useFakeTimers()
  })

  it('handleExportAllViews does nothing with empty parts', async () => {
    const { result } = renderHook(() => useImageExport({
      viewerRef: mockViewerRef,
      projectSlug: 'proj',
      mode: 'unit',
      parts: [],
      setLogs: vi.fn(),
      t: (k) => k,
      cameraViews: [{ id: 'front' }],
    }))

    await act(async () => {
      await result.current.handleExportAllViews()
    })

    expect(downloadZipFromData).not.toHaveBeenCalled()
  })
})
