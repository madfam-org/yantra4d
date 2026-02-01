import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useShareableUrl, getSharedParams } from './useShareableUrl'

describe('useShareableUrl', () => {
  const defaultParams = { size: 40, rows: 3, cols: 3, show_base: true }

  beforeEach(() => {
    // Reset URL state
    window.history.replaceState(null, '', window.location.pathname)
  })

  describe('getSharedParams', () => {
    it('returns null when no ?p= param', () => {
      expect(getSharedParams()).toBeNull()
    })

    it('decodes base64url-encoded param diff', () => {
      const diff = { size: 60, rows: 5 }
      const encoded = btoa(JSON.stringify(diff)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
      window.history.replaceState(null, '', `?p=${encoded}`)
      expect(getSharedParams()).toEqual(diff)
    })

    it('returns null for malformed base64', () => {
      window.history.replaceState(null, '', '?p=!!!invalid!!!')
      expect(getSharedParams()).toBeNull()
    })

    it('returns null for valid base64 but invalid JSON', () => {
      const encoded = btoa('not json').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
      window.history.replaceState(null, '', `?p=${encoded}`)
      expect(getSharedParams()).toBeNull()
    })
  })

  describe('generateShareUrl', () => {
    it('generates URL with encoded param diff', () => {
      const params = { ...defaultParams, size: 60 }
      const { result } = renderHook(() =>
        useShareableUrl({ params, mode: 'single', projectSlug: 'tablaco', defaultParams })
      )
      const url = result.current.generateShareUrl()
      expect(url).toContain('#/tablaco/share/single')
      expect(url).toContain('p=')

      // Decode and verify
      const parsed = new URL(url)
      const encoded = parsed.searchParams.get('p')
      const base64 = encoded.replace(/-/g, '+').replace(/_/g, '/')
      const padded = base64 + '='.repeat((4 - base64.length % 4) % 4)
      const decoded = JSON.parse(atob(padded))
      expect(decoded).toEqual({ size: 60 })
    })

    it('omits ?p= when params match defaults', () => {
      const { result } = renderHook(() =>
        useShareableUrl({ params: defaultParams, mode: 'single', projectSlug: 'tablaco', defaultParams })
      )
      const url = result.current.generateShareUrl()
      expect(url).toContain('#/tablaco/share/single')
      expect(url).not.toContain('p=')
    })

    it('encodes multiple differing params', () => {
      const params = { ...defaultParams, size: 80, rows: 7, show_base: false }
      const { result } = renderHook(() =>
        useShareableUrl({ params, mode: 'grid', projectSlug: 'test', defaultParams })
      )
      const url = result.current.generateShareUrl()
      const parsed = new URL(url)
      const encoded = parsed.searchParams.get('p')
      const base64 = encoded.replace(/-/g, '+').replace(/_/g, '/')
      const padded = base64 + '='.repeat((4 - base64.length % 4) % 4)
      const decoded = JSON.parse(atob(padded))
      expect(decoded).toEqual({ size: 80, rows: 7, show_base: false })
    })
  })

  describe('copyShareUrl', () => {
    it('copies to clipboard and returns true on success', async () => {
      const writeText = vi.fn().mockResolvedValue(undefined)
      Object.assign(navigator, { clipboard: { writeText } })

      const { result } = renderHook(() =>
        useShareableUrl({ params: { ...defaultParams, size: 50 }, mode: 'single', projectSlug: 'tablaco', defaultParams })
      )

      let ok
      await act(async () => { ok = await result.current.copyShareUrl() })
      expect(ok).toBe(true)
      expect(writeText).toHaveBeenCalledOnce()
      expect(writeText.mock.calls[0][0]).toContain('#/tablaco/share/single')
    })

    it('returns false when clipboard fails', async () => {
      Object.assign(navigator, { clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) } })

      const { result } = renderHook(() =>
        useShareableUrl({ params: defaultParams, mode: 'single', projectSlug: 'tablaco', defaultParams })
      )

      let ok
      await act(async () => { ok = await result.current.copyShareUrl() })
      expect(ok).toBe(false)
    })
  })
})
