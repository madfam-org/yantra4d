import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('./backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('./apiClient', () => ({
  apiFetch: vi.fn(),
}))

import { getStatus, getDiff, commit, push, pull, connectRemote } from './gitService'
import { apiFetch } from './apiClient'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('getStatus', () => {
  it('returns git status', async () => {
    const data = { success: true, branch: 'main', clean: true, modified: [], untracked: [] }
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(data) })
    const result = await getStatus('proj')
    expect(result.branch).toBe('main')
  })

  it('throws on error', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'No git' }) })
    await expect(getStatus('proj')).rejects.toThrow('No git')
  })
})

describe('getDiff', () => {
  it('returns diff without file param', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ success: true, diff: '' }) })
    await getDiff('proj')
    expect(apiFetch).toHaveBeenCalledWith('http://localhost:5000/api/projects/proj/git/diff')
  })

  it('includes file param when provided', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ success: true, diff: '+line' }) })
    await getDiff('proj', 'main.scad')
    expect(apiFetch).toHaveBeenCalledWith(expect.stringContaining('file=main.scad'))
  })
})

describe('commit', () => {
  it('sends POST with message and files', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ success: true, commit: 'abc123' }) })
    const result = await commit('proj', 'Update', ['main.scad'])
    expect(result.success).toBe(true)
    expect(apiFetch).toHaveBeenCalledWith(
      'http://localhost:5000/api/projects/proj/git/commit',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('throws on error', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'No files' }) })
    await expect(commit('proj', 'msg', [])).rejects.toThrow('No files')
  })
})

describe('push', () => {
  it('sends POST', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ success: true }) })
    await push('proj')
    expect(apiFetch).toHaveBeenCalledWith(
      'http://localhost:5000/api/projects/proj/git/push',
      expect.objectContaining({ method: 'POST' })
    )
  })
})

describe('pull', () => {
  it('sends POST', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ success: true }) })
    await pull('proj')
    expect(apiFetch).toHaveBeenCalledWith(
      'http://localhost:5000/api/projects/proj/git/pull',
      expect.objectContaining({ method: 'POST' })
    )
  })
})

describe('connectRemote', () => {
  it('sends POST with remote_url', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ success: true }) })
    await connectRemote('proj', 'https://github.com/u/r.git')
    expect(apiFetch).toHaveBeenCalledWith(
      'http://localhost:5000/api/projects/proj/git/connect-remote',
      expect.objectContaining({ method: 'POST' })
    )
  })
})
