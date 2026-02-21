import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../core/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('../core/apiClient', () => ({
  apiFetch: vi.fn(),
}))

import { listFiles, readFile, writeFile, createFile, deleteFile } from './editorService'
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
