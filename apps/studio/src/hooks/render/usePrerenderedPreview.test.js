import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { usePrerenderedPreview } from './usePrerenderedPreview'
import { resetPrerenderManifestCache } from '../../lib/prerenderedPreview'

const manifest = {
  version: 2,
  generated: '2026-09-19T18:46:49Z',
  source: { commons_pin: 'f2c578f78037c37f0f29fe0571b946aeeb45bc0f' },
  models: [
    { slug: 'torus-knot', lod0: { file: 'torus-knot.lod0.glb' }, lod1: { file: 'torus-knot.lod1.glb' } },
    { slug: 'gridfinity', lod1: { file: 'gridfinity.lod1.glb' } },
  ],
}
const BASE = 'https://yantra4d.com/models/'

beforeEach(() => {
  resetPrerenderManifestCache()
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => manifest })))
})
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('usePrerenderedPreview', () => {
  it('a manifest hit offers lod0 with the commons pin', async () => {
    const { result } = renderHook(() => usePrerenderedPreview('torus-knot'))
    await waitFor(() => expect(result.current.current).not.toBeNull())
    expect(result.current.current).toMatchObject({
      url: `${BASE}torus-knot.lod0.glb`, lod: 'lod0', slug: 'torus-knot',
      commonsPin: 'f2c578f78037c37f0f29fe0571b946aeeb45bc0f',
    })
  })

  it('falls back from lod0 to lod1 when lod0 fails to load, then to nothing', async () => {
    const { result } = renderHook(() => usePrerenderedPreview('torus-knot'))
    await waitFor(() => expect(result.current.current?.lod).toBe('lod0'))
    act(() => result.current.reportFailure(`${BASE}torus-knot.lod0.glb`))
    expect(result.current.current?.url).toBe(`${BASE}torus-knot.lod1.glb`)
    act(() => result.current.reportFailure(`${BASE}torus-knot.lod1.glb`))
    expect(result.current.current).toBeNull()
  })

  it('a manifest miss shows nothing', async () => {
    const { result } = renderHook(() => usePrerenderedPreview('ab-drive'))
    await waitFor(() => expect(fetch).toHaveBeenCalled())
    await act(async () => {})
    expect(result.current.current).toBeNull()
  })

  it('a failed manifest fetch shows nothing and logs nothing', async () => {
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('CORS') }))
    const { result } = renderHook(() => usePrerenderedPreview('gridfinity'))
    await waitFor(() => expect(fetch).toHaveBeenCalled())
    await act(async () => {})
    expect(result.current.current).toBeNull()
    expect(errors).not.toHaveBeenCalled()
  })

  it('follows the project: a new slug never shows the previous mesh', async () => {
    const { result, rerender } = renderHook(({ slug }) => usePrerenderedPreview(slug), { initialProps: { slug: 'gridfinity' } })
    await waitFor(() => expect(result.current.current?.slug).toBe('gridfinity'))
    rerender({ slug: 'torus-knot' })
    expect(result.current.current?.slug).not.toBe('gridfinity')
    await waitFor(() => expect(result.current.current?.slug).toBe('torus-knot'))
    expect(fetch).toHaveBeenCalledTimes(1) // the manifest is cached
  })

  it('does nothing without a slug', () => {
    const { result } = renderHook(() => usePrerenderedPreview(null))
    expect(result.current.current).toBeNull()
    expect(fetch).not.toHaveBeenCalled()
  })
})
