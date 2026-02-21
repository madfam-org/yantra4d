import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))
vi.mock('../lib/downloadUtils', () => ({
  downloadFile: vi.fn(),
  downloadZip: vi.fn().mockResolvedValue(),
}))
vi.mock('../services/engine/verifyService', () => ({
  verify: vi.fn(),
}))

import { useProjectActions } from './useProjectActions'
import { toast } from 'sonner'
import { downloadFile, downloadZip } from '../lib/downloadUtils'
import { verify } from '../services/engine/verifyService'

const t = (key) => key

function renderActions(overrides = {}) {
  const defaults = {
    parts: [],
    mode: 'basic',
    projectSlug: 'test-project',
    t,
    setLogs: vi.fn(),
    getDefaultParams: vi.fn(() => ({ x: 1 })),
    getDefaultColors: vi.fn(() => ['#fff']),
    setParams: vi.fn(),
    setColors: vi.fn(),
    setWireframe: vi.fn(),
    copyShareUrl: vi.fn().mockResolvedValue(true),
    handleExportImage: vi.fn(),
    handleExportAllViews: vi.fn(),
  }
  const opts = { ...defaults, ...overrides }
  return { ...renderHook(() => useProjectActions(opts)), opts }
}

describe('useProjectActions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ---------- handleShare ----------
  describe('handleShare', () => {
    it('copies share URL and shows success toast', async () => {
      const { result } = renderActions()
      await act(async () => {
        await result.current.handleShare()
      })
      expect(toast.success).toHaveBeenCalledWith('act.share_copied', { duration: 2000 })
    })

    it('sets shareToast temporarily on success', async () => {
      vi.useFakeTimers()
      const { result } = renderActions()
      await act(async () => {
        await result.current.handleShare()
      })
      expect(result.current.shareToast).toBe(true)
      act(() => { vi.advanceTimersByTime(2500) })
      expect(result.current.shareToast).toBe(false)
      vi.useRealTimers()
    })

    it('shows error toast when copy fails', async () => {
      const { result } = renderActions({
        copyShareUrl: vi.fn().mockResolvedValue(false),
      })
      await act(async () => {
        await result.current.handleShare()
      })
      expect(toast.error).toHaveBeenCalledWith('toast.share_failed')
    })
  })

  // ---------- handleVerify ----------
  describe('handleVerify', () => {
    it('calls verify and appends passed log', async () => {
      verify.mockResolvedValue({ passed: true, output: 'all good' })
      const setLogs = vi.fn()
      const parts = [{ url: 'u1', type: 'a' }]
      const { result } = renderActions({ parts, setLogs })
      await act(async () => {
        await result.current.handleVerify()
      })
      expect(verify).toHaveBeenCalledWith(parts, 'basic', 'test-project')
      // setLogs called multiple times (start, report, result)
      expect(setLogs).toHaveBeenCalled()
    })

    it('appends fail log when verify fails', async () => {
      verify.mockResolvedValue({ passed: false, output: 'failure' })
      const setLogs = vi.fn()
      const { result } = renderActions({ setLogs })
      await act(async () => {
        await result.current.handleVerify()
      })
      // last setLogs call should include fail key
      const lastCall = setLogs.mock.calls[setLogs.mock.calls.length - 1]
      const updater = lastCall[0]
      expect(typeof updater).toBe('function')
      expect(updater('')).toContain('log.fail')
    })

    it('handles verify error gracefully', async () => {
      verify.mockRejectedValue(new Error('network'))
      const setLogs = vi.fn()
      const { result } = renderActions({ setLogs })
      await act(async () => {
        await result.current.handleVerify()
      })
      const lastCall = setLogs.mock.calls[setLogs.mock.calls.length - 1]
      const updater = lastCall[0]
      expect(updater('')).toContain('network')
    })
  })

  // ---------- handleDownloadStl ----------
  describe('handleDownloadStl', () => {
    it('is a no-op when parts is empty', async () => {
      const { result } = renderActions({ parts: [] })
      await act(async () => {
        await result.current.handleDownloadStl()
      })
      expect(downloadFile).not.toHaveBeenCalled()
      expect(downloadZip).not.toHaveBeenCalled()
    })

    it('downloads single part directly', async () => {
      const parts = [{ url: 'http://file.stl', type: 'body' }]
      const { result } = renderActions({ parts })
      await act(async () => {
        await result.current.handleDownloadStl()
      })
      expect(downloadFile).toHaveBeenCalledWith(
        'http://file.stl',
        'test-project_basic_body.stl'
      )
    })

    it('downloads multiple parts as zip', async () => {
      const parts = [
        { url: 'http://a.stl', type: 'top' },
        { url: 'http://b.stl', type: 'bottom' },
      ]
      const setLogs = vi.fn()
      const { result } = renderActions({ parts, setLogs })
      await act(async () => {
        await result.current.handleDownloadStl()
      })
      expect(downloadZip).toHaveBeenCalled()
      const zipCall = downloadZip.mock.calls[0]
      expect(zipCall[0]).toHaveLength(2)
      expect(zipCall[1]).toBe('test-project_basic_all_parts.zip')
    })

    it('handles zip download error', async () => {
      downloadZip.mockRejectedValue(new Error('zip fail'))
      const parts = [
        { url: 'http://a.stl', type: 'top' },
        { url: 'http://b.stl', type: 'bottom' },
      ]
      const setLogs = vi.fn()
      const { result } = renderActions({ parts, setLogs })
      await act(async () => {
        await result.current.handleDownloadStl()
      })
      const lastCall = setLogs.mock.calls[setLogs.mock.calls.length - 1]
      const updater = lastCall[0]
      expect(updater('')).toContain('zip fail')
    })
  })

  // ---------- handleReset ----------
  describe('handleReset', () => {
    it('resets params, colors, and wireframe', () => {
      const { result, opts } = renderActions()
      act(() => {
        result.current.handleReset()
      })
      expect(opts.setParams).toHaveBeenCalledWith({ x: 1 })
      expect(opts.setColors).toHaveBeenCalledWith(['#fff'])
      expect(opts.setWireframe).toHaveBeenCalledWith(false)
    })
  })

  // ---------- passthrough exports ----------
  it('passes through handleExportImage', () => {
    const exportImage = vi.fn()
    const { result } = renderActions({ handleExportImage: exportImage })
    expect(result.current.handleExportImage).toBe(exportImage)
  })

  it('passes through handleExportAllViews', () => {
    const exportAll = vi.fn()
    const { result } = renderActions({ handleExportAllViews: exportAll })
    expect(result.current.handleExportAllViews).toBe(exportAll)
  })

  it('shareToast initializes to false', () => {
    const { result } = renderActions()
    expect(result.current.shareToast).toBe(false)
  })
})
