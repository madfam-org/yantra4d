import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../core/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('../core/apiClient', () => ({
  apiFetch: vi.fn(),
}))

import { listFiles, readFile, writeFile, createFile, deleteFile, updateGraphBindings } from './editorService'
import { apiFetch } from '../core/apiClient'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('listFiles', () => {
  it('returns file list on success', async () => {
    const files = [{ path: 'main.scad', name: 'main.scad', size: 100 }]
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(files) })
    const result = await listFiles('my-project')
    expect(result).toEqual(files)
    expect(apiFetch).toHaveBeenCalledWith('http://localhost:5000/api/projects/my-project/files')
  })

  it('throws on error', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'Not found' }) })
    await expect(listFiles('bad')).rejects.toThrow('Not found')
  })
})

describe('readFile', () => {
  it('returns file content', async () => {
    const data = { path: 'main.scad', content: 'cube(10);', size: 9 }
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(data) })
    const result = await readFile('proj', 'main.scad')
    expect(result.content).toBe('cube(10);')
  })

  it('throws on error', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'File not found' }) })
    await expect(readFile('proj', 'missing.scad')).rejects.toThrow('File not found')
  })
})

describe('writeFile', () => {
  it('sends PUT with content', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ path: 'main.scad', size: 9 }) })
    await writeFile('proj', 'main.scad', 'cube(20);')
    expect(apiFetch).toHaveBeenCalledWith(
      'http://localhost:5000/api/projects/proj/files/main.scad',
      expect.objectContaining({ method: 'PUT' })
    )
  })

  it('throws on error', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'Too large' }) })
    await expect(writeFile('proj', 'main.scad', 'x')).rejects.toThrow('Too large')
  })
})

describe('createFile', () => {
  it('sends POST with path and content', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ path: 'new.scad', size: 5 }) })
    await createFile('proj', 'new.scad', 'cube(1);')
    expect(apiFetch).toHaveBeenCalledWith(
      'http://localhost:5000/api/projects/proj/files',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('throws on conflict', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'File already exists' }) })
    await expect(createFile('proj', 'main.scad')).rejects.toThrow('File already exists')
  })
})

describe('deleteFile', () => {
  it('sends DELETE', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ deleted: 'helper.scad' }) })
    await deleteFile('proj', 'helper.scad')
    expect(apiFetch).toHaveBeenCalledWith(
      'http://localhost:5000/api/projects/proj/files/helper.scad',
      expect.objectContaining({ method: 'DELETE' })
    )
  })

  it('throws on error', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'Not found' }) })
    await expect(deleteFile('proj', 'x.scad')).rejects.toThrow('Not found')
  })
})

// Fallback error branches — when server returns no error field
describe('fallback error messages', () => {
  it('listFiles throws fallback', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(listFiles('proj')).rejects.toThrow('Failed to list files')
  })

  it('readFile throws fallback', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(readFile('proj', 'f.scad')).rejects.toThrow('Failed to read file')
  })

  it('writeFile throws fallback', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(writeFile('proj', 'f.scad', 'x')).rejects.toThrow('Failed to write file')
  })

  it('createFile throws fallback', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(createFile('proj', 'f.scad')).rejects.toThrow('Failed to create file')
  })

  it('deleteFile throws fallback', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(deleteFile('proj', 'f.scad')).rejects.toThrow('Failed to delete file')
  })
})

describe('updateGraphBindings', () => {
  it('sends PUT with exactly {bindings}', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ bindings: { r: 'outline.r' } }) })
    const result = await updateGraphBindings('fork', { r: 'outline.r', h: null })
    expect(result).toEqual({ bindings: { r: 'outline.r' } })
    expect(apiFetch).toHaveBeenCalledWith(
      'http://localhost:5000/api/projects/fork/manifest/bindings',
      expect.objectContaining({ method: 'PUT', body: JSON.stringify({ bindings: { r: 'outline.r', h: null } }) }),
    )
  })

  it('throws the server reason, or a fallback', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'Bindings can only be edited on your fork' }) })
    await expect(updateGraphBindings('commons', { r: null })).rejects.toThrow('only be edited on your fork')
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(updateGraphBindings('commons', { r: null })).rejects.toThrow('Failed to save bindings')
  })
})

describe('EditorRequestError', () => {
  it('carries the status and the server error_code of a refused write', async () => {
    const { EditorRequestError } = await import('./editorService')
    apiFetch.mockResolvedValue({ ok: false, status: 403, json: () => Promise.resolve({ error: 'Fork it', error_code: 'not_cartridge_owner' }) })
    const err = await writeFile('fork', 'main.scad', 'x').catch((e) => e)
    expect(err).toBeInstanceOf(EditorRequestError)
    expect(err).toMatchObject({ status: 403, code: 'not_cartridge_owner', message: 'Fork it' })
  })

  it('still reports a non-JSON error page (a proxy 502) by status', async () => {
    apiFetch.mockResolvedValue({ ok: false, status: 502, json: () => Promise.reject(new SyntaxError('Unexpected token <')) })
    const err = await writeFile('fork', 'main.scad', 'x').catch((e) => e)
    expect(err).toMatchObject({ status: 502, code: null, message: 'Failed to write file' })
    await expect(deleteFile('fork', 'main.scad')).rejects.toMatchObject({ status: 502, message: 'Failed to delete file' })
  })
})
