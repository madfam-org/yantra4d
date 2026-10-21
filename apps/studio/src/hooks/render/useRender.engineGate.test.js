import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

// The engine gate runs BEFORE the long-render estimate: a tier without the
// mode's engine gets the upgrade prompt, never the "~2 minutes" dialog and
// never a network render (the old path confirmed, rendered, and got a 403).

const mocks = vi.hoisted(() => ({
  triggerUpgradePrompt: vi.fn(),
  tier: { tier: 'guest', limits: null },
  preview: undefined,
}))

vi.mock('../../services/engine/renderService', () => ({
  renderParts: vi.fn(() => Promise.resolve([{ type: 'main', url: 'blob:mock' }])),
  cancelRender: vi.fn(() => Promise.resolve()),
  cancelRenderOnUnload: vi.fn(() => true),
  cancelSupersededRender: vi.fn(() => false),
  estimateRenderTime: vi.fn(() => 120),
}))
vi.mock('../system/useUpgradePrompt', () => ({
  useUpgradePrompt: () => ({ triggerUpgradePrompt: mocks.triggerUpgradePrompt }),
}))
vi.mock('../system/useTier', () => ({ useTier: () => mocks.tier }))
vi.mock('../../lib/prerenderedPreview', () => ({ peekPrerenderedPreview: () => mocks.preview }))
vi.mock('../../services/cache/renderCache', () => ({
  makeCacheKey: vi.fn(async (...args) => JSON.stringify(args)),
  get: vi.fn(async () => null),
  put: vi.fn(async () => {}),
}))
vi.mock('sonner', () => ({ toast: { info: vi.fn(), success: vi.fn(), error: vi.fn() } }))

import { useRender } from './useRender'
import { renderParts, estimateRenderTime } from '../../services/engine/renderService'
import { toast } from 'sonner'

const GUEST = { cadquery_engine: false, graph_engine: false, backend_renders_per_hour: 10 }
const ESSENTIALS = { cadquery_engine: false, graph_engine: false, backend_renders_per_hour: 30 }
const PRO = { cadquery_engine: true, graph_engine: true, backend_renders_per_hour: 150 }

// gridfinity's shape: a CadQuery project whose `grid` mode is OpenSCAD.
const dualEngine = {
  engine: 'cadquery',
  modes: [{ id: 'bin', parts: ['bin'] }, { id: 'grid', engine: 'openscad', parts: ['grid'] }],
  parts: [],
  parameters: [{ id: 'size' }],
  estimate_constants: { warning_threshold_seconds: 60 },
}
const cadqueryOnly = { ...dualEngine, modes: [{ id: 'bin', parts: ['bin'] }] }

const t = (key, params) => (params ? `${key} ${Object.values(params).join(' ')}` : key)

function setup({ mode = 'bin', manifest = dualEngine } = {}) {
  return renderHook(() => useRender({
    mode, params: { size: 20 }, manifest, t,
    getCacheKey: (m, p) => JSON.stringify({ mode: m, ...p }), project: 'gridfinity',
  }))
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.tier = { tier: 'guest', limits: GUEST }
  mocks.preview = { slug: 'gridfinity', candidates: [], commonsPin: null, generated: null }
})

describe('engine gate before the render estimate', () => {
  it('a guest asking for a CadQuery mode gets the upgrade prompt, no estimate dialog, no render call', async () => {
    const { result } = setup()
    await act(async () => { await result.current.handleGenerate() })

    expect(mocks.triggerUpgradePrompt).toHaveBeenCalledTimes(1)
    expect(mocks.triggerUpgradePrompt).toHaveBeenCalledWith('tier.engine_cadquery', {
      alternatives: ['tier.free_alt_preview', 'tier.free_alt_openscad_guest 10'],
    })
    expect(result.current.showConfirmDialog).toBe(false)
    expect(estimateRenderTime).not.toHaveBeenCalled()
    expect(renderParts).not.toHaveBeenCalled()
  })

  it('logs what the plan includes, never as an error line', async () => {
    const { result } = setup()
    await act(async () => { await result.current.handleGenerate() })
    expect(result.current.logs).toContain('tier.engine_gated_log tier.engine_cadquery')
    expect(result.current.logs).not.toContain('log.error')
  })

  it('Force Regenerate is gated too', async () => {
    const { result } = setup()
    await act(async () => { await result.current.handleGenerate(true) })
    expect(mocks.triggerUpgradePrompt).toHaveBeenCalledTimes(1)
    expect(renderParts).not.toHaveBeenCalled()
  })

  it('an automatic render of a gated mode is skipped quietly', async () => {
    const { result } = setup()
    await act(async () => { await result.current.handleGenerate(false, null, { automatic: true }) })
    expect(mocks.triggerUpgradePrompt).not.toHaveBeenCalled()
    expect(toast.info).not.toHaveBeenCalled()
    expect(renderParts).not.toHaveBeenCalled()
    expect(result.current.logs).toBe('log.ready')
  })

  it("the same guest on the cartridge's OpenSCAD mode reaches the estimate as before", async () => {
    const { result } = setup({ mode: 'grid' })
    await act(async () => { await result.current.handleGenerate() })
    expect(mocks.triggerUpgradePrompt).not.toHaveBeenCalled()
    expect(result.current.showConfirmDialog).toBe(true)
  })

  it('a tier with CadQuery reaches the estimate dialog', async () => {
    mocks.tier = { tier: 'pro', limits: PRO }
    const { result } = setup()
    await act(async () => { await result.current.handleGenerate() })
    expect(mocks.triggerUpgradePrompt).not.toHaveBeenCalled()
    expect(result.current.showConfirmDialog).toBe(true)
  })

  it('unknown limits fall through to the server, which stays the authority', async () => {
    mocks.tier = { tier: 'guest', limits: null }
    const { result } = setup()
    await act(async () => { await result.current.handleGenerate(true) })
    expect(mocks.triggerUpgradePrompt).not.toHaveBeenCalled()
    expect(renderParts).toHaveBeenCalledTimes(1)
  })

  it('names only the alternatives that exist', async () => {
    mocks.preview = null
    const { result } = setup({ manifest: cadqueryOnly })
    await act(async () => { await result.current.handleGenerate() })
    expect(mocks.triggerUpgradePrompt).toHaveBeenCalledWith('tier.engine_cadquery', { alternatives: [] })
  })

  it('a signed-in tier without CadQuery gets its own quota in the alternative', async () => {
    mocks.tier = { tier: 'essentials', limits: ESSENTIALS }
    const { result } = setup()
    await act(async () => { await result.current.handleGenerate() })
    expect(mocks.triggerUpgradePrompt).toHaveBeenCalledWith('tier.engine_cadquery', {
      alternatives: ['tier.free_alt_preview', 'tier.free_alt_openscad 30'],
    })
  })

  it('a server 403 that still happens is logged without the error prefix', async () => {
    mocks.tier = { tier: 'guest', limits: null }
    renderParts.mockRejectedValueOnce(new Error('HTTP 403 Forbidden'))
    const { result } = setup()
    await act(async () => { await result.current.handleGenerate(true) })
    expect(result.current.logs).toContain('tier.upgrade_cloud_render')
    expect(result.current.logs).not.toContain('log.error')
    expect(mocks.triggerUpgradePrompt).toHaveBeenCalledWith('CadQuery Cloud Rendering')
  })
})
