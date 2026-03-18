import { describe, it, expect, vi } from 'vitest'
import { downloadFile, downloadDataUrl, downloadZip, downloadZipFromData } from './downloadUtils'

describe('downloadUtils', () => {
  it('downloadFile fetches blob and clicks an anchor element', async () => {
    const click = vi.fn()
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => {})
    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click,
    })
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:local')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      blob: () => Promise.resolve(new Blob(['stldata'])),
    })

    await downloadFile('http://cross-origin.example/file.stl', 'test.stl')

    expect(globalThis.fetch).toHaveBeenCalledWith('http://cross-origin.example/file.stl')
    expect(URL.createObjectURL).toHaveBeenCalled()
    expect(click).toHaveBeenCalled()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:local')

    vi.restoreAllMocks()
  })

  it('downloadFile falls back to direct anchor on fetch failure', async () => {
    const click = vi.fn()
    const links = []
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => {})
    vi.spyOn(document, 'createElement').mockImplementation(() => {
      const link = { href: '', download: '', click }
      links.push(link)
      return link
    })
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network error'))

    await downloadFile('http://cross-origin.example/file.stl', 'test.stl')

    expect(click).toHaveBeenCalled()
    // Fallback should use the original URL directly
    expect(links[links.length - 1].href).toBe('http://cross-origin.example/file.stl')

    vi.restoreAllMocks()
  })

  it('downloadDataUrl delegates to downloadFile', async () => {
    const click = vi.fn()
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => {})
    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click,
    })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      blob: () => Promise.resolve(new Blob(['hello'])),
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
      blob: () => Promise.resolve(new Blob(['stldata'])),
    })

    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:zip-url')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})

    const click = vi.fn()
    vi.spyOn(document, 'createElement').mockReturnValue({ href: '', download: '', click })
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
    vi.spyOn(document, 'createElement').mockReturnValue({ href: '', download: '', click })
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
