import { describe, it, expect, vi } from 'vitest'
import { downloadFile, downloadDataUrl, downloadZip, downloadZipFromData } from './downloadUtils'

describe('downloadUtils', () => {
  it('downloadFile creates and clicks an anchor element', () => {
    const click = vi.fn()
    const appendChild = vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
    const removeChild = vi.spyOn(document.body, 'removeChild').mockImplementation(() => {})
    vi.spyOn(document, 'createElement').mockReturnValue({
      set href(_) {},
      set download(_) {},
      click,
    })

    downloadFile('blob:http://localhost/abc', 'test.stl')

    expect(click).toHaveBeenCalled()
    expect(appendChild).toHaveBeenCalled()
    expect(removeChild).toHaveBeenCalled()

    vi.restoreAllMocks()
  })

  it('downloadDataUrl delegates to downloadFile', () => {
    const click = vi.fn()
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => {})
    vi.spyOn(document, 'createElement').mockReturnValue({
      set href(_) {},
      set download(_) {},
      click,
    })

    downloadDataUrl('data:text/plain;base64,aGVsbG8=', 'hello.txt')

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
