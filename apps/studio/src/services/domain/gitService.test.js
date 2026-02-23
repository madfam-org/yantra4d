import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../core/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('../core/apiClient', () => ({
  apiFetch: vi.fn(),
}))

import { getStatus, getDiff, commit, push, pull, connectRemote, renderHead } from './gitService'
import { apiFetch } from '../core/apiClient'

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

  it('throws on error with server message', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'Invalid URL' }) })
    await expect(connectRemote('proj', 'bad')).rejects.toThrow('Invalid URL')
  })

  it('throws fallback message when no error field', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(connectRemote('proj', 'bad')).rejects.toThrow('Failed to connect remote')
  })
})

describe('renderHead', () => {
  it('returns render result on success', async () => {
    const data = { parts: [{ type: 'main', url: 'blob:x' }] }
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(data) })
    const result = await renderHead('proj', { mode: 'unit', file: 'main.scad' })
    expect(result).toEqual(data)
    expect(apiFetch).toHaveBeenCalledWith(
      'http://localhost:5000/api/projects/proj/git/render-head',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('throws on error with server message', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'Git conflict' }) })
    await expect(renderHead('proj', {})).rejects.toThrow('Git conflict')
  })

  it('throws fallback message when no error field', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(renderHead('proj', {})).rejects.toThrow('Render HEAD failed')
  })
})

describe('getDiff error branches', () => {
  it('throws on error with server message', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'Repo locked' }) })
    await expect(getDiff('proj')).rejects.toThrow('Repo locked')
  })

  it('throws fallback message when no error field', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(getDiff('proj')).rejects.toThrow('Failed to get diff')
  })
})

describe('push error branches', () => {
  it('throws on error with server message', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'No remote' }) })
    await expect(push('proj')).rejects.toThrow('No remote')
  })

  it('throws fallback message when no error field', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(push('proj')).rejects.toThrow('Push failed')
  })
})

describe('pull error branches', () => {
  it('throws on error with server message', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'Merge conflict' }) })
    await expect(pull('proj')).rejects.toThrow('Merge conflict')
  })

  it('throws fallback message when no error field', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(pull('proj')).rejects.toThrow('Pull failed')
  })
})

describe('getStatus fallback error', () => {
  it('throws fallback message when no error field', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(getStatus('proj')).rejects.toThrow('Failed to get git status')
  })
})

describe('commit fallback error', () => {
  it('throws fallback message when no error field', async () => {
    apiFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })
    await expect(commit('proj', 'msg', [])).rejects.toThrow('Commit failed')
  })
})
