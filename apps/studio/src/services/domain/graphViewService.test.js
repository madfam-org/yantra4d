import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../core/backendDetection', () => ({ getApiBase: () => 'http://localhost:5000' }))
vi.mock('../core/apiClient', () => ({ apiFetch: vi.fn() }))

import { fetchModeGraph, GraphViewError, modeDeclaresGraph } from './graphViewService'
import { apiFetch } from '../core/apiClient'

const ok = (body) => ({ ok: true, status: 200, json: () => Promise.resolve(body) })

beforeEach(() => vi.clearAllMocks())

describe('fetchModeGraph', () => {
  it('asks the public graph route for one mode, encoding both parts', async () => {
    apiFetch.mockResolvedValue(ok({ mode: 'a b', path: 'g.graph.json', role: 'source', script: null, content: '{}' }))
    await fetchModeGraph('flange-plate', 'a b')
    expect(apiFetch).toHaveBeenCalledWith('http://localhost:5000/api/projects/flange-plate/graph?mode=a%20b', {})
  })

  it('passes an abort signal through', async () => {
    apiFetch.mockResolvedValue(ok({ path: 'g.graph.json', content: '{}' }))
    const controller = new AbortController()
    await fetchModeGraph('s', 'm', controller.signal)
    expect(apiFetch.mock.calls[0][1]).toEqual({ signal: controller.signal })
  })

  it('returns the graph, with a twin keeping its script', async () => {
    apiFetch.mockResolvedValue(ok({ mode: 'drive', path: 'd.graph.json', role: 'twin', script: 'main.py', content: '{"nodes":[]}' }))
    expect(await fetchModeGraph('ab-drive', 'drive')).toEqual({
      mode: 'drive', path: 'd.graph.json', role: 'twin', script: 'main.py', content: '{"nodes":[]}',
    })
  })

  it('throws the server code on a refusal', async () => {
    apiFetch.mockResolvedValue({ ok: false, status: 404, json: () => Promise.resolve({ error: 'This mode is not a graph', error_code: 'not_a_graph_mode' }) })
    const err = await fetchModeGraph('s', 'm').catch((e) => e)
    expect(err).toBeInstanceOf(GraphViewError)
    expect(err.code).toBe('not_a_graph_mode')
    expect(err.status).toBe(404)
    expect(err.message).toBe('This mode is not a graph')
  })

  it('keeps the status when the error body is not JSON', async () => {
    apiFetch.mockResolvedValue({ ok: false, status: 502, json: () => Promise.reject(new Error('html')) })
    const err = await fetchModeGraph('s', 'm').catch((e) => e)
    expect(err.status).toBe(502)
    expect(err.code).toBeNull()
  })

  it('rejects a response without content', async () => {
    apiFetch.mockResolvedValue(ok({ path: 'g.graph.json' }))
    await expect(fetchModeGraph('s', 'm')).rejects.toThrow('Malformed graph response')
  })
})

describe('modeDeclaresGraph', () => {
  it('is true for a graph-engine mode and for a mode with a graph twin', () => {
    expect(modeDeclaresGraph({ scad_file: 'flange.graph.json' })).toBe(true)
    expect(modeDeclaresGraph({ scad_file: 'main.py', graph_file: 'ab-drive.graph.json' })).toBe(true)
  })

  it('is false for a script-only mode or no mode', () => {
    expect(modeDeclaresGraph({ scad_file: 'main.scad' })).toBe(false)
    expect(modeDeclaresGraph(undefined)).toBe(false)
  })
})
