import { describe, it, expect, vi } from 'vitest'
import { setTokenGetter } from '../services/core/apiClient'
import { downloadFile, downloadDataUrl, downloadZip, downloadZipFromData } from './downloadUtils'

describe('downloadUtils', () => {
  it('downloadFile fetches blob and clicks an anchor element', async () => {
    const click = vi.fn()
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => {})
    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click, remove: vi.fn(),
    })
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:local')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true, blob: () => Promise.resolve(new Blob(['stldata'])),
    })

    await downloadFile('http://cross-origin.example/file.stl', 'test.stl')

    expect(globalThis.fetch).toHaveBeenCalledWith('http://cross-origin.example/file.stl')
    expect(URL.createObjectURL).toHaveBeenCalled()
    expect(click).toHaveBeenCalled()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:local')

    vi.restoreAllMocks()
  })

  it('downloadFile rejects network failures without navigating', async () => {
    const click = vi.fn()
    const links = []
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => {})
    vi.spyOn(document, 'createElement').mockImplementation(() => {
      const link = { href: '', download: '', click, remove: vi.fn() }
      links.push(link)
      return link
    })
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network error'))

    await expect(downloadFile('http://cross-origin.example/file.stl', 'test.stl')).rejects.toThrow('network error')
    expect(click).not.toHaveBeenCalled()

    vi.restoreAllMocks()
  })

  it('downloadDataUrl delegates to downloadFile', async () => {
    const click = vi.fn()
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => {})
    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click, remove: vi.fn(),
    })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true, blob: () => Promise.resolve(new Blob(['hello'])),
    })
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:data')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})

    downloadDataUrl('data:text/plain;base64,aGVsbG8=', 'hello.txt')

    // downloadDataUrl calls downloadFile which is now async — give it a tick
    await new Promise(r => setTimeout(r, 0))
    expect(click).toHaveBeenCalled()
    vi.restoreAllMocks()
  })
})

vi.mock('jszip', () => ({
  default: class MockJSZip {
    file() {}
    generateAsync() { return Promise.resolve(new Blob(['zipdata'])) }
  },
}))

describe('downloadZip', () => {
  it('fetches items, creates zip, and triggers download', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true, blob: () => Promise.resolve(new Blob(['stldata'])),
    })

    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:zip-url')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})

    const click = vi.fn()
    vi.spyOn(document, 'createElement').mockReturnValue({ href: '', download: '', click, remove: vi.fn() })
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => {})

    const result = await downloadZip(
      [{ url: 'blob:a', filename: 'part.stl' }],
      'export.zip'
    )

    expect(result).toBeInstanceOf(Blob)
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:zip-url')
    expect(click).toHaveBeenCalled()

    vi.restoreAllMocks()
  })
})

describe('downloadZipFromData', () => {
  it('creates zip from data arrays and triggers download', async () => {
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:zip-url2')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})

    const click = vi.fn()
    vi.spyOn(document, 'createElement').mockReturnValue({ href: '', download: '', click, remove: vi.fn() })
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => {})

    const result = await downloadZipFromData(
      [{ filename: 'part.stl', data: new Uint8Array([1, 2, 3]) }],
      'data.zip'
    )

    expect(result).toBeInstanceOf(Blob)
    expect(click).toHaveBeenCalled()

    vi.restoreAllMocks()
  })
})


describe('artifact response validation', () => {
  it.each([401, 403, 404, 500])('rejects HTTP %s instead of saving its body', async status => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status })
    await expect(downloadFile('/static/private.stl', 'part.stl')).rejects.toThrow(`HTTP ${status}`)
    await expect(downloadZip([{ url: '/static/private.stl', filename: 'part.stl' }], 'parts.zip')).rejects.toThrow(`HTTP ${status}`)
    fetchMock.mockRestore()
  })
  it('authenticates trusted artifacts without sending tokens to external files', async () => {
    setTokenGetter(async () => 'test-token')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status: 403 })
    await expect(downloadFile('/static/private.stl', 'part.stl')).rejects.toThrow()
    expect(fetchMock).toHaveBeenLastCalledWith('/static/private.stl', { headers: { Authorization: 'Bearer test-token' } })
    await expect(downloadFile('https://external.example/file.stl', 'part.stl')).rejects.toThrow()
    expect(fetchMock).toHaveBeenLastCalledWith('https://external.example/file.stl')
    setTokenGetter(async () => null)
    fetchMock.mockRestore()
  })
})
